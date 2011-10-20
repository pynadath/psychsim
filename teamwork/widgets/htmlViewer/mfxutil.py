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
import sys, os, operator, re, string, time, types, htmlentitydefs
import traceback

try:
    from cPickle import Pickler, Unpickler, UnpicklingError
except ImportError:
    from pickle import Pickler, Unpickler, UnpicklingError
thread = None
try:
    import thread
except:
    thread = None
if os.name == "mac":
    import macfs, MACFS
win32api = None

from mfxtools import *


# /***********************************************************************
# // exceptions
# ************************************************************************/

# work around a Mac problem
##EnvError = EnvironmentError
EnvError = (IOError, OSError, os.error,)


class SubclassResponsibility(Exception):
    pass


# /***********************************************************************
# // misc. util
# ************************************************************************/

def static(f, *args, **kw):
    if args:
        a = tuple([f.im_class()] + list(args))
    else:
        a = (f.im_class(),)
    return apply(f, a, kw)


def ifelse(expr, val1, val2):
    if expr:
        return val1
    return val2


def merge_dict(dict1, dict2, merge_none=1):
    for k, v in dict2.items():
        if dict1.has_key(k):
            if type(dict1[k]) is type(v):
                dict1[k] = v
            elif dict1[k] is None and merge_none:
                dict1[k] = v


# this is a quick hack - we definitely need Unicode support...
def latin1_to_ascii(n):
    ## FIXME: rewrite this for better speed
    n = string.replace(n, "\xc4", "Ae")
    n = string.replace(n, "\xd6", "Oe")
    n = string.replace(n, "\xdc", "Ue")
    n = string.replace(n, "\xe4", "ae")
    n = string.replace(n, "\xf6", "oe")
    n = string.replace(n, "\xfc", "ue")
    return n


htmlentitydefs_i = {}

def latin1_to_html(n):
    global htmlentitydefs_i
    if not htmlentitydefs_i:
        for k, v in htmlentitydefs.entitydefs.items():
            htmlentitydefs_i[v] = "&" + k + ";"
    s, g = "", htmlentitydefs_i.get
    for c in n:
        s = s + g(c, c)
    return s


def hexify(s):
    return "%02x"*len(s) % tuple(map(ord, s))


# /***********************************************************************
# // misc. portab stuff
# ************************************************************************/

def getusername():
    if os.name == "nt":
        return win32_getusername()
    user = string.strip(os.environ.get("USER",""))
    if not user:
        user = string.strip(os.environ.get("LOGNAME",""))
    return user


def gethomedir():
    if os.name == "nt":
        return win32_gethomedir()
    home = string.strip(os.environ.get("HOME", ""))
    if not home or not os.path.isdir(home):
        home = os.curdir
    return os.path.abspath(home)


def getprefdir(package, home=None):
    if os.name == "nt":
        return win32_getprefdir(package, appname, home)
    if os.name == "mac":
        vrefnum, dirid = macfs.FindFolder(MACFS.kOnSystemDisk, MACFS.kPreferencesFolderType, 0)
        fss = macfs.FSSpec((vrefnum, dirid, ":" + appname))
        return fss.as_pathname()
    if home is None:
        home = gethomedir()
    return os.path.join(home, "." + string.lower(package))


# high resolution clock() and sleep()
uclock = time.clock
usleep = time.sleep
if os.name == "posix":
    uclock = time.time


# /***********************************************************************
# // memory util
# ************************************************************************/

def destruct(obj):
    # assist in breaking circular references
    if obj is not None:
        assert type(obj) is types.InstanceType
        for k in obj.__dict__.keys():
            obj.__dict__[k] = None
            ##del obj.__dict__[k]


# /***********************************************************************
# //
# ************************************************************************/

class Struct:
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def __str__(self):
        return str(self.__dict__)

    def __setattr__(self, key, value):
        if not self.__dict__.has_key(key):
            raise AttributeError, key
        self.__dict__[key] = value

    def addattr(self, **kw):
        for key in kw.keys():
            if hasattr(self, key):
                raise AttributeError, key
        self.__dict__.update(kw)

    def update(self, dict):
        for key in dict.keys():
            if not self.__dict__.has_key(key):
                raise AttributeError, key
        self.__dict__.update(dict)

    def clear(self):
        for key in self.__dict__.keys():
            t = type(key)
            if t is types.ListType:
                self.__dict__[key] = []
            elif t is types.TupleType:
                self.__dict__[key] = ()
            elif t is types.DictType:
                self.__dict__[key] = {}
            else:
                self.__dict__[key] = None

    def copy(self):
        c = Struct()
        c.__class__ = self.__class__
        c.__dict__.update(self.__dict__)
        return c


# /***********************************************************************
# // keyword argument util
# ************************************************************************/

# update keyword arguments with default arguments
def kwdefault(kw, **defaults):
    for k, v in defaults.items():
        if not kw.has_key(k):
            kw[k] = v


class KwStruct:
    def __init__(self, kw={}, **defaults):
        if isinstance(kw, KwStruct):
            kw = kw.__dict__
        if isinstance(defaults, KwStruct):
            defaults = defaults.__dict__
        if defaults:
            kw = kw.copy()
            for k, v in defaults.items():
                if not kw.has_key(k):
                    kw[k] = v
        self.__dict__.update(kw)

    def __setattr__(self, key, value):
        if not self.__dict__.has_key(key):
            raise AttributeError, key
        self.__dict__[key] = value

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return self.__dict__.get(key, default)

    def getKw(self):
        return self.__dict__


