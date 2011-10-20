"""Collection of inter-related L{teamwork.agent.Generic.GenericModel} instances
@author: David V. Pynadath <pynadath@isi.edu>
"""
from teamwork.agent.Generic import GenericModel
from teamwork.agent.Entities import PsychEntity
from teamwork.multiagent.Multiagent import MultiagentSystem
from xml.dom.minidom import parseString

class GenericSociety(MultiagentSystem):
    """A taxonomy of generic agent models

    In essence, a generic society is simply a dictionary of L{GenericModel}
    objects.  You can manipulate the society through the following operations:

       0. Creating a new society:
            - C{society = L{GenericSociety}()}

       1. Insert/overwrite a generic model:
            - C{society.L{addMember}(model)}

       2. Get a generic model by name
            - C{model = society[name]}

       3. Get a list of model objects:
            - C{society.L{members}()}

       4. Get a list of names of leaf nodes
            - C{society.L{leaves}()}

       5. Get a list of leaf node model objects
            - C{society.L{leafModels}()}

       6. Delete a generic model
            - C{del society[model.name]}

       7. Get a list of model names:
            - C{society.keys()}

       8. Get a list of (name,model) tuples
            - C{society.items()}

       9. Create an instantiated agent model of a particular class
            - C{entity = society.L{instantiate}(className,instanceName)}

    @ivar network: a dictionary representation of the descendent relationships in this society
    @ivar root: a list of all of the root models in this society
    """
    def __init__(self,agents=[]):
        """Initializes a collection to contain the given list of agents"""
        MultiagentSystem.__init__(self,agents)
        self._keys = self.keys()
        self._keys.sort()
        self.turns = {}
        self.network = {}
        self.root = []
        
    def addMember(self,agent):
        """Adds the agent to this collection
        @param agent: the agent to add
        @type agent: L{teamwork.agent.Agent}
        @warning: will clobber any pre-existing agent with the same name
        """
        MultiagentSystem.addMember(self,agent)
        agent.setHierarchy(self)
        try:
            # We could test whether it's parallel, but what the heck
            self._keys[0].append(agent.name)
        except IndexError:
            # I guess we were wrong
            self._keys.insert(0,agent.name)
        except AttributeError:
            # I guess we were wrong
            self._keys.insert(0,agent.name)
        self.network[agent.name] = []
        if len(agent.getParents()) == 0:
            self.root.append(agent.name)
            self.root.sort()
        for name in agent.getParents():
            try:
                self.network[name].append(agent.name)
                self.network[name].sort()
            except KeyError:
                pass
        for name in self.network.keys():
            if agent.name in self[name].getParents():
                self.network[agent.name].append(name)
        self.network[agent.name].sort()
        # Add generic beliefs to other agents
        for name in self.keys():
            if self[name].depth > 0 and not self[name].entities.has_key(agent.name):
                self[name].initializeModel(agent)
            if agent.depth > 0 and not agent.entities.has_key(name):
                agent.initializeModel(self[name])

    def renameEntity(self,old,new):
        """
        @param old: the current name of the member
        @param new: the new name of the member
        @type old,new: str
        """
        try:
            # Maybe it's serial?
            self._keys.index(old)
            agent = self[old]
            index = self._keys.index(old)
            self._keys.insert(index,new)
        except ValueError:
            # Nope
            for names in self._keys:
                try:
                    names.remove(old)
                    names.append(new)
                    break
                except ValueError:
                    pass
        self[new] = agent
        for agent in self.members():
            agent.renameEntity(old,new)
        # Update network
        self.network[new] = self.network[old]
        for names in self.network.values():
            if old in names:
                names.append(new)
        if old in self.root:
            self.root.append(new)
        del self[old]
            
    def merge(self,society):
        """Merges the contents of a new society into this one
        """
        warnings = []
        for name,entity in society.items():
            if self.has_key(name):
                warnings += self[name].merge(entity)
            else:
                self.addMember(entity)
        for name,entity in society.items():
            if len(entity.getParents()) == 0:
                self.root.append(entity.name)
                self.root.sort()
            for parent in entity.getParents():
                if not name in self.network[parent]:
                    self.network[parent].append(name)
                    self.network[parent].sort()
        return warnings

    def descendents(self,name):
        """
        @return: the names of the given entity and all of its descendents in the hierarchy
        @rtype: str[]
        """
        result = {}
        remaining = [name]
        while len(remaining) > 0:
            current = remaining.pop(0)
            result[current] = True
            remaining += self.network[current]
        return result.keys()

    def __delitem__(self,name):
        MultiagentSystem.__delitem__(self,name)
        for agent in self.members():
            del agent.entities[name]
            try:
                agent.parentModels.remove(name)
            except ValueError:
                # Not a parent
                pass
        try:
            # Assume serial
            self._keys.remove(name)
        except ValueError:
            # Oh well
            for names in self._keys:
                try:
                    names.remove(name)
                    break
                except ValueError:
                    pass
        del self.network[name]
        try:
            self.root.remove(name)
        except ValueError:
            pass
        for names in self.network.values():
            try:
                names.remove(name)
            except ValueError:
                pass
        
    def __xml__(self):
        doc = MultiagentSystem.__xml__(self)
        node = doc.createElement('order')
        if self._keys and isinstance(self._keys[0],list):
            node.setAttribute('serial','0')
        else:
            node.setAttribute('serial','1')
        for index in range(len(self._keys)):
            if isinstance(self._keys[index],str):
                names = [self._keys[index]]
            else:
                names = self._keys[index]
            for name in names:
                child = doc.createElement('turn')
                child.setAttribute('name',name)
                child.setAttribute('position',str(index))
                node.appendChild(child)
        doc.documentElement.appendChild(node)
        return doc
        
    def parse(self,element):
        """Extracts society elements from the provided XML Document"""
        MultiagentSystem.parse(self,element,GenericModel)
        for agent in self.members():
            agent.setHierarchy(self)
        # Extract turn order
        indices = {}
        child = element.firstChild
        serial = True
        while child:
            if child.nodeType == child.ELEMENT_NODE:
                if child.tagName == 'order':
                    serial = str(child.getAttribute('serial')) != '0'
                    children = child.getElementsByTagName('turn')
                    for node in children:
                        name = str(node.getAttribute('name'))
                        index = int(node.getAttribute('position'))
                        indices[name] = index
            child = child.nextSibling
        # Unpack turn order results
        if serial:
            if max(indices.values()) >= len(self):
                # Position information out of whack.  A sad day for humanity
                self._keys = self.keys()
                self._keys.sort(lambda x,y: cmp(indices[x],indices[y]))
            else:
                self._keys = map(lambda i: None,range(len(self)))
                for name,position in indices.items():
                    self._keys[position] = name
                self._keys = filter(lambda k: not k is None,self._keys)
        else:
            self._keys = map(lambda i: [],range(len(self)))
            for name,position in indices.items():
                self._keys[position].append(name)
        self._keys = filter(lambda l: len(l),self._keys)
        # Check for obsolete links
        for agent in self.members():
            for relation in agent.getLinkTypes():
                for name in agent.getLinkees(relation):
                    if not self.has_key(name):
                        agent.removeLink(relation,name)
