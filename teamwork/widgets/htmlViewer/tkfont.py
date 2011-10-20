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
import Tkinter

# Toolkit imports
import tkinit
from tkconst import tkversion


# /***********************************************************************
# // font
# ************************************************************************/

getFont_cache = {}

def getFont(name, cardw=0):
    key = (name, cardw)
    font = getFont_cache.get(key)
    if font:
        return font
    # default
    font = ("Helvetica", "-14")
    #
    if name in ("canvas", "canvas_small", "small", "tree_small",):
        font = ("Helvetica", "-12")
    elif name in ("canvas_large",):
        font = ("Helvetica", "-18")
    elif name in ("canvas_card",):
        if cardw >= 71:
            font = getFont("canvas_large")
        elif cardw >= 57:
            font = ("Helvetica", "-16")
        else:
            font = ("Helvetica", "-14")
    elif name in ("canvas_fixed",):
        font = ("Courier", "-12")
    elif name in ("fixed",):
        font = ("Courier", "-14")
    elif not name in ("default",):
        pass
    #
    getFont_cache[key] = font
    return font

