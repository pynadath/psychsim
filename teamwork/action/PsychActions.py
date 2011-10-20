import copy
import string
from xml.dom.minidom import Document,parse

class Action(dict):
    nop = 'wait'
    fields = {'type':{},'actor':{},'object':{},'command':{},
              '_observed':{},'_unobserved':{},
              'self':bool ,
              'repeatable':bool ,
              }
    format = ['actor','type','object','command']
    
    def __init__(self,arg={}):
        if isinstance(arg,str):
            raise DeprecationWarning,'PsychAction: Use dictionaries instead of strings (%s) in action creation' % (arg)
        if len(arg) == 0:
            dict.__init__(self,{'type': self.nop})
        else:
            dict.__init__(self,arg)
        if self['actor'] and not isinstance(self['actor'],str):
            raise TypeError
        if self['object'] and not isinstance(self['object'],str):
            raise TypeError
        self.name = ''

        
    def instantiate(self,entities=[]):
        if isinstance(entities,dict):
            for key in self.fields.keys():
                if entities.has_key(key):
                    self[key] = entities[key]
        elif isinstance(entities,list):
            for key in self.fields.keys():
                for entity in entities:
                    try:
                        if entity.name == self[key]:
                            self[key] = entity
                            break
                    except AttributeError:
                        pass
        else:
            raise TypeError,`type(entities)`+' not supported by '+\
                  'PsychAgents instantiate method'
        if self['command']:
            self['command'].instantiate(entities)

    def makeRange(self,actType={}):
        """Returns a list of all possible instantiations of this
        partially specified action."""
        actList = [self]
        for key,value in self.fields.items():
            if not self[key]:
                try:
                    valRange = actType[key]
                except KeyError:
                    try:
                        valRange = value['range']
                    except KeyError:
                        continue
                if len(valRange) > 0:
                    for oldAct in actList[:]:
                        actList.remove(oldAct)
                        for item in valRange:
                            newAct = copy.copy(oldAct)
                            newAct[key] = item
                            actList.append(newAct)
        return actList

    def addField(self,key,value):
        """@return: a I{copy} of this action with the given key,value pair
        @rtype: L{Action}"""
        new = self.__copy__()
        new[key] = value
        return new
    
    def __getitem__(self,index):
        if self.fields.has_key(index):
            try:
                return dict.__getitem__(self,index)
            except KeyError:
                return None
        else:
            raise KeyError,'%s: Unknown field "%s"' \
                  % (self.__class__.__name__,index)
            
    def __setitem__(self,index,value):
        if self.fields.has_key(index):
            dict.__setitem__(self,index,value)
        else:
            raise KeyError,'%s: Unknown field "%s"' \
                  % (self.__class__.__name__,index)
        self.name = ''
            
    def __delitem__(self,index):
        if self.fields.has_key(index):
            self[index] = None
        else:
            raise KeyError,'%s: Unknown field "%s"' \
                  % (self.__class__.__name__,index)
        self.name = ''

    def keys(self):
        list = []
        for key in self.fields.keys():
            if self[key]:
                list.append(key)
        return list

    def __deepcopy__(self,memo):
        result = {}
        for key,value in self.items():
            if isinstance(value,Action):
                result[key] = copy.copy(value)
            elif isinstance(value,str):
                result[key] = value
            else:
                try:
                    result[key] = value.name
                except AttributeError:
                    result[key] = value
        result = self.__class__(result)
        memo[id(self)] = result
        return result
    
    def __str__(self):
        """Translates a structured dictionary representation of an action
        into a standardized string format (e.g.,
        {'actor':CLF,'type':'violence','object':UrbanPoor} becomes
        'CLF-violence-UrbanPoor'"""
        if len(self.name) == 0:
            for key in self.format:
                value = self[key]
                if value is None:
                    continue
                if len(self.name) > 0:
                    self.name += '-'
                if isinstance(value,str):
                    self.name += value
                elif isinstance(value,Action):
                    self.name += `value`
                elif isinstance(value,float):
                    self.name += '%6.4f' % (value)
                else:
                    self.name += value.name
        return self.name

    def simpleText(self):
        content = self['type']
        if isinstance(self['object'],str):
            content += ' %s' % (self['object'])
        elif not self['object'] is None:
            content += ' %s' % (self['object'].name)
        return content

    def matchTemplate(self,template):
        """
        @return: true iff the action matches the given template
        @rtype: bool
        """
        for key in self.fields:
            if template.has_key(key) and template[key]:
                if isinstance(self[key],str):
                    if template[key] != self[key]:
                        # Mismatch
                        break
#                elif isinstance(self[key],Agent):
#                    if template[key] != self[key].name:
#                        # Mismatch
#                        break
                else:
                    print 'Unable to match template fields of type:',self[key].__class__.__name__
        else:
            # Successful match
            return True
        return False

    def __xml__(self):
        doc = Document()
        root = doc.createElement('action')
        root.setAttribute('class',self.__class__.__name__)
        doc.appendChild(root)
        for key,value in self.items():
            if value is not None:
                if isinstance(value,str):
                    data = doc.createTextNode(value)