##        count = {'generic actions':0,'specific actions':0,
##                 'generic dynamics': 0,'specific dynamics':0,
##                 'player effects':0,'NPC effects':0,
##                 'NPC decision':0}
##        for agent in self.members():
##            count['generic actions'] += len(agent.actions.getOptions())
##            count['generic dynamics'] += sum(map(len,agent.dynamics.values()))
##            if len(self.descendents(agent.name)) == 1:
##                actions = filter(lambda a: not agent.actions.illegal.has_key(str(a)),
##                                 agent.getAllFillers('action'))
##                count['specific actions'] += len(actions)
##                biggest = 0
##                for action in actions:
##                    effects = 0
##                    for other in self.members():
##                        for feature,table in other.dynamics.items():
##                            if table.has_key(action[0]['type']):
##                                count['specific dynamics'] += 1
##                                effects += 1
##                                if not agent.isSubclass('Player'):
##                                    count['NPC decision'] += 1
##                    biggest = max(biggest,effects)
##                if agent.isSubclass('Player'):
##                    count['player effects'] += biggest
##                else:
##                    count['NPC effects'] += biggest
##        print count
####        exit()

    def importDict(self,hierarchy,modelClass=None):
        """Updates society from dictionary-style hierarchy
        @param hierarchy: the specification of the generic society
        @type hierarchy: C{dict}
        @param modelClass: the class for the individual generic agent models (default is L{GenericModel}
        @type modelClass: C{class}
        """
        if not modelClass:
            modelClass = GenericModel
        # Read the separate models in
        for name,generic in hierarchy.items():
            if not name:
                # Ignore "None" entry?
                continue
            model = modelClass(name)
            self.addMember(model)
            model.importDict(generic)
        # Tie up some connections among models
        for name,generic in self.items():
            self.__copyGeneric(generic)

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

    def leaves(self):
        """Returns a list of generic model names that are leaf nodes"""
        leaves = self.keys()
        for model in self.values():
            for parent in model.getParents():
                try:
                    leaves.remove(parent)
                except ValueError:
                    pass
        return leaves
        
    def leafModels(self):
        """Returns a list of generic model objects that are leaf nodes"""
        return map(lambda name,s=self:s[name], self.leaves())

    def instantiate(self,className,instanceName,objClass=None):
        """Returns a new instantiated agent model
        @param className: name of the relevant generic model
        @type className: C{str}
        @param instanceName: name for the new instance
        @type instanceName: C{str}
        objClass: class to create agent object from (defaults to L{PsychEntity})
        """
        if not objClass:
            objClass = PsychEntity
        if not self.has_key(className):
            raise UserWarning,'Unknown class: %s' % (className)
        entity = objClass(instanceName)
        entity.applyDefaults(className,self)
        entity.society = self
        return entity

