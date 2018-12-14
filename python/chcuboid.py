#!/usr/bin/env python

# Copyright (C) 2017
#               Free Software Foundation, Inc.
# This file is part of Chisel.
#
# Chisel is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# Chisel is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Chisel; see the file COPYING.  If not, write to the
# Free Software Foundation, 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.
#
# Author Gaius Mulley <gaius@gnu.org>
#

from chvec import *


expandedCuboids = 0  # how many cuboids have we optimised?
chcuboid_enable_optimise = False


#
#  getexpanded - returns the number of expanded or optimised cuboids.
#

def getexpanded ():
    return expandedCuboids


#
#  setOptimise - turn the optimiser on/off.
#

def setOptimise (on):
    chcuboid_enable_optimise = on


def regressiontest ():
    pass


#
#  intersectingRange - returns True if range (a0..a1) intersects with range (b0..b1).
#                      It is easier to test whether they do not intersect
#                      and invert the result.  They do not intersect if a0 lies after b1.
#                      or if the end of a1 is before the start of b0.
#

def intersectingRange (a0, a1, b0, b1):
    return not ((a0 > b1) or (a1 < b0))


class cuboid:
    def __init__ (self, pos, size, material, cuboidno):
        self.pos = pos
        self.size = size
        self.end = addVec (pos, size)
        self.material = material
        self.cuboidno = cuboidno
        self.debugging = False

    #
    #  intersection - return True if self overlaps with the proposed
    #                 cuboid defined by pos, size.
    #

    def intersection (self, pos, size):
        return self._intersectingAxis (pos, addVec (pos, size))

    #
    #  _intersectingAxis - return True if the x, y, and z axis intersects
    #                      between cuboid self and cuboid bpos/bend.
    #                      Returns True if these two cuboids overlap.
    #

    def _intersectingAxis (self, bpos, bend):
        # --complete me--
        return False

    #
    #  interpenetration - return True if self penetrates with the proposed
    #                    cuboid defined by pos, size.
    #

    def interpenetration (self, pos, size):
        return self._interpenetrationAxis (pos, addVec (pos, size))

    #
    #  _interpenetrationAxis - return True if the x, y, and z axis penetrates
    #                          between cuboid self and cuboid bpos/bend.
    #

    def _interpenetrationAxis (self, bpos, bend):
        # --complete me--
        return False

    #
    #  _limits - return True if self has the same start end limits as defined by pos, size
    #            in the dimension, dim.
    #

    def _limits (self, pos, size, dim):
        end = addVec (pos, size)
        return (pos[dim] == self.pos[dim]) and (end[dim] == self.end[dim])

    #
    #  _xlimits - return True if self has the same x start, end as defined by pos and size.
    #

    def _xlimits (self, pos, size):
        pass # --complete me--

    #
    #  _ylimits - return True if self has the same y start, end as defined by pos and size.
    #

    def _ylimits (self, pos, size):
        pass # --complete me--

    #
    #  _zlimits - return True if self has the same x start, end as defined by pos and size.
    #

    def _zlimits (self, pos, size):
        pass # --complete me--

    #
    #  canExtend - returns True if we can enlarge self to contain pos, size.
    #              We can only do this if pos, size joins or overlaps with self.
    #              We have already tested for a superset or subset elsewhere so
    #              this routine just handles extending a cuboid.
    #

    def _canExtend (self, pos, size):
        return False  # --complete me--


    #
    #  _enlarge - we know that self can be enlarged to contain, pos, end.
    #             Futhermore we know we are only going to grow one axis.
    #             (the other two axis will be the same).
    #             We also know that the pos, size might fit inside, or
    #             partially fit inside or join exactly to the end or start of self.
    #             So all we need to do is move the self.pos and self.end to
    #             consume pos, end.
    #

    def _enlarge (self, pos, end):
        self.pos = minVec (self.pos, pos)
        self.end = maxVec (self.end, end)
        self.size = subVec (self.end, self.pos)
        if self.debugging:
            print "_enlarging", self.pos, self.end, self.size

    #
    #  _extend - return True if self was extended to include cuboid pos, size in the
    #            dimension, dim.  It tests whether it overlaps or whether it just
    #            touches self at either end.
    #

    def _extend (self, pos, size, dim):
        global expandedCuboids
        end = addVec (pos, size)
        if (intersectingRange (pos[dim], end[dim], self.pos[dim], self.end[dim]) or
            (pos[dim] == self.end[dim]) or (end[dim] == self.pos[dim])):
            self._enlarge (pos, end)
            expandedCuboids += 1
            return True
        return False

    #
    #  _Xextend - return True if cuboid self was extended along the X axis to
    #             consume pos, size.
    #

    def _Xextend (self, pos, size):
        return self._extend (pos, size, 0)

    #
    #  _Yextend - return True if cuboid self was extended along the Y axis to
    #             consume pos, size.
    #

    def _Yextend (self, pos, size):
        return self._extend (pos, size, 1)

    #
    #  _Zextend - return True if cuboid self was extended along the Z axis to
    #             consume pos, size.
    #

    def _Zextend (self, pos, size):
        return self._extend (pos, size, 2)

    #
    #  _inside - returns True if pos is inside self.
    #

    def _inside (self, pos):
        return ((pos[0] >= self.pos[0]) and (pos[0] <= self.end[0]) and
                (pos[1] >= self.pos[1]) and (pos[1] <= self.end[1]) and
                (pos[2] >= self.pos[2]) and (pos[2] <= self.end[2]))

    #
    #  _subset - returns True if cuboid of pos, size
    #            will fit inside self.
    #

    def _subset (self, pos, size):
        return self._inside (pos) and self._inside (addVec (pos, size))

    #
    #  _superset - return True if cuboid, pos, size will contain self.
    #

    def _superset (self, pos, size):
        b = cuboid (pos, size, None, None)
        return b._subset (self.pos, self.size)

    #
    #  combined - return if we have managed to combine self
    #             with a proposed new cubiod as defined by
    #             pos, size and material.  The material must
    #             be the same.  The arguments pos and size are
    #             might be inside (in which case we return True
    #             and do nothing) or are a superset of self
    #             in which case we change self to be the larger
    #             cuboid and return True.  Finally it
    #             tries to extend self to consume pos, size
    #             by first testing whether pos, size fit on
    #             the end of self (it tries to grow self with
    #             no gaps to consume, pos, size).  If successful
    #             it returns True.
    #

    def combined (self, pos, size, material):
        if material == self.material:
            if self._subset (pos, size):
                return True
            if self._superset (pos, size):
                self.pos = pos
                self.size = size
                self.end = addVec (pos, size)
                return True
            if self._canExtend (pos, size):
                return True
        return False
