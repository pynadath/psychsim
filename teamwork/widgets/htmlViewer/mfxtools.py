## vim:ts=4:et:nowrap
##
##---------------------------------------------------------------------------##
##
## PySol -- a Python Solitaire game
##
## Copyright (C) 2003 Markus Franz Xaver Johannes Oberhumer
## Copyright (C) 2002 Markus Franz Xaver Johannes Oberhumer
## Copyright (C) 2001 Markus Franz Xaver Johannes Oberhumer
## Copyright (C) 2000 Markus Franz Xaver Johannes Oberhumer
## Copyright (C) 1999 Markus Franz Xaver Johannes Oberhumer
## Copyright (C) 1998 Markus Franz Xaver Johannes Oberhumer
## All Rights Reserved.
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; see the file COPYING.
## If not, write to the Free Software Foundation, Inc.,
## 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
##
## Markus F.X.J. Oberhumer
## <markus@oberhumer.com>
## http://www.oberhumer.com/pysol
##
##---------------------------------------------------------------------------##


# imports
import sys, types, operator


# /***********************************************************************
# // unicode
# ************************************************************************/

try:
    types.StringTypes
except:
    try:
        types.StringTypes = (types.StringType, types.UnicodeType)
    except:
        types.StringTypes = (types.StringType,)

try:
    types.UnicodeType
except:
    types.UnicodeType = None


def ustr(s):
    if type(s) is types.UnicodeType:
        try:
            x = str(s)
        except:
            x = ""
            for c in x:
                if ord(c) >= 256:
                    c = ""
                x = x + c
        return s
    else:
        x = str(s)
    return x


# /***********************************************************************
# // emulation of some of Marc-Andre Lemburg's mxTools
# ************************************************************************/

def indices(object):
    return tuple(range(len(object)))

def trange(start, stop=None, step=None):
    if stop is None:
        return tuple(range(start))
    elif step is None:
        return tuple(range(start, stop))
    else:
        return tuple(range(start, stop, step))

def range_len(object):
    return range(len(object))

def reverse(sequence):
    if type(sequence) is types.TupleType:
        l = list(sequence)
        l.reverse()
        l = tuple(l)
    elif type(sequence) is types.ListType:
        l = sequence[:]
        l.reverse()
    else:
        l = list(sequence)
        l.reverse()
    return l

def irange(object, indices=None):
    if indices is None:
        return tuple(map(None, range(len(object)), object))
    else:
        # this is slow...
        l = []
        for i in indices:
            l.append((i, object[i]))
        return tuple(l)

def count(condition, sequence):
    if condition is None:
        return len(filter(None, sequence))
    else:
        ##return len(filter(condition, sequence))
        # why is this faster ???
        return len(filter(None, map(condition, sequence)))

def exists(condition, sequence):
    if condition is None:
        condition = operator.truth
    for obj in sequence:
        if condition(obj):
            return 1
    return 0

def forall(condition, sequence):
    if condition is None:
        condition = operator.truth
    for obj in sequence:
        if not condition(obj):
            return 0
    return 1


# /***********************************************************************
# //
# ************************************************************************/

# def bool(expr): if expr: return 1 else: return 0
bool = operator.truth

def sgn(expr):
    if expr < 0: return -1
    if expr > 0: return 1
    return 0


# /***********************************************************************
# //
# ************************************************************************/


def mfxtools_main(args=[]):
    print types.StringTypes
    #
    m = None
    try:
        import NewBuiltins.mxTools
        m = NewBuiltins.mxTools
    except:
        print "mxTools not found !"
        return 0
    #
    b = sys.modules[__name__]
    t1 = (0, 1, 2, 3, 4)
    t2 = ()
    l1 = [0, 1, 2, 3, 4]
    l2 = []
    cond1 = lambda x: x == 1
    cond2 = lambda x: x < 3
    #
    for x in (t1, t2, l1, l2):
        assert b.indices(x) == m.indices(x)
        assert b.range_len(x) == m.range_len(x)
        assert b.reverse(x) == m.reverse(x)
        assert b.irange(x) == m.irange(x)
        for cond in (cond1, cond2):
            assert b.count(cond, x) == m.count(cond, x)
            assert b.exists(cond, x) == m.exists(cond, x)
            assert b.forall(cond, x) == m.forall(cond, x)
    #
    assert b.irange(t1, t1) == m.irange(t1, t1)
    assert b.irange(t1, reverse(t1)) == m.irange(t1, reverse(t1))
    assert b.irange(t1, t2) == m.irange(t1, t2)
    #
    assert b.trange(10) == m.trange(10)
    assert b.trange(0, 10) == m.trange(0, 10)
    assert b.trange(0, 10, 2) == m.trange(0, 10, 2)
    #
    print "All tests passed."
    return 0

if __name__ == "__main__":
    sys.exit(mfxtools_main(sys.argv))