# /***********************************************************************
# // pickling support
# ************************************************************************/

def pickle(obj, filename, binmode=0):
    f = None
    try:
        f = open(filename, "wb")
        p = Pickler(f, binmode)
        p.dump(obj)
        f.close(); f = None
        ##print "Pickled", filename
    finally:
        if f: f.close()


def unpickle(filename):
    f, obj = None, None
    try:
        f = open(filename, "rb")
        p = Unpickler(f)
        x = p.load()
        f.close(); f = None
        obj = x
        ##print "Unpickled", filename
    finally:
        if f: f.close()
    return obj


# /***********************************************************************
# //
# ************************************************************************/

def spawnv(file, args=()):
    if not args:
        args = ()
    args = (file,) + tuple(args)
    #
    if not os.path.isfile(file):
        raise os.error, str(file)
    mode = os.stat(file)[0]
    if not (mode & 0100):
        return 0
    #
    if os.name == "posix":
        pid = os.fork()
        if pid == -1:
            raise os.error, "fork failed"
        if pid != 0:
            # parent
            try:
                os.waitpid(pid, 0)
            except:
                pass
            return 1
        # child
        # 1) close all files
        for fd in range(255, -1, -1):
            try:
                os.close(fd)
            except:
                pass
        # 2) open stdin, stdout and stderr to /dev/null
        try:
            fd = os.open("/dev/null", os.O_RDWR)
            os.dup(fd)
            os.dup(fd)
        except:
            pass
        # 3) fork again and exec program
        try:
            if os.fork() == 0:
                try:
                    os.setpgrp()
                except:
                    pass
                os.execv(file, args)
        except:
             pass
        # 4) exit
        while 1:
            os._exit(0)
    return 0


def spawnvp(file, args=()):
    if file and os.path.isabs(file):
        try:
            if spawnv(file, args):
                return file
        except:
             ##if traceback: traceback.print_exc()
             pass
        return None
    #
    path = os.environ.get("PATH", "")
    path = string.splitfields(path, os.pathsep)
    for dir in path:
        try:
            if dir and os.path.isdir(dir):
                f = os.path.join(dir, file)
                try:
                    if spawnv(f, args):
                        return f
                except:
                    ##if traceback: traceback.print_exc()
                    pass
        except:
            ##if traceback: traceback.print_exc()
            pass
    return None


# /***********************************************************************
# //
# ************************************************************************/

__SOUND_MIXER = ()

def spawnSystemSoundMixer(query=0):
    global __SOUND_MIXER
    if query:
        return __SOUND_MIXER is not None
    MIXERS = ()
    if os.name == "posix":
        MIXERS = (("kmix", None), ("gmix", None),)
    for name, args in MIXERS:
        try:
            f = spawnvp(name, args)
            if f:
                __SOUND_MIXER = (f, args)
                return 1
        except:
            if traceback: traceback.print_exc()
            pass
    __SOUND_MIXER = None
    return 0


def spawnSystemDisplaySettings():
    if os.name == "nt":
        return win32_spawnSystemDisplaySettings()
    return 0


# /***********************************************************************
# //
# ************************************************************************/

def openURL(url):
    if os.name == "nt":
        return win32_openURL(url)
    if 0 and os.name == "posix":
        ns = (url,)
        ns = ("-remote", "openURL(" + url + ",new-window)",)
        BROWSERS = (
            ("kfmclient", ("openURL", url,)),
            ("netscape", ns),
            ("netscape4", ns),
            ("netscape3", ns),
            ("/opt/netscape-3.04/netscape304", ns),
            ("mozilla", (url,)),
            ("gnome-help-browser", (url,)),
        )
        for name, args in BROWSERS:
            try:
                ##print name, args
                if spawnvp(name, args):
                    return 1
            except:
                pass
    return 0


# /***********************************************************************
# // memory debugging
# ************************************************************************/


def dumpmem(dump_all_objects=1):
    var = {}
    if dump_all_objects:
        for m in sys.modules.keys():
            mod = sys.modules[m]
            if mod:
                for k in mod.__dict__.keys():
                    v = mod.__dict__[k]
                    if type(v) in (types.ClassType, types.InstanceType):
                        var[k] = v
    else:
        for k, v in vars().items() + globals().items():
            var[k] = v
    info = []
    for k in var.keys():
        n = sys.getrefcount(var[k])
        v = var[k]
        if type(v) is types.ClassType:
            ## FIXME: we must subtract the number of methods
            ## FIXME: we must also subtract the number of subclasses
            pass
        if n > 3:
            # we seem to create 3 (???) extra references while in this function
            info.append(n - 3, k, v)
        var[k] = None
    var = None
    info.sort()
    info.reverse()
    sum = 0
    for count, varname, value in info:
        sum = sum + count
        if type(value) in (
            types.InstanceType, types.ModuleType, types.ClassType,
            types.NoneType, types.FunctionType, types.StringType
            ):
            valuestr = repr(value)[:40]
        else:
            valuestr = "n/a"
        print "%7d %-25s %s" % (count, varname, valuestr)
    print "%7d ---TOTAL---" % (sum)



# /***********************************************************************
# // debugging
# ************************************************************************/


def callername():
    try:
        raise Exception
    except:
        return sys.exc_traceback.tb_frame.f_back.f_back.f_code.co_name

def callerglobals():
    try:
        raise Exception
    except:
        return sys.exc_traceback.tb_frame.f_back.f_back.f_globals

def uplevel(name):
    print __name__, callerglobals()[name], callerglobals()["__name__"]


