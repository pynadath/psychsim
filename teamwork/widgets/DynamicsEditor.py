import copy
import string
import tkMessageBox
import Pmw
from teamwork.widgets.TreeEditor import TreeEditor
from teamwork.math.Keys import StateKey,ActionKey,RelationshipKey,ClassKey,IdentityKey,ConstantKey
from teamwork.math.KeyedVector import KeyedVector,DeltaRow,TrueRow
from teamwork.math.KeyedMatrix import KeyedMatrix
from teamwork.math.KeyedTree import KeyedPlane
from teamwork.math.probability import Distribution
from MatrixEditor import MatrixEditor

class DynamicsEditor(TreeEditor):
    def __init__(self,parent,**kw):
        optiondefs = (
            # The GenericSociety object for context
            ('society',       {},   Pmw.INITOPT),
            )
        self.defineoptions(kw, optiondefs)
        TreeEditor.__init__(self,parent)
        # Initialize state values
        stateKeys = {}
        roleKeys = {}
        classKeys = {}
        relationKeys = {}
        actionKeys = {}
        if self['society']:
            featureDict = {}
            for entity in self['society'].members():
                for feature in entity.getStateFeatures():
                    featureDict[feature] = True
                    key = StateKey({'entity':entity.name,'feature':feature})
                    stateKeys[key.simpleText()] = key
                for option in entity.actions.getOptions():
                    for action in option:
                        key = ActionKey({'type': action['type'],'object': None,
                                         'entity': entity.name})
                        actionKeys[key] = True
                        key = ActionKey({'type': action['type'],'object': None,
                                         'entity': None})
                        actionKeys[key] = True
            # Reserved role names
            roles = {'actor': True,'object': True,'self': True}
#            if isinstance(self['key'],StateKey):
#                roles[self['key']['entity']] = True
            # Fill in the possible relationship fillers
            for entity in self['society'].members():
                for relation in entity.relationships.keys():
                    for role in roles:
                        key = RelationshipKey({'feature':relation,
                                               'relatee':role})
                        relationKeys[key.simpleText()] = key
            # Add relationship references, too
            for entity in self['society'].members():
                roles.update(entity.relationships)
            # Fill in all the states on roles
            for role in roles.keys():
                for feature in featureDict.keys():
                    key = StateKey({'entity':role,'feature':feature})
                    stateKeys[key.simpleText()] = key
                key = IdentityKey({'entity':role,'relationship':'equals'})
                roleKeys[key.simpleText()] = key
            # Fill in all of the possible class fillers
            for role in roles.keys():
                for entity in self['society'].keys():
                    key = ClassKey({'entity':role,
                                    'value':entity})
                    classKeys[key.simpleText()] = key
            self.createcomponent('menus',(),None,MatrixEditor,
                                 (self.pane('editorPane'),),
                                 states=stateKeys,
                                 roles=roleKeys,
                                 classes=classKeys,
                                 relations=relationKeys,
                                 actions=actionKeys,
                                 ).pack(side='top',fill='both')
            for index in range(self.component('menus').cget('selectorCount')):
                widget = self.component('menus_feature%d_entryfield' % (index))
                widget.configure(command=self.apply)
        
    def displayLeaf(self,value):
        if isinstance(value,KeyedMatrix) or isinstance(value,KeyedVector):
            if isinstance(value,KeyedMatrix):
                vector = value.values()[0]
            else:
                vector = value
            if isinstance(vector,DeltaRow):
                name = vector.simpleText()
            else:
                name = ''
                rowKey = value.keys()[0]
                elements = []
                for colKey,weight in vector.items():
                    if colKey == rowKey:
                        weight -= 1.
                    if abs(weight) > 0.:
                        if isinstance(colKey,ConstantKey):
                            elements.append('%5.3f' % (weight))
                        else:
                            elements.append('%d%% of %s' % (weight*100.,
                                                            colKey.simpleText()))
                name = 'increment by %s' % (string.join(elements,' and '))
        elif isinstance(value,str):
            name = value
        elif value is None or isinstance(value,bool):
            name = str(value)
        else:
            tkMessageBox.showwarning('Warning','Unable to display leaf nodes of type %s' % (value.__class__.__name__))
            name = ''
        return name

    def displayPlane(self,planes):
        if isinstance(planes,list):
            # PWL branches
            planeStr = string.join(map(lambda p:p.simpleText(numbers=self['expert']),planes),' and ')
            return 'if %s' % (planeStr)
        elif len(planes) == 1:
            # Distribution, but no real branch
            return 'with 100% probability'
        elif len(planes) == 2:
            # Probabilistic branch
            return 'with %d%% probability' % (planes['then']*100.)
        else:
            # Too much to handle
            raise UserWarning,'Unable to display distributions with more than 2 branches'

    def apply(self):
        """Callback for applying changes to underlying L{KeyedTree<teamwork.math.KeyedTree.KeyedTree>} object"""
        tree = self.selectedTree()
        if tree is None:
            pass
        elif tree.isLeaf():
            row = self.component('menus').getDynamics()
            tree.makeLeaf(row)
            name = self.displayLeaf(tree.getValue())
        else:
            branch = self.component('menus').getBranch()
            children = tree.children()
            if isinstance(branch,KeyedPlane):
                # PWL branch
                tree.split = [branch]
            else:
                # Probabilistic branch
                prob = branch['then']
                branch = Distribution({'then': prob, 'else': 1.-prob})
                branch._domain['then'] = children[0]
                branch._domain['else'] = children[1]
                tree.branch(branch)
            name = self.displayPlane(tree.split)
        if tree.parent:
            if tree.parent[0].isProbabilistic():
                name = '%s %s' % (tree.parent[1],name)
            elif tree.parent[1]:
                name = 'then %s' % (name)
            else:
                name = 'else %s' % (name)
        selectednode = self.selection()
        #keep track of expansion
        rnode = self.component('tree').find_full_id(selectednode.full_id())
        expand = (rnode and rnode.expandable() and rnode.expanded())
        selectednode['label'] = name
        selectednode.refresh()
        if expand:
            self.component('tree').find_full_id(selectednode.full_id()).expand()
        self.nodes[id(self.selection())] = tree
        
    def setLeaf(self,rowType):
        self.component('menus').setDynamics(rowType)

    def setBranch(self,rowType):
        self.component('menus').setBranch(rowType)

    def selectLeaf(self):
        if not self['society']:
            self.component('box_apply').configure(state='disabled')
            self.component('box_add').configure(state='disabled')
            self.component('box_delete').configure(state='disabled')
            return
