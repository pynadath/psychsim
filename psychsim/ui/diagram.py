import random
from xml.dom.minidom import Document,Node
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

class Diagram:
    """
    Information for a diagram view of a L{psychsim.world.World}
    """
    def __init__(self,args=None):
        self.x = {}
        self.y = {}
        self.color = {}
        if isinstance(args,Node):
            self.parse(args)

    def getX(self,key):
        try:
            return self.x[key]
        except KeyError:
            return None

    def getY(self,key):
        try:
            return self.y[key]
        except KeyError:
            return None
    
    def getColor(self,key):
        """
        @warning: if no color exists, assigns a random color
        """
        if not key in self.color:
            self.color[key] = QColor(random.choice(QColor.colorNames()))
        return self.color[key]

    def setColor(self,key,value):
        if not isinstance(value,QColor):
            value = QColor(value)
        self.color[key] = value

    def clear(self):
        self.x.clear()
        self.y.clear()
        
    def __xml__(self):
        doc = Document()
        root = doc.createElement('diagram')
        for key,value in self.x.items():
            node = doc.createElement('x')
            node.setAttribute('key',key)
            node.appendChild(doc.createTextNode(str(value)))
            root.appendChild(node)
        for key,value in self.y.items():
            node = doc.createElement('y')
            node.setAttribute('key',key)
            node.appendChild(doc.createTextNode(str(value)))
            root.appendChild(node)
        for key,value in self.color.items():
            node = doc.createElement('color')
            if key:
                node.setAttribute('key',key)
            node.appendChild(doc.createTextNode(str(value.name())))
            root.appendChild(node)
        doc.appendChild(root)
        return doc

    def parse(self,root):
        assert root.tagName == 'diagram'
        node = root.firstChild
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                key = str(node.getAttribute('key'))
                if not key:
                    key = None
                if node.tagName == 'x':
                    self.x[key] = float(node.firstChild.data)
                elif node.tagName == 'y':
                    self.y[key] = float(node.firstChild.data)
                elif node.tagName == 'color':
                    self.setColor(key,str(node.firstChild.data).strip())
                else:
                    raise NameError('Unknown element %s when parsing %s' % \
                        (node.tagName,self.__class__.__name__))
            node = node.nextSibling
