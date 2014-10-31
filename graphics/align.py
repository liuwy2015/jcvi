#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
%prog [dotplot|reads|om]

Illustrate three different types of alignments.
- Pairwise sequence alignment, aka, "dot plot"
- Read alignment, similar to the visualization of a BAM file
- Optical map alignment, matchings between restriction fragments
"""


import sys

from random import randint

from jcvi.graphics.chromosome import Chromosome, HorizontalChromosome
from jcvi.graphics.glyph import GeneGlyph
from jcvi.graphics.base import plt, savefig, normalize_axes
from jcvi.apps.base import OptionParser


class BaseAlign (object):

    def __init__(self, fig, xywh, xmax=100):
        x, y, w, h = xywh
        self.ax = fig.add_axes(xywh)
        self.sax = fig.add_axes([x + .15 * w, y + .15 * h, w * .7, h * .7])
        self.amax = self.bmax = xmax
        self.a = [(1, xmax)]
        self.b = [(1, xmax)]
        self.apatch = self.bpatch = None

    def convert(self, pos, xmax, xstart=.15, canvas=.7):
        return xstart + pos * canvas / xmax

    def invert(self, a, b):
        self.a = [(1, a), (a, b), (b, self.amax)]
        self.b = [(1, a), (b, a), (b, self.bmax)]
        self.apatch = (self.convert(a, self.amax),
                       self.convert(b, self.amax))
        self.bpatch = (self.convert(a, self.bmax),
                       self.convert(b, self.bmax))

    def delete(self, a, b):
        self.bmax -= b - a
        self.a = [(1, a), (b, self.amax)]
        self.b = [(1, a), (a, self.bmax)]
        self.apatch = (self.convert(a, self.amax),
                       self.convert(b, self.amax))

    def duplicate(self, a, b, gap=0):
        self.bmax += b - a + gap
        self.a = [(1, b), (a, self.amax)]
        self.b = [(1, b), (b + gap, self.bmax)]
        self.apatch = (self.convert(a, self.amax),
                       self.convert(b, self.amax))
        self.bpatch = (self.convert(a, self.bmax),
                       self.convert(b, self.bmax),
                       self.convert(b + gap, self.bmax),
                       self.convert(2 * b - a + gap, self.bmax))


class PairwiseAlign (BaseAlign):

    def __init__(self, fig, xywh):
        super(PairwiseAlign, self).__init__(fig, xywh)

    def draw(self, width=.03):
        HorizontalChromosome(self.ax, .15, .85, .1, height=width,
                             patch=self.apatch, lw=2)
        Chromosome(self.ax, .1, .15, .85, width=width,
                   patch=self.bpatch, lw=2)
        for a, b in zip(self.a, self.b):
            self.sax.plot(a, b, "-", color="darkslategrey", lw=2)
        self.sax.set_xticklabels([])
        self.sax.set_yticklabels([])


class ReadAlign (BaseAlign):

    def __init__(self, fig, xywh, readlen=6, gap=6):
        super(ReadAlign, self).__init__(fig, xywh)
        readrange = 2 * readlen + gap
        self.reads = []
        for x in xrange(100):
            pos = self.convert(randint(1, self.amax - readrange), self.amax,
                               xstart=.1, canvas=.8)
            self.reads.append(PairedRead(pos, ratio=.8 / self.amax))
        self.layout()

    def layout(self, maxtracks=8):
        track_ends = [0]
        self.reads.sort(key=lambda x: x.start)
        for r in self.reads:
            m = min(track_ends)
            mi = track_ends.index(m)
            if r.start > m + .005:
                track_ends[mi] = r.end
            else:
                if len(track_ends) >= maxtracks:
                    continue
                track_ends.append(r.end)
                mi = len(track_ends) - 1
            r.set_y(.25 + mi * .03)
        self.reads = [x for x in self.reads if x.y is not None]

    def draw(self, width=.03):
        HorizontalChromosome(self.ax, .1, .9, .2, height=width,
                             patch=self.apatch, lw=2)
        for r in self.reads:
            r.draw(self.ax)
        normalize_axes(self.sax)

    def delete(self, a, b):
        self.apatch = (self.convert(a, self.amax),
                       self.convert(b, self.amax))
        for r in self.reads:
            self.breakpoint(a, b)


class SingleRead (object):

    def __init__(self, start, ratio, readlen=6, sign=1):
        self.x1 = start
        self.x2 = start + sign * ratio * readlen
        self.y = None
        self.start, self.end = min(self.x1, self.x2), max(self.x1, self.x2)
        self.span = self.end - self.start + 1
        self.color = 'k'

    def draw(self, ax, height=.015):
        GeneGlyph(ax, self.x1, self.x2, self.y, height, tip=.01,
                  color=self.color, gradient=True)

    def breakpoint(self, a, b):
        if self.start < a < self.end:
            self.end = a
            self.color = 'r'
        elif self.start < b < self.end:
            self.start = b
            self.color = 'r'


class PairedRead (object):

    def __init__(self, start, ratio, readlen=6, gap=6):
        self.r1 = SingleRead(start, ratio, readlen=readlen)
        i1 = start + readlen * ratio
        i2 = i1 + gap * ratio
        i3 = i2 + readlen * ratio
        self.r2 = SingleRead(i3, ratio, readlen=readlen, sign=-1)
        self.i1, self.i2 = i1, i2
        self.start = min(self.r1.start, self.r2.start)
        self.end = max(self.r1.end, self.r2.end)
        self.y = None

    def set_y(self, y):
        self.y = y
        self.r1.y = self.r2.y = y

    def draw(self, ax):
        self.r1.draw(ax)
        self.r2.draw(ax)
        ax.plot((self.i1, self.i2), (self.y, self.y), "-",
                 color="lightslategrey", lw=2)


def main():
    p = OptionParser(__doc__)
    opts, args, iopts = p.set_image_options()

    if len(args) != 1:
        sys.exit(not p.print_help())

    mode, = args
    assert mode in ("dotplot", "reads", "om")

    fig = plt.figure(1, (iopts.w, iopts.h))
    root = fig.add_axes([0, 0, 1, 1])
    if mode == "dotplot":
        p = PairwiseAlign(fig, [0, 0, 1, 1])
        p.duplicate(30, 50, gap=10)
        p.draw()
    elif mode == "reads":
        p = ReadAlign(fig, [0, 0, 1, 1])
        p.draw()

    normalize_axes(root)

    image_name = mode + "." + iopts.format
    savefig(image_name, dpi=iopts.dpi, iopts=iopts)


if __name__ == '__main__':
    main()