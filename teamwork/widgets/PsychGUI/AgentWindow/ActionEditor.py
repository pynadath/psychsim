import string
from Tkinter import *
import Pmw
from teamwork.widgets.TreeEditor import TreeEditor

class ActionEditor(TreeEditor):
    
    def __init__(self,parent,**kw):
        optiondefs = (
            ('entity', None, Pmw.INITOPT),
            )
        self.defineoptions(kw, optiondefs)
        TreeEditor.__init__(self,parent)
        widget = self.createcomponent('Entry',(),None,
                                      Pmw.EntryField,
                                      (self.pane('editorPane'),),
                                      )
        widget.pack_forget()
        self.component('box').add('Test...',command=self.generate)
        self.configure(tree=self['entity'].actions)
        self.initialiseoptions()

    def setLeaf(self,leafType):
        tree = self.selectedTree()
        if leafType == 'relationship':
            widget = self.component('feature0')
            widget.setitems(self['entity'].getRelationships())
            widget.pack(fill='x')
            widget.configure(menubutton_state='normal')
            if tree.split == leafType:
                widget.invoke(tree._children[0])
            widget = self.component('feature1')
            widget.setitems(['object'])
            widget.pack(fill='x')
            widget.configure(menubutton_state='normal')
            if tree.split == leafType:
                widget.invoke(tree.key)
            self.component('Entry').pack_forget()
        elif leafType == 'generic':
            widget = self.component('feature0')
            itemList = self['entity'].hierarchy.keys()
            itemList.sort()
            widget.setitems(itemList)
            widget.pack(fill='x')
            widget.configure(menubutton_state='normal')
            if tree.split == leafType:
                widget.invoke(tree._children[0])
            widget = self.component('feature1')
            widget.setitems(['object'])
            widget.pack(fill='x')
            widget.configure(menubutton_state='normal')
            if tree.split == leafType:
                widget.invoke(tree.key)
            self.component('Entry').pack_forget()
        elif leafType == 'literal':
            self.component('feature1').pack_forget()
            widget = self.component('feature0')
            widget.setitems(['object','type'])
            widget.pack(fill='x')
            widget.configure(menubutton_state='normal')
            if tree.split == leafType:
                widget.invoke(tree.key)
            widget = self.component('Entry')
            widget.pack(after=self.component('feature0'),side='top',
                        fill='x',expand='yes')
            if tree.split == leafType:
                widget.setvalue(tree._children[0])
        else:
            raise NotImplementedError,'Unable to edit leaves of type %s' % \
                  (leafType)
            
    def setBranch(self,rowType):
        self.component('feature0').pack_forget()
        self.component('feature1').pack_forget()
        self.component('Entry').pack_forget()

    def selectLeaf(self):
        names = ['generic','literal','relationship']
        self.component('type').setitems(names)
        tree = self.selectedTree()
        self.component('type').invoke(tree.split)

    def selectBranch(self):
        self.component('type').setitems(['AND','OR','XOR'])
        tree = self.selectedTree()
        self.component('type').invoke(tree.split)

    def apply(self):
        tree = self.selectedTree()
        if tree.isLeaf():
            tree.split = self.component('type').getvalue()
            if tree.split == 'literal':
                tree.key = self.component('feature0').getvalue()
                tree._children[0] = self.component('Entry').getvalue()
            else:
                tree.key = self.component('feature1').getvalue()
                tree._children[0] = self.component('feature0').getvalue()
            print tree
            name = self.displayLeaf(tree.getValue())
            self.selection().var.set(name)
        else:
            tree.split = self.component('type').getvalue()
            name = self.displayPlane(tree.split)
            self.selection().var.set(name)
            
    def generate(self):
        tree = self.selectedTree()
        if tree:
            tree.generateOptions(debug=True)
            actions = tree.getOptions()
        else:
            actions = self['entity'].actions.getOptions()
        if len(actions) == 0:
            msg = 'No actions.'
        else:
            msg = string.join(map(lambda a:str(a),actions),'\n')
        dialog = Pmw.MessageDialog(self.component('hull'),
                                   title='Actions for %s' % \
                                   (self['entity'].ancestry()),
                                   message_text=msg)
        dialog.activate()

    def addBranch(self):
        tree = self.selectedTree()
        node = self.selection()
        if tree.isLeaf():
            pass
        else:
            pass
        
    def deleteNode(self):
        tkMessageBox.showerror('Delete Node','Not implemented')