##        self.component('menus_type').configure(menubutton_state='normal')
        self.component('menus_type').configure(selectioncommand=self.setLeaf)
        self.component('menus').displayDynamics(self.selectedTree().getValue())
        
    def selectBranch(self):
        if not self['society']:
            self.component('box_apply').configure(state='disabled')
            self.component('box_add').configure(state='disabled')
            self.component('box_delete').configure(state='disabled')
            return
##        self.component('menus_type').configure(menubutton_state='normal')
        self.component('menus_type').configure(selectioncommand=self.setBranch)
        tree = self.selectedTree()
        if isinstance(tree.split,list):
            if len(tree.split) > 1:
                raise NotImplementedError,'Currently unable to display multiple hyperplanes'
            else:
                self.component('menus').displayBranch(tree.split[0])
        else:
            # Probabilistic branch
            self.component('menus').displayBranch(tree.split)

    def addBranch(self):
        tree = self.selectedTree()
        parent = self.selection()
        if tree.isLeaf():
            # Adding branch to leaf node
            trueTree = tree.__class__()
            trueTree.makeLeaf(copy.deepcopy(tree.getValue()))
            falseTree = tree.__class__()
            falseTree.makeLeaf(copy.deepcopy(tree.getValue()))
        else:
            # Adding branch above branch; must handle children first
            for child in parent['children'][:]:
                child.delete() 
                del self.nodes[id(child)]
#            parent.refresh()
            trueTree = copy.deepcopy(tree)
            falseTree = copy.deepcopy(tree)
        row = TrueRow()
        plane = KeyedPlane(row,-.1)
        # The None flags are important to prevent pruning (because
        # left and right are ==, so they'll get collapsed otherwise)
        tree.branch(plane,trueTree=trueTree,falseTree=falseTree,
                    pruneF=False,pruneT=False)
        # Draw the new branch
        self.component('tree').inhibitDraw = True
        name = self.displayPlane(tree.split)
        if tree.parent:
            if tree.parent[1]:
                name = 'then %s' % (name)
            else:
                name = 'else %s' % (name)
#        parent.var.set(name)
        parent['label'] = name
        parent['isLeaf'] = False
        subnode = parent.addChild(self.component('tree'),isLeaf=True)
        subnode['action'] = self.select
        self.setTree(trueTree,subnode,'then ')
        subnode = parent.addChild(self.component('tree'),isLeaf=True)
        subnode['action'] = self.select
        self.setTree(falseTree,subnode,'else ')
        self.nodes[id(parent)] = tree
        self.component('tree').inhibitDraw = False