#                elif isinstance(value,Agent):
#                    data = doc.createTextNode(value.name)
                elif isinstance(value,Action):
                    data = value.__xml__().documentElement
                elif isinstance(value,bool):
                    data = doc.createTextNode(str(value))
                else:
                    # Not XMLizable
                    data = None
##                     data = doc.createTextNode(`value`)
                if not data is None:
                    node = doc.createElement(key)
                    root.appendChild(node)
                    node.appendChild(data)
        return doc

    def parse(self,doc):
        if doc.nodeType == doc.DOCUMENT_NODE:
            root = doc.documentElement
        else:
            root = doc
        clsName = str(root.getAttribute('class'))
        if clsName and clsName != self.__class__.__name__:
            for cls in self.__class__.__subclasses__():
                if clsName == cls.__name__:
                    obj = cls()
                    return obj.parse(doc)
            else:
                raise NameError,'Unknown Action subclass: %s' % (clsName)
        child = root.firstChild
        while child:
            if child.nodeType == child.ELEMENT_NODE:
                key = str(child.tagName)
                grandchild = child.firstChild
                if grandchild and grandchild.nodeType == grandchild.TEXT_NODE:
                    value = string.strip(str(child.firstChild.data))
                    if self.fields.has_key(key):
                        if self.fields[key] is bool:
                            if value == 'True':
                                value = True
                            else:
                                value = False
                        self[key] = value
            child = child.nextSibling
        return self

    def __hash__(self):
        return str(self).__hash__()
    
class ActionCondition:
    """
    Class for specifying a template for matching joint actions
    @ivar verbs: dictionary of verbs that this condition matches
    @type verbs: strS{->}C{True}
    @ivar only: C{True} iff only actions in the verb set are allowed (default is C{False})
    @type only: bool
    @ivar count: C{True} iff we are interested in how many actions match, not just a boolean value (default is C{False})
    @type count: bool
    """
    def __init__(self,only=False,count=False):
        self.verbs = {}
        self.only = only
        self.count = count

    def addCondition(self,verb):
        self.verbs[verb] = True

    def delCondition(self,verb):
        del self.verbs[verb]

    def __len__(self):
        return len(self.verbs)

    def match(self,actions):
        """
        @return: If C{self.count} is C{False}, then return C{True} iff the given joint action meets this condition; otherwise, return number of matching actions, or 0 if match fails
        @rtype: bool or int
        """
        if isinstance(actions,dict):
            # Dictionary of agent->action lists
            actions = sum(actions.values(),[])
        match = {} # Verbs found so far
        if self.only:
            # Check whether there are any extra actions
            for action in actions:
                if self.verbs.has_key(action['type']):
                    match[action['type']] = True
                elif self.count:
                    return 0
                else:
                    return False
            # All actions match, comes down to numbers
            if self.count:
                return len(actions)
            else:
                return len(match) == len(self.verbs)
        elif self.count:
            # Count how many desired verbs are present
            count = 0
            for action in actions:
                if self.verbs.has_key(action['type']):
                    match[action['type']] = True
                    count += 1
            if len(match) == len(self.verbs):
                return count
            else:
                return 0
        else:
            # Check whether all desired verbs are present
            index = 0
            while len(match) < len(self.verbs):
                if index < len(actions):
                    if self.verbs.has_key(actions[index]['type']):
                        match[actions[index]['type']] = True
                    index += 1
                else:
                    # Get out of here as quickly as possible
                    break
            # Check whether we have matched 
            return len(match) == len(self.verbs)

    def __eq__(self,other):
        if self.only != other.only:
            return False
        elif len(self.verbs) != len(other.verbs):
            return False
        else:
            for verb in self.verbs.keys():
                if not other.verbs.has_key(verb):
                    return False
            else:
                return True

    def __str__(self):
        if self.only:
            return 'Only '+','.join(self.verbs.keys())
        elif len(self.verbs) == 0:
            return 'Any'
        else:
            return ','.join(self.verbs.keys())

    def __xml__(self):
        doc = Document()
        root = doc.createElement('condition')
        doc.appendChild(root)
        root.setAttribute('only',str(self.only))
        root.setAttribute('count',str(self.count))
        for verb in self.verbs.keys():
            if self.verbs[verb]:
                node = doc.createElement('verb')
                node.appendChild(doc.createTextNode(verb))
                root.appendChild(node)
        return doc

    def parse(self,element):
        self.verbs.clear()
        self.only = str(element.getAttribute('only')).lower() == 'true'
        self.count = str(element.getAttribute('count')).lower() == 'true'
        node = element.firstChild
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                assert str(node.tagName) == 'verb'
                child = node.firstChild
                while child:
                    if child.nodeType == child.TEXT_NODE:
                        self.verbs[str(child.data).strip()] = True
                    child = child.nextSibling
            node = node.nextSibling

            
if __name__ == '__main__':
    import os.path
    

    act = Action({'actor':'CortinaGov','type':'wait'})
    name = '/tmp/%s.xml' % (os.path.basename(__file__))
    file = open(name,'w')
    file.write(act.__xml__().toxml())
    file.close()

    new = Action()
    new.parse(parse(name))
    print new
    
