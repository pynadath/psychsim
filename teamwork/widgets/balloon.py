from getpass import getuser
import time
import Pmw
from teamwork.agent.audit import Auditor

class EntityBalloon(Pmw.Balloon):
    """Minor augmentation of the PMW Balloon help system that allows one to
    easily update balloon strings associated with entity histories"""
    
    def __init__(self, parent = None, **kw):
        """Identical to the PMW Balloon class initialization, except that it
        also initializes the table of managed widgets"""
        Pmw.Balloon.__init__(self,parent,**kw)
        self.bindings = {}
        
    def add(self,widget,entity,key):
        """Adds the given widget to the handling of this balloon help system
        and associates it with the given entity and state/goal name"""
        if isinstance(entity,Auditor):
            history = entity.getHistory(key)
            try:
                str = history[0]
            except IndexError:
                # Initialize history
                from getpass import getuser
                entry = {'what':'initialized',
                         'who':getuser(),
                         'when':time.time()
                         }
                entity.extendHistory(entry)
                str = entity.formatHistory(entry)
            self.bind(widget,str)
            self.bindings[widget] = (entity,key)
        else:
            # Just plain old tooltip
            self.bind(widget,key)

    def update(self,widget=None):
        """Updates the balloon help of all of the known widgets"""
        if widget:
            self.__update(widget)
        else:
            for widget in self.bindings.keys():
                self.__update(widget)

    def __update(self,widget):
        """Updates the balloon help of the specified widget"""
        entity,key = self.bindings[widget]
        str = entity.getHistory(key)[0]
        self.bind(widget,str)

    def __delete(self,widget):
        del self.bindings[widget]

    def delete(self,widget=None):
        if widget:
            self.__delete(widget)
        else:
            for widget in self.bindings.keys():
                self.__delete(widget)