#        self.component('tree').display()
        parent.refresh(self.component('tree'))
        self.select()
        self.component('tree').find_full_id(parent.full_id()).expand()

    def __deleteRecursiveFromDict__(self,node,somedict):
        for child in node['children'][:]:
            self.__deleteRecursiveFromDict__(child,somedict)
        somedict[id(node)] = None

    def deleteNode(self):
        childTree = self.selectedTree()
        if childTree.parent:
            parentTree,side = childTree.parent
        else:
            tkMessageBox.showerror('Delete Error',
                                   'You cannot delete the entire tree!')
            return
        childNode = self.selection()
#        parentNode = childNode.master
        parentNode = childNode['parent']
        if isinstance(parentTree.split,list):
            # Binary tree
            #do some housecleaning of our convenience hash
#            self.__deleteRecursiveFromDict__(parentNode,self.nodes)
            del self.nodes[id(parentNode)]
            del self.nodes[id(childNode)]

            fTree,tTree = parentTree.getValue()
            if parentTree.parent is None:
                prefix = ''
            elif parentTree.parent[1]:
                prefix = 'then '
            else:
                prefix = 'else '
            if side:
                # We're deleting T side
                if fTree.isLeaf():
                    parentTree.makeLeaf(fTree.getValue())
                elif fTree.isProbabilistic():
                    tkMessageBox.showerror('Not implemented','Unable to delete children from probabilistic branches.')
                else:
                    plane = fTree.split
                    fTree,tTree = fTree.getValue()
                    parentTree.branch(plane,fTree,tTree)
#                name = parentNode.child[1].var.get()
                name = parentNode['children'][1]['label']
                parentNode['label'] = prefix+name[5:]
                parentNode['children'][0].delete()
                parentNode['isLeaf'] = True
#                parentNode.var.set(prefix+name[5:])
#                parentNode.deleteChild(parentNode.child[0])
            else:
                # We're deleting F side
                if tTree.isLeaf():
                    parentTree.makeLeaf(tTree.getValue())
                elif tTree.isProbabilistic():
                    tkMessageBox.showerror('Not implemented','Unable to delete children from probabilistic branches.')
                else:
                    plane = tTree.split
                    fTree,tTree = tTree.getValue()
                    parentTree.branch(plane,fTree,tTree)
#                name = parentNode.child[0].var.get()
                name = parentNode['children'][0]['label']
                parentNode['label'] = prefix+name[5:]
                parentNode['children'][1].delete()
                parentNode['isLeaf'] = True

#                parentNode.var.set(prefix+name[5:])
#                parentNode.deleteChild(parentNode.child[1])
#            children = parentNode.child[0].child
            children = parentNode['children'][0]['children'][:]
#            parentNode.state = parentNode.child[0].state
            parentNode['children'][0].delete(recursive=False)
#            parentNode.deleteChild(parentNode.child[0])
            for child in children:
#                parentNode.child.append(child)
                parentNode['children'].append(child)
                child['parent'] = parentNode
                parentNode['isLeaf'] = False
#                child.master = parentNode
            self.nodes[id(parentNode)] = parentTree
            parentNode.selected = True
            parentNode.refresh()
        else:
            tkMessageBox.showerror('Not implemented','Unable to delete children from probabilistic branches.')
            return
#        self.component('tree').display()
        if self.selectedTree().isLeaf():
            self.selectLeaf()
        else:
            self.selectBranch()
            
    def paste(self,content):
        # Check whether this tree is compatible
        tree = content
        while not tree.isLeaf():
            tree = tree.children()[0]
        newKey = tree.getValue().keys()[0]
        oldKey = self.component('menus').cget('key')
        if newKey != oldKey:
            msg = 'Unable to paste an effect on %s into an effect on %s.'\
                % (newKey,oldKey)
            tkMessageBox.showerror('Unable to Paste',msg)
            return
        # Get selection
        node = self.selection()
        tree = self.selectedTree()
        if tree.parent is None:
            parentTree,side = None,None
        else:
            parentTree,side = tree.parent
        # Update the tree
        if content.isProbabilistic():
            tkMessageBox.showerror('Not implemented','Unable to paste probabilistic subtrees')
            return
        elif parentTree:
            # Create new child
            fTree,tTree = parentTree.getValue()
            if parentTree.isProbabilistic():
                tkMessageBox.showerror('Not implemented','Unable to paste into probabilistic branches')
                return
            else:
                plane = parentTree.split
                if side:
                    # New T side
                    parentTree.branch(plane,fTree,content)
                else:
                    # New F side
                    parentTree.branch(plane,content,tTree)
        elif content.isLeaf():
            tree.makeLeaf(content.getValue())
        else:
            fTree,tTree = content.getValue()
            tree.branch(content.split,fTree,tTree)
        # Update display
        node.deleteChildren()
        if parentTree is None:
            self.setTree(content,node)
        elif side:
            self.setTree(content,node,'then ')
        else:
            self.setTree(content,node,'else ')
