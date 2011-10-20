__author__ = 'David V. Pynadath <pynadath@isi.edu>'
from xml.dom.minidom import *

from teamwork.agent.Generic import GenericModel
from teamwork.agent.Entities import *
from teamwork.multiagent.Multiagent import *
from teamwork.multiagent.GenericSociety import *

from ThespianGeneric import *
from ThespianAgents import *

class ThespianGenericSociety(GenericSociety):

    def __copyGeneric(self,generic):
        """Copies top-level generic values onto nested belief models"""
        for other in generic.getEntities():
            entity = generic.getEntity(other)
            if self.has_key(other):
                # Belief about another class in this society
                toExplore = [other]
                while len(toExplore) > 0:
                    cls = toExplore.pop()
                    if len(self[cls].models) > 0:
                        entity.models = self[cls].models
                        break
                    toExplore += self[cls].getParents()
                entity.dynamics = self[other].dynamics
                # Anything else to copy?
            # Descend recursively
            self.__copyGeneric(entity)

    def importDict(self,hierarchy):
        """Updates society from dictionary-style hierarchy"""
        # Read the separate models in
        for name,generic in hierarchy.items():
            if not name:
                # Ignore "None" entry?
                continue
            model = ThespianGenericModel(name)
            
            self[name] = model
##            model.hierarchy = self
            model.importDict(generic)
        # Tie up some connections among models
        for name,generic in self.items():
            self._copyGeneric(generic)

    

    def instantiate(self,className,instanceName,objClass=ThespianAgent):
        """Returns a new instantiated agent model

        className:    The string name of the relevant generic model
        instanceName: The string name for the new instance
        objClass:     (Optional) Class to create agent object from"""
        entity = objClass(instanceName)
        entity.applyDefaults(className,self)
        return entity

