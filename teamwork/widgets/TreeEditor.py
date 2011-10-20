#from teamwork.math.KeyedMatrix import *
#from teamwork.math.KeyedTree import *

from Tkinter import Label,Scrollbar
import Pmw

from teamwork.widgets.TreeWidget import EasyTree

class TreeEditor(Pmw.PanedWidget):
    """Widget for editing a KeyedTree object"""
    
    def __init__(self,parent,**kw):
        optiondefs = (
            # The initial dynamics tree to show/edit
            ('tree',         None, self.setTree),
            # Width of the pane containing the tree browser
            ('treeWidth',    300,   Pmw.INITOPT),
            # Width of the pane containing editing widgets
            ('editorWidth',  150,   Pmw.INITOPT),
            # Flag indicating the level of detail used in display
            ('expert',       False, Pmw.INITOPT),
            # Font for Tree
            ('font', ('Helvetica', 10,'bold'), Pmw.INITOPT),
            )
        self.defineoptions(kw, optiondefs)
        Pmw.PanedWidget.__init__(self,parent)
        # Set overall widget size
        self.configure(hull_width=self['treeWidth']+self['editorWidth'])
        # Pane for viewing decision tree
        self.add('treePane',size=self['treeWidth'],min=self['treeWidth'])
        self.pane('treePane').configure(padx=10)
        Label(self.pane('treePane'),text='Tree:').grid(row=0,column=0,sticky='wn')
        widget = self.createcomponent('additive',(),None,Label,
                                      (self.pane('treePane'),))
        widget.grid(row=0,column=1,sticky='en')
        widget = self.createcomponent('tree',(),None,EasyTree,
                                      (self.pane('treePane'),),
                                      font=self['font'],
                                      icon=None,openicon=None,
                                      root_label="no change",
                                      root_action = self.select,
##                                      usehullsize=1,
                                      action=None)

        # Vertical scrollbar
        sb=Scrollbar(widget.master,orient='vertical')
        sb.grid(row=1,column=1,sticky='ns')
        widget.configure(yscrollcommand=sb.set)
        sb.configure(command=widget.yview)
        # Horizontal scrollbar
        sb=Scrollbar(widget.master,orient='horizontal')
        sb.grid(row=2,column=0,sticky='ew')
        widget.configure(xscrollcommand=sb.set)
        sb.configure(command=widget.xview)

        widget.grid(row=1,column=0,columnspan=2,sticky='esnw')
        widget.master.grid_rowconfigure(1, weight=1)
        widget.master.grid_columnconfigure(0, weight=1)
        # Pane for editing widgets
        self.add('editorPane',size=self['editorWidth'],
                 max=self['editorWidth'],min=self['editorWidth'])
        self.component('editorPane').configure(padx=10)
        Label(self.pane('editorPane'),text='Edit:',
              anchor='nw').pack(side='top',fill='x')
        # Action buttons
        frame = self.createcomponent('box',(),None,Pmw.ButtonBox,
                                     (self.pane('editorPane'),),
                                     orient='vertical')
        frame.add('apply',command=self.apply,
                  text='Apply',state='disabled')
        frame.add('add',command=self.addBranch,
                  text='Add branch',state='disabled')
        frame.add('delete',command=self.deleteNode,
                  text='Delete node',state='disabled')
        frame.pack(side='bottom',fill='x')
        # Store individual tree nodes
        self.nodes = {}
        self.initialiseoptions()

    def setTree(self,tree=None,node=None,prefix=''):
        """Callback for setting the tree to display and edit"""
        self.component('tree').inhibitDraw = True
        if tree is None:
            tree = self['tree']
        if tree is None:
            # Draw emptiness
            self.component('tree').easyRoot.deleteChildren()
            self.component('additive').configure(text='')
            self.component('additive').unbind('<Double-ButtonRelease-1>')
            return
        if not node:
            # Start at top of tree
            node = self.component('tree').easyRoot
            # Remove any previous tree display
            node.deleteChildren()
            self.component('tree').root.action = self.select
