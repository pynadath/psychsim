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
import sys, os, re, string, time, types

# PySol imports
from mfxtools import *
from version import VERSION, VERSION_DATE, VERSION_TUPLE
from mfxutil import Pickler, Unpickler, UnpicklingError
from mfxutil import Struct, EnvError


# /***********************************************************************
# // constants
# ************************************************************************/

PACKAGE = "PySol"                                                   #bundle#
PACKAGE_URL = "http://www.oberhumer.com/pysol"                      #bundle#

# Suits values are 0-3. This maps to colors 0-1.
SUITS = ("Club", "Spade", "Heart", "Diamond")
COLORS = ("black", "red")

# Card ranks are 0-12.  We also define symbolic names for the picture cards.
RANKS = ("Ace", "2", "3", "4", "5", "6", "7", "8", "9", "10", "Jack", "Queen", "King")
ACE = 0
JACK = 10
QUEEN = 11
KING = 12

# Special values for Stack.cap:
ANY_SUIT = -1
ANY_COLOR = -1
ANY_RANK = -1
NO_SUIT = 999999        # no card can ever match this suit
NO_COLOR = 999999       # no card can ever match this color
NO_RANK = 999999        # no card can ever match this rank

#
NO_REDEAL = 0
UNLIMITED_REDEALS = -1
VARIABLE_REDEALS = -2

CARDSET = "cardset"

IMAGE_EXTENSIONS = (".gif", ".ppm",)
if 1 and os.name == "nt":
    ## #$unbundle#IMAGE_EXTENSIONS = (".png", ".gif", ".ppm", ".jpg",)
    IMAGE_EXTENSIONS = (".png", ".gif", ".ppm", ".jpg",)
    pass

try:
    bundle
except:
    bundle = 0

def get_version_tuple(version_string):
    v = re.split(r"[^\d\.]", version_string)
    if not v or not v[0]:
        return (0,)
    v = string.split(v[0], ".")
    v = filter(lambda x: x != "", v)
    if not v or not v[0]:
        return (0,)
    return tuple(map(int, v))


# /***********************************************************************
# // simple benchmarking
# ************************************************************************/

class Timer:
    def __init__(self, msg = ""):
        self.msg = msg
        self.clock = time.time
        if os.name == "nt":
            self.clock = time.clock
        self.start = self.clock()
    def reset(self):
        self.start = self.clock()
    def get(self):
        return self.clock() - self.start
    def __repr__(self):
        return "%-20s %6.3f seconds" % (self.msg, self.clock() - self.start)


# /***********************************************************************
# // DataLoader
# ************************************************************************/

class DataLoader:
    def __init__(self, argv0, filenames, path=[]):
        self.dir = None
        if type(filenames) is types.StringType:
            filenames = (filenames,)
        assert type(filenames) in (types.TupleType, types.ListType)
        #$ init path
        path = path[:]
        head, tail = os.path.split(argv0)
        if not head:
            head = os.curdir
        path.append(head)
        path.append(os.path.join(head, "data"))
        path.append(os.path.join(head, os.pardir, "data"))          #bundle#
        #$ you can add your extra directories here
        if os.name == "posix":
            pass
        if os.name == "nt":
            pass
        if os.name == "mac":
            pass
        #$ add standard Unix directories to search path
        if 1 and os.name == "posix":
            for v in (VERSION, ""):
                for prefix in ("@prefix@", "/usr/local", "/usr"):
                    try:
                        if os.path.isdir(prefix):
                            path.append(os.path.join(prefix,"share/pysol",v))
                            path.append(os.path.join(prefix,"lib/pysol",v))
                            path.append(os.path.join(prefix,"share/games/pysol",v))
                            path.append(os.path.join(prefix,"lib/games/pysol",v))
                            path.append(os.path.join(prefix,"games/share/pysol",v))
                            path.append(os.path.join(prefix,"games/lib/pysol",v))
                    except EnvError:
                        pass
        #$ check path for valid directories
        self.path = []
        for p in path:
            if not p: continue
            try:
                np = os.path.normpath(p)
                if np and (not np in self.path) and os.path.isdir(np):
                    self.path.append(np)
            except EnvError:
                pass
        #$ now try to find all filenames along path
        for p in self.path:
            n = 0
            for filename in filenames:
                try:
                    f = os.path.join(p, filename)
                    if os.path.isfile(f):
                        n = n + 1
                    else:
                        break
                except EnvError:
                    pass
            if n == len(filenames):
                self.dir = p
                break
        else:
            raise os.error, str(argv0) + ": DataLoader could not find " + str(filenames)
        ##print path, self.path, self.dir


    def __findFile(self, func, filename, subdirs=None, do_raise=1):
        if subdirs is None:
            subdirs = ("",)
        elif type(subdirs) is types.StringType:
            subdirs = (subdirs,)
        for dir in subdirs:
            f = os.path.join(self.dir, dir, filename)
            f = os.path.normpath(f)
            if func(f):
                return f
        if do_raise:
            raise os.error, "DataLoader could not find " + filename + " in " + self.dir + " " + str(subdirs)
        return None

    def findFile(self, filename, subdirs=None):
        return self.__findFile(os.path.isfile, filename, subdirs)

    def findImage(self, filename, subdirs=None):
        for ext in IMAGE_EXTENSIONS:
            f = self.__findFile(os.path.isfile, filename+ext, subdirs, 0)
            if f:
                return f
        raise os.error, "DataLoader could not find image " + filename + " in " + self.dir + " " + str(subdirs)

    def findIcon(self, filename=None, subdirs=None):
        if not filename:
            filename = string.lower(PACKAGE)
        root, ext = os.path.splitext(filename)
        if not ext:
            filename = filename + ".xbm"
        return self.findFile(filename, subdirs)

    def findDir(self, filename, subdirs=None):
        return self.__findFile(os.path.isdir, filename, subdirs)


# /***********************************************************************
# // memory util/debugging
# ************************************************************************/

cyclops = None

