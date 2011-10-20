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
import os, sys, string, types
import Tkinter, Canvas


# /***********************************************************************
# // patch lib-tk/Tkinter.py
# ************************************************************************/

# ignore self.tk.deletecommand() failures in Misc.destroy, or else the
# destruction of a (withdrawn & transient) toplevel may fail somewhere
# in the middle, possibly making Tk hang under Windows
def Misc__destroy(self):
    if self._tclCommands is not None:
        for name in self._tclCommands:
            try:
                self.tk.deletecommand(name)
                #print '- Tkinter: deleted command', name
            except:
                pass
        self._tclCommands = None

# fix Python 1.5.2 _tagcommands bug
def Canvas__tag_bind(self, tagOrId, sequence=None, func=None, add=None):
    return self._bind((self._w, "bind", tagOrId), sequence, func, add)

#
def Canvas__xview(self, *args):
    if not args:
        return self._getdoubles(self.tk.call(self._w, 'xview'))
    if args[0] == "moveto":
        return self.xview_moveto(float(args[1]))
    elif args[0] == "scroll":
        return self.xview_scroll(int(args[1]), args[2])
def Canvas__xview_moveto(self, fraction):
    fraction = max(fraction, 0.0)
    return self.tk.call(self._w, 'xview', 'moveto', fraction)
def Canvas__xview_scroll(self, number, what):
    if number < 0:
        v = self._getdoubles(self.tk.call(self._w, 'xview'))
        if v[0] <= 0.0001:
            return
    return self.tk.call(self._w, 'xview', 'scroll', number, what)
def Canvas__yview(self, *args):
    if not args:
        return self._getdoubles(self.tk.call(self._w, 'yview'))
    if args[0] == "moveto":
        return self.yview_moveto(float(args[1]))
    elif args[0] == "scroll":
        return self.yview_scroll(int(args[1]), args[2])
def Canvas__yview_moveto(self, fraction):
    fraction = max(fraction, 0.0)
    return self.tk.call(self._w, 'yview', 'moveto', fraction)
def Canvas__yview_scroll(self, number, what):
    if number < 0:
        v = self._getdoubles(self.tk.call(self._w, 'yview'))
        if v[0] <= 0.0001:
            return
    return self.tk.call(self._w, 'yview', 'scroll', number, what)

# fix missing "newstate" parm
def Wm__wm_state(self, newstate=None):
    return self.tk.call('wm', 'state', self._w, newstate)

# these are missing in class Text (probably some others as well)
def Text__xview_moveto(self, fraction):
    return self.tk.call(self._w, "xview", "moveto", fraction)
def Text__xview_scroll(self, number, what):
    return self.tk.call(self._w, "xview", "scroll", number, what)
def Text__yview_moveto(self, fraction):
    return self.tk.call(self._w, "yview", "moveto", fraction)
def Text__yview_scroll(self, number, what):
    return self.tk.call(self._w, "yview", "scroll", number, what)


Tkinter.Misc.destroy = Misc__destroy
Tkinter.Canvas.tag_bind = Canvas__tag_bind
Tkinter.Canvas.xview = Canvas__xview
Tkinter.Canvas.xview_moveto = Canvas__xview_moveto
Tkinter.Canvas.xview_scroll = Canvas__xview_scroll
Tkinter.Canvas.yview = Canvas__yview
Tkinter.Canvas.yview_moveto = Canvas__yview_moveto
Tkinter.Canvas.yview_scroll = Canvas__yview_scroll
Tkinter.Wm.wm_state = Wm__wm_state
Tkinter.Wm.state = Wm__wm_state                 # obsolete
Tkinter.Text.xview_moveto = Text__xview_moveto
Tkinter.Text.xview_scroll = Text__xview_scroll
Tkinter.Text.yview_moveto = Text__yview_moveto
Tkinter.Text.yview_scroll = Text__yview_scroll


# /***********************************************************************
# // patch lib-tk/Canvas.py
# ************************************************************************/

# fix inconsistent bbox() return value
def CanvasItem__bbox(self):
    return self.canvas.bbox(self.id)
def Group__bbox(self):
    return self.canvas.bbox(self.id)

# fix missing "add" parm
def CanvasItem__bind(self, sequence=None, command=None, add=None):
    return self.canvas.tag_bind(self.id, sequence, command, add)
def Group__bind(self, sequence=None, command=None, add=None):
    return self.canvas.tag_bind(self.id, sequence, command, add)

# fix missing "funcid" parm
def CanvasItem__unbind(self, sequence, funcid=None):
    return self.canvas.tag_unbind(self.id, sequence, funcid)
def Group__unbind(self, sequence, funcid=None):
    return self.canvas.tag_unbind(self.id, sequence, funcid)

# call tag_raise / tag_lower
def CanvasItem__tkraise(self, abovethis=None):
    return self.canvas.tag_raise(self.id, abovethis)
def CanvasItem__lower(self, belowthis=None):
    return self.canvas.tag_lower(self.id, belowthis)
def Group__tkraise(self, abovethis=None):
    return self.canvas.tag_raise(self.id, abovethis)
def Group__lower(self, belowthis=None):
    return self.canvas.tag_lower(self.id, belowthis)


# other problems in Canvas.Group:
#   - inconsistent usage of self.id and self.tag
#   - calls the obsolete Tkinter.Canvas._do method


Canvas.CanvasItem.bbox = CanvasItem__bbox
Canvas.Group.bbox = Group__bbox
Canvas.CanvasItem.bind = CanvasItem__bind
Canvas.Group.bind = Group__bind
Canvas.CanvasItem.unbind = CanvasItem__unbind
Canvas.Group.unbind = Group__unbind
Canvas.CanvasItem.tkraise = CanvasItem__tkraise
Canvas.CanvasItem.lower = CanvasItem__lower
Canvas.Group.tkraise = Group__tkraise
Canvas.Group.lower = Group__lower


# /***********************************************************************
# // PySol extra patches
# ************************************************************************/

# do not catch any exceptions in a Tkinter callback
def CallWrapper____call__(self, *args):
    if self.subst:
        args = apply(self.subst, args)
    return apply(self.func, args)

Tkinter.CallWrapper.__call__ = CallWrapper____call__