#                node = node.addChild(self.component('tree'),isLeaf=True)
            node['action'] = self.select
            self.setAdditive(tree)
            self.component('additive').bind('<Double-ButtonRelease-1>',
                                             self.toggle)
        if not isinstance(tree,self['tree'].__class__):
            name = self.displayLeaf(tree)
            node['label'] = prefix+name
        elif tree.isLeaf():
            # Simply display value
            name = self.displayLeaf(tree.getValue())
            node['label'] = prefix+name
        else:
            # Display branchpoint first
            name = self.displayPlane(tree.split)
            node['label'] = prefix+name
            # Display children
            if tree.isProbabilistic():
                assert len(tree.split) == 2
                elements = [tree.split._domain['then'],
                            tree.split._domain['else']]
                node['isLeaf'] = False
                subnode = node.addChild(self.component('tree'),isLeaf=True)
                subnode['action'] = self.select
                self.setTree(elements[0],subnode,'then ')
                if len(elements) == 2:
                    # Probabilistic branch
                    subnode = node.addChild(self.component('tree'),isLeaf=True)
                    subnode['action'] = self.select
                    self.setTree(elements[1],subnode,'else ')
                elif len(elements) > 2:
                    raise NotImplementedError,'Unable to distributions with more than 2 branches'
            else:
                node['isLeaf']=False
                fTree,tTree = tree.getValue()
                # Then branch
                subnode = node.addChild(self.component('tree'),isLeaf=True)
                subnode['action'] = self.select
                self.setTree(tTree,subnode,'then ')
                # Else branch
                subnode = node.addChild(self.component('tree'),isLeaf=True)
                subnode['action']=self.select
                self.setTree(fTree,subnode,'else ')
        self.component('tree').inhibitDraw = False
        self.nodes[id(node)] = tree
        self.component('tree').root.expand()
        node.refresh(self.component('tree'))

    def toggle(self,event=None):
        tree = self.selectedTree()
        tree.additive = not tree.additive
        self.setAdditive(tree)

    def setAdditive(self,tree):
        if tree.isAdditive():
            self.component('additive').configure(text='+')
        else:
            self.component('additive').configure(text='*')

    def displayLeaf(self,value):
        return str(value)

    def displayPlane(self,planes):
        return str(planes)
    
    def select(self,selection=None,event=None):
        tree = self.selectedTree()
        if not tree:
            self.component('box_apply').configure(state='disabled')
            self.component('box_add').configure(state='disabled')
            self.component('box_delete').configure(state='disabled')
        else:
            if tree.isLeaf():
                self.component('box_add').configure(state='normal')
                self.component('box_delete').configure(state='normal')
            else:
                self.component('box_add').configure(state='normal')
                self.component('box_delete').configure(state='normal')
            self.component('box_apply').configure(state='normal')
            if tree.isLeaf():
                self.selectLeaf()
            else:
                self.selectBranch()

    def setLeaf(self,leafType):
        pass
    
    def setBranch(self,rowType):
        pass
    
    def selectLeaf(self):
        pass

    def selectBranch(self):
        pass
    
    def apply(self):
        pass
        
    def selection(self,tree=None):
        """
        @return: the selected C{Node} object (C{None} if none selected)"""
        if not tree:
            tree = self.component('tree')
            return tree.selected_node()

    def selectedTree(self):
        """
        @return: selected C{KeyedTree} object (C{None} if none selected)"""
        node = self.selection()
        if node:
            try:
                return self.nodes[id(node)]
            except KeyError:
                # Hopefully, because we've selected the top (label) node
                return None
        else:
            return None

    def addBranch(self):
        pass

    def deleteNode(self):
        pass

    def findParent(self,node,tree=None):
        """Returns the parent of the given node (None if none)"""
        if not tree:
            tree = self.component('tree')
        for child in tree.child:
            if child is node:
                return tree
            else:
                value = self.findParent(node,child)
                if value:
                    return value
        else:
            return None

    def getSubtree(self):
        """
        @return: the subtree object whose root node is currently selected
        """
        tree = self.selectedTree()
        if tree:
            return tree
        else:
            return None
