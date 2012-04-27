from xml.dom.minidom import Document,Node

class Action(dict):
    def __init__(self,arg={}):
        if isinstance(arg,Node):
            dict.__init__(self)
            self.parse(arg)
        else:
            dict.__init__(self,arg)
        self._string = None
        

    def __setitem__(self,key,value):
        self._string = None
        dict.__setitem__(self,key,value)

    def clear(self):
        self._string = None
        dict.clear(self)

    def __str__(self):
        if self._string is None:
            elements = []
            keys = self.keys()
            for special in ['subject','verb','object']:
                if self.has_key(special):
                    elements.append(self[special])
                    keys.remove(special)
            keys.sort()
            elements += map(lambda k: self[k],keys)
            self._string = '-'.join(elements)
        return self._string

    def __hash__(self):
        return hash(str(self))

    def __xml__(self):
        doc = Document()
        root = doc.createElement('action')
        doc.appendChild(root)
        for key,value in self.items():
            node = doc.createElement('entry')
            node.setAttribute('key',key)
            node.appendChild(doc.createTextNode(value))
            root.appendChild(node)
        return doc

    def parse(self,element):
        assert element.tagName == 'action'
        self.clear()
        child = element.firstChild
        while child:
            if child.nodeType == child.ELEMENT_NODE:
                assert child.tagName == 'entry'
                key = str(child.getAttribute('key'))
                subchild = child.firstChild
                while subchild.nodeType != subchild.TEXT_NODE:
                    subchild = subchild.nextSibling
                value = str(subchild.data).strip()
                self[key] = value
            child = child.nextSibling
    
class ActionSet(set):
    def __init__(self,iterable=[]):
        if isinstance(iterable,Node):
            set.__init__(self)
            self.parse(iterable)
        else:
            set.__init__(self,iterable)
        self._string = None

    def clear(self):
        set.clear(self)
        self._string = None

    def add(self,element):
        set.add(self,element)
        self._string = None
        
    def __str__(self):
        if self._string is None:
            self._string = ','.join(map(str,self))
        return self._string

    def __hash__(self):
        return hash(str(self))

    def __xml__(self):
        doc = Document()
        root = doc.createElement('option')
        doc.appendChild(root)
        for atom in self:
            root.appendChild(atom.__xml__().documentElement)
        return doc

    def parse(self,element):
        assert element.tagName == 'option'
        self.clear()
        node = element.firstChild
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                assert node.tagName == 'action'
                self.add(Action(node))
            node = node.nextSibling
