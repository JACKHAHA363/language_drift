""" The general interface of an model
"""
import torch
from torch.nn import functional as F
import os

from ld_research.model.grus import GRUDecoder, GRUEncoder
from ld_research.text import Vocab
from ld_research.model.utils import sequence_mask

class Agent(torch.nn.Module):
    """ The model. A seq to seq model """
    def __init__(self, src_vocab, tgt_vocab, opt):
        """ Constructor
            :param src_vocab: source language_vocab. An instance of `Vocab`
            :param tgt_vocab: target language_vocab. An instance of `Vocab`
            :param opt: The hyparparameters
        """
        super(Agent, self).__init__()
        assert isinstance(src_vocab, Vocab)
        assert isinstance(tgt_vocab, Vocab)
        self.src_vocab = src_vocab
        self.tgt_vocab = tgt_vocab
        self.add_module('src_emb', torch.nn.Embedding(len(src_vocab),
                                                      opt.emb_size))
        self.add_module('tgt_emb', torch.nn.Embedding(len(tgt_vocab),
                                                      opt.emb_size))
        self.add_module('encoder', GRUEncoder(self.src_emb, hidden_size=opt.hidden_size))
        self.add_module('decoder', GRUDecoder(self.tgt_emb, hidden_size=opt.hidden_size))

    def forward(self, src, tgt, src_lengths=None, tgt_lengths=None, with_align=False):
        """ Forwarding
            :param src [bsz, src_len]
            :param tgt [bsz, tgt_len]
            :param src_lengths [bsz]
            :param tgt_lengths [bsz]
            :param with_align: Whether or not output alignments
            :return: logprobs, targets, mask, alignment (depends)
                logprobs: The logits result. [bsz, tgt_len-1, tgt_vocab]
                targets: The targets to match. [bsz, tgt_len-1]
                mask: The sequence mask. [bsz, tgt_len-1]. None if tgt_lengths is None
                alignments: The attention alignments [bsz, tgt_len-1, src_len]
        """
        states, memory = self.encoder.encode(src)

        # Set up input and output for decoder
        tgt_in = tgt[:, :-1]
        logits, alignments = self.decoder.teacher_forcing(targets=tgt_in,
                                                          memory=memory,
                                                          states=states,
                                                          memory_lengths=src_lengths)
        # Get outputs
        tgt_out = tgt[:, 1:]
        masks = None if tgt_lengths is None else \
            sequence_mask(lengths=tgt_lengths - 1,
                          max_len=logits.size(1))
        masks = masks.float().to(device=self.device)
        logprobs = F.log_softmax(logits, dim=-1)
        outputs = [logprobs, tgt_out, masks]
        if with_align:
            outputs += [alignments]
        return tuple(outputs)

    @property
    def device(self):
        """ Return the device """
        first_param = next(self.parameters())
        return first_param.device