def loadSociety(filename):
    """
    Loads a society from the given filename
    @return: the scenario
    @rtype: L{GenericSociety}
    """
    import bz2

    f = bz2.BZ2File(filename,'r')
    data = f.read()
    f.close()
    doc = parseString(data)
    society = GenericSociety()
    society.parse(doc.documentElement)
    return society

if __name__ == '__main__':
    import sys
    import bz2
    from xml.dom.minidom import parseString

    f = bz2.BZ2File(sys.argv[1],'r')
    data = f.read()
    f.close()

    try:
        key = sys.argv[2].lower()
    except IndexError:
        key = ''

    doc = parseString(data)
    newClasses = GenericSociety()
    newClasses.parse(doc.documentElement)

    names = newClasses.keys()
    names.sort(lambda x,y:cmp(x.lower(),y.lower()))

    for name in names:
        entity = newClasses[name]
        if key[:5] == 'state':
            for feature in entity.getStateFeatures():
                print '%s,%s,%5.3f' % (name,feature,entity.getState(feature))
        elif key[:6] == 'action':
            for action in entity.actions.getOptions():
                if action[0]['object']:
                    print '%s,%s,%s' % (name,action[0]['type'],
                                        action[0]['object'])
                else:
                    print '%s,%s,' % (name,action[0]['type'])
        elif key[:8] == 'relation':
            for relation in entity.getLinkTypes():
                for other in entity.getLinkees(relation):
                    print '%s,%s,%s,%5.3f' % (name,relation,other,
                                              entity.getLink(relation,other))
        elif key[:6] == 'leaves':
            if name in newClasses.leaves():
                print name
        elif key[:6] == 'static':
            for relation,fillers in entity.relationships.items():
                for other in fillers:
                    print '%s,%s,%s' % (name,relation,other)
        elif key[:5] == 'neigh':
            if 'Neighborhood' in entity.getParents():
                print name
        else:
            print name
