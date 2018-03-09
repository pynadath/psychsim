from xml.dom.minidom import Document,Node

from psychsim.probability import Distribution
from psychsim.action import Action

from vector import KeyedVector
from matrix import *
from plane import KeyedPlane

class KeyedTree:
    """
    Decision tree node using symbolic PWL structures
    @ivar leaf: C{True} iff this node is a leaf
    @type leaf: bool
    @ivar children: table of children of this node
    @type children: dict
    @ivar branch: the hyperplane branch at this node (if applicable)
    @type branch: L{KeyedPlane}
    """
    def __init__(self,leaf=None):
        self._string = None
        self._keysIn = None
        self._keysOut = None
        if isinstance(leaf,Node):
            self.parse(leaf)
        else:
            self.makeLeaf(leaf)
            
    def isLeaf(self):
        return self.leaf

    def makeLeaf(self,leaf):
        self.children = {None: leaf}
        self.leaf = True
        self.branch = None

    def makeBranch(self,plane,trueTree,falseTree):
        self.children = {True: trueTree,False: falseTree}
        self.branch = plane
        self.leaf = False

    def makeProbabilistic(self,distribution):
        assert isinstance(distribution,Distribution)
        self.children = distribution
        self.branch = None
        self.leaf = False

    def isProbabilistic(self):
        """
        @return: C{True} if there is a probabilistic branch at this node
        @rtype: bool
        """
        return self.branch is None and not self.isLeaf()

    def getKeysIn(self):
        """
        @return: a set of all keys that affect the output of this PWL function
        """
        if self._keysIn is None:
            self._keysIn = set()
            self._keysOut = set()
            if self.isProbabilistic():
                # Keys are taken from each child
                children = self.children.domain()
            else:
                children = self.children.values()
                if not self.isLeaf():
                    # Keys also include those in the branch
                    self._keysIn |= set(self.branch.vector.keys())
            # Accumulate keys across children
            for child in children:
                if isinstance(child,KeyedVector):
                    self._keysIn |= set(child.keys())
                elif not child is None and not isinstance(child,bool):
                    self._keysIn |= child.getKeysIn()
                    self._keysOut |= child.getKeysOut()
        return self._keysIn

    def getKeysOut(self):
        """
        @return: a set of all keys that are affected by this PWL function
        """
        if self._keysOut is None:
            self.getKeysIn()
        return self._keysOut

    # def getKeys(self):
    #     """
    #     @return: a set of all keys references in this PWL function
    #     """
    #     if self.isProbabilistic():
    #         # Keys are taken from each child
    #         result = set()
    #         children = self.children.domain()
    #     else:
    #         children = self.children.values()
    #         if self.isLeaf():
    #             result = set()
    #         else:
    #             # Keys also include those in the branch
    #             result = set(self.branch.vector.keys())
    #     # Accumulate keys across children
    #     for child in children:
    #         if isinstance(child,KeyedVector):
    #             result |= set(child.keys())
    #         elif not child is None and not isinstance(child,bool):
    #             result |= child.getKeys()
    #     return result

    def collapseProbabilistic(self):
        """
        Utility method that combines any consecutive probabilistic branches at this node into a single distribution
        """
        if self.isProbabilistic():
            collapse = False
            distribution = Distribution(self.children)
            for child in self.children.domain():
                if child.isProbabilistic():
                    # Probabilistic branch to merge
                    collapse = True
                    child.collapseProbabilistic()
                    del distribution[child]
                    for grandchild in child.children.domain():
                        try:
                            distribution[grandchild] += self.children[child]*child.children[grandchild]
                        except KeyError:
                            distribution[grandchild] = self.children[child]*child.children[grandchild]
            if collapse:
                assert sum(distribution.values()) == 1.
                self.makeProbabilistic(distribution)
            
    def __getitem__(self,index):
        if self.isLeaf():
            return self.children[None]
        elif self.branch is None:
            # Probabilistic branch
            result = {}
            for element in self.children.domain():
                prob = self.children[element]
                subtree = element[index]
                if isinstance(subtree,Distribution):
                    for subelement in subtree.domain():
                        try:
                            result[subelement] += prob*subtree[subelement]
                        except KeyError:
                            result[subelement] = prob*subtree[subelement]
                else:
                    try:
                        result[subtree] += prob
                    except KeyError:
                        result[subtree] = prob
            return Distribution(result)
        else:
            # Deterministic branch
            return self.children[self.branch.evaluate(index)][index]

    def desymbolize(self,table,debug=False):
        """
        @return: a new tree with any symbolic references replaced with numeric values according to the table of element lists
        @rtype: L{KeyedTree}
        """
        tree = self.__class__()
        if self.isLeaf():
            leaf = self.children[None]
            if isinstance(leaf,KeyedVector) or isinstance(leaf,KeyedMatrix):
                tree.makeLeaf(leaf.desymbolize(table,debug))
            else:
                tree.makeLeaf(leaf)
        elif self.branch:
            tree.makeBranch(self.branch.desymbolize(table),self.children[True].desymbolize(table),
                            self.children[False].desymbolize(table))
        else:
            new = TreeDistribution()
            for child in self.children.domain():
                new.addProb(child.desymbolize(table),self.children[child])
            tree.makeProbabilistic(new)
        return tree

    def floor(self,key,lo):
        """
        Modify this tree to make sure the new computed value never goes lower than the given floor
        @warning: may introduce redundant checks
        """
        if self.isLeaf():
            tMatrix = self.children[None]
            assert len(tMatrix) == 1,'Unable to handle dynamics of more than one feature'
            assert tMatrix.has_key(key),'Are you sure you should be flooring me on a key I don\'t have?'
            del self.children[None]
            fMatrix = setToConstantMatrix(key,lo)
            branch = KeyedPlane(KeyedVector(tMatrix[key]),lo)
            self.makeBranch(branch,KeyedTree(tMatrix),KeyedTree(fMatrix))
        elif self.branch:
            self.children[True].floor(key,lo)
            self.children[False].floor(key,lo)
        else:
            for child in self.children.domain():
                prob = self.children[child]
                del self.children[child]
                self[child.floor(key,lo)] = prob
        return self

    def ceil(self,key,hi):
        """
        Modify this tree to make sure the new computed value never goes higher than the given ceiling
        @warning: may introduce redundant checks
        """
        if self.isLeaf():
            fMatrix = self.children[None]
            assert len(fMatrix) == 1,'Unable to handle dynamics of more than one feature'
            assert fMatrix.has_key(key),'Are you sure you should be ceiling me on a key I don\'t have?'
            del self.children[None]
            tMatrix = setToConstantMatrix(key,hi)
            branch = KeyedPlane(KeyedVector(fMatrix[key]),hi)
            self.makeBranch(branch,KeyedTree(tMatrix),KeyedTree(fMatrix))
        elif self.branch:
            self.children[True].ceil(key,hi)
            self.children[False].ceil(key,hi)
        else:
            for child in self.children.domain():
                prob = self.children[child]
                del self.children[child]
                self[child.ceil(key,hi)] = prob
        return self

    def scale(self,table):
        tree = self.__class__()
        if self.isLeaf():
            tree.makeLeaf(self.children[None].scale(table))
        elif self.branch:
            tree.makeBranch(self.branch.scale(table),self.children[True].scale(table),
                            self.children[False].scale(table))
        else:
            new = {}
            for child in self.children.domain():
                new[child.scale(table)] = self.children[child]
            tree.makeProbabilistic(TreeDistribution(new))
        return tree

    def __eq__(self,other):
        if self.isLeaf():
            if other.isLeaf():
                return self.children[None] == other.children[None]
            else:
                return False
        elif isinstance(self.children,Distribution):
            if isinstance(other.children,Distribution):
                return self.children == other.children
            else:
                return false
        else:
            if self.branch == other.branch:
                return self.children == other.children
            else:
                return False
            
    def __add__(self,other):
        if isinstance(other,KeyedTree):
            return self.compose(other,lambda x,y: x+y)
        else:
            return self+KeyedTree(other)
            
    def __mul__(self,other):
        if isinstance(other,KeyedTree):
            return self.compose(other,lambda x,y: x*y,lambda x,y: x*y)
        else:
            return self*KeyedTree(other)

    def max(self,other):
        return self.compose(other,self.__max)

    def __max(self,leaf1,leaf2):
        """
        Helper method for computing max
        @return: a tree returing the maximum of the two vectors
        @rtype: L{KeyedTree}
        """
        result = self.__class__()
        if leaf1 is False:
            result.graft(leaf2)
        elif leaf2 is False:
            result.graft(leaf1)
        else:
            if isinstance(leaf1,dict):
                weights = leaf1['vector'] - leaf2['vector']
            else:
                # Assume vectors
                weights = leaf1 - leaf2
            result.makeBranch(KeyedPlane(weights,0.),KeyedTree(leaf1),KeyedTree(leaf2))
        return result

    def compose(self,other,leafOp=None,planeOp=None):
        """
        Compose two trees into a single tree
        @param other: the other tree to be composed with
        @type other: L{KeyedTree}
        @param leafOp: the binary operator to apply to leaves of each tree to generate a new leaf
        @param planeOp: the binary operator to apply to the plane
        @rtype: L{KeyedTree}
        """
        result = KeyedTree()
        if other.isLeaf():
            if self.isLeaf():
                result.graft(leafOp(self.children[None],other.children[None]))
            elif self.branch is None:
                # Probabilistic branch
                distribution = self.children.__class__()
                for old in self.children.domain():
                    new = old.compose(other,leafOp,planeOp)
                    if isinstance(new,Distribution):
                        for tree in new.domain():
                            distribution.addProb(tree,self.children[old]*new[tree])
                    else:
                        distribution.addProb(new,self.children[old])
                if len(distribution) > 1:
                    result.makeProbabilistic(distribution)
                    result.collapseProbabilistic()
                else:
                    result.graft(new)
            else:
                # Deterministic branch
                trueTree = self.children[True].compose(other,leafOp,planeOp)
                falseTree = self.children[False].compose(other,leafOp,planeOp)
                if trueTree == falseTree:
                    result.graft(trueTree)
                else:
                    if planeOp is None or not isinstance(other.children[None],KeyedMatrix):
                        plane = self.branch
                    else:
                        plane = KeyedPlane(planeOp(self.branch.vector,other.children[None]),
                                           self.branch.threshold,self.branch.comparison)
                    result.makeBranch(plane,trueTree,falseTree)
        elif other.branch is None:
            # Probabilistic branch
            distribution = other.children.__class__()
            for old in other.children.domain():
                new = self.compose(old,leafOp,planeOp)
                if isinstance(new,Distribution):
                    for tree in new.domain():
                        distribution.addProb(tree,other.children[old]*new[tree])
                else:
                    distribution.addProb(new,other.children[old])
            if len(distribution) > 1:
                result.makeProbabilistic(distribution)
                result.collapseProbabilistic()
            else:
                result.graft(new)
        else:
            # Deterministic branch
            trueTree = self.compose(other.children[True],leafOp,planeOp)
            falseTree = self.compose(other.children[False],leafOp,planeOp)
            if trueTree == falseTree:
                result.graft(trueTree)
            else:
                result.makeBranch(other.branch,trueTree,falseTree)
        return result
            
    def replace(self,old,new):
        """
        @return: a new tree with the given substitution applied to all leaf nodes
        """
        return self.map(lambda leaf: new if leaf == old else leaf)

    def expectation(self):
        """
        @return: a new tree representing an expectation over any probabilistic branches
        """
        return self.map(distOp=lambda branch: branch.expectation())

    def map(self,leafOp=None,planeOp=None,distOp= None):
        """
        Generates a new tree applying a function to all planes and leaves
        @param leafOp: functional transformation of leaf nodes
        @type leafOp: lambda XS{->}X
        @param planeOp: functional transformation of hyperplanes
        @type planeOp: lambda XS{->}X
        @param distOp: functional transformation of probabilistic branches
        @type distOp: lambda L{TreeDistribution}S{->}X
        @rtype: L{KeyedTree}
        """
        result = self.__class__()
        if self.isLeaf():
            if leafOp:
                leaf = leafOp(self.children[None])
            else:
                leaf = self.children[None]
            result.graft(leaf)
        elif self.isProbabilistic():
            if distOp:
                result.graft(distOp(self.children))
            else:
                distribution = self.children.__class__()
                for old in self.children.domain():
                    new = old.map(leafOp,planeOp,distOp)
                    try:
                        distribution[new] += self.children[old]
                    except KeyError:
                        distribution[new] = self.children[old]
                result.makeProbabilistic(distribution)
        else:
            # Deterministic branch
            if planeOp:
                branch = planeOp(self.branch)
            else:
                branch = self.branch
            result.makeBranch(branch,self.children[True].map(leafOp,planeOp,distOp),
                              self.children[False].map(leafOp,planeOp,distOp))
        return result

    def graft(self,root):
        """
        Grafts a tree at the current node
        @warning: clobbers anything currently at (or rooted at) this node
        """
        if isinstance(root,TreeDistribution):
            self.makeProbabilistic(root)
        elif isinstance(root,KeyedTree):
            if root.isLeaf():
                self.makeLeaf(root.children[None])
            elif root.isProbabilistic():
                self.makeProbabilistic(root.children)
            else:
                self.makeBranch(root.branch,root.children[True],root.children[False])
        else:
            # Leaf node (not a very smart use of graft, but who are we to judge)
            self.makeLeaf(root)

    def prune(self,path=[]):
        """
        Removes redundant branches
        @warning: correct, but not necessarily complete
        """
        result = self.__class__()
        if self.isLeaf():
            # Leaves are unchanged
            result.makeLeaf(self.children[None])
        elif self.isProbabilistic():
            # Distributions are passed through
            distribution = self.children.__class__() 
            for tree in self.children.domain():
                prob = self.children[tree]
                tree.prune(path)
                try:
                    distribution[tree] += prob
                except KeyError:
                    distribution[tree] = prob
            if len(distribution) == 1:
                result.graft(tree)
            else:
                result.makeProbabilistic(distribution)
        else:
            # Deterministic branch
            for branch,value in path:
                conflict = self.branch.compare(branch,value)
                if not conflict is None:
                    result.graft(self.children[conflict].prune(path))
                    break
            else:
                # No matches
                result.makeBranch(self.branch,self.children[True].prune(path+[(self.branch,True)]),
                                  self.children[False].prune(path+[(self.branch,False)]))
        return result

    def minimizePlanes(self):
        """
        Modifies tree in place so that there are no constant factors in branch weights
        """
        if self.isProbabilistic():
            for child in self.children.domain():
                child.minimizePlanes()
        elif not self.isLeaf():
            self.branch = self.branch.minimize()
            self.children[True].minimizePlanes()
            self.children[False].minimizePlanes()
            
    def __hash__(self):
        return hash(str(self))

    def __str__(self):
        if self._string is None:
            if self.isLeaf():
                self._string = str(self.children[None])
            elif self.children.has_key(True):
                # Deterministic branch
                self._string = 'if %s\nThen\t%s\nElse\t%s' % (str(self.branch),str(self.children[True]).replace('\n','\n\t'),
                                                      str(self.children[False]).replace('\n','\n\t'))
            else:
                # Probabilistic branch
                self._string = '\n'.join(map(lambda el: '%d%%: %s' % (100.*self.children[el],str(el)),self.children.domain()))
        return self._string

    def __xml__(self):
        doc = Document()
        root = doc.createElement('tree')
        if not self.isLeaf():
            if self.branch:
                root.appendChild(self.branch.__xml__().documentElement)
        if isinstance(self.children,Distribution):
            root.appendChild(self.children.__xml__().documentElement)
        else:
            for key,value in self.children.items():
                if isinstance(value,bool):
                    node = doc.createElement('bool')
                    node.setAttribute('value',str(value))
                elif isinstance(value,str):
                    node = doc.createElement('str')
                    node.appendChild(doc.createTextNode(value))
                elif value is None:
                    node = doc.createElement('none')
                else:
                    node = value.__xml__().documentElement
                node.setAttribute('key',str(key))
                root.appendChild(node)
        doc.appendChild(root)
        return doc

    def parse(self,element):
        assert element.tagName == 'tree'
        node = element.firstChild
        plane = None
        children = {}
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                if node.tagName == 'vector':
                    if node.getAttribute('key'):
                        # Vector leaf
                        key = eval(node.getAttribute('key'))
                        children[key] = KeyedVector(node)
                    else:
                        # Branch
                        plane = KeyedPlane(node)
                elif node.tagName == 'matrix':
                    key = eval(node.getAttribute('key'))
                    children[key] = KeyedMatrix(node)
                elif node.tagName == 'tree':
                    key = eval(node.getAttribute('key'))
                    children[key] = KeyedTree(node)
                elif node.tagName == 'distribution':
                    children = TreeDistribution(node)
                elif node.tagName == 'bool':
                    key = eval(node.getAttribute('key'))
                    children[key] = eval(node.getAttribute('value'))
                elif node.tagName == 'action': 
                    key = eval(node.getAttribute('key'))
                    children[key] = Action(node)
                elif node.tagName == 'str':
                    key = eval(node.getAttribute('key'))
                    children[key] = str(node.firstChild.data).strip()
                elif node.tagName == 'none':
                    key = eval(node.getAttribute('key'))
                    children[key] = None
            node = node.nextSibling
        if plane:
            self.makeBranch(plane,children[True],children[False])
        elif isinstance(children,Distribution):
            self.makeProbabilistic(children)
        else:
            self.makeLeaf(children[None])

class TreeDistribution(Distribution):
    """
    A class representing a L{Distribution} over L{KeyedTree} instances
    """
    def element2xml(self,value):
        return value.__xml__().documentElement

    def xml2element(self,key,node):
        return KeyedTree(node)

def makeTree(table):
    if isinstance(table,bool):
        # Boolean leaf
        return KeyedTree(table)
    elif table is None:
        # Null leaf
        return KeyedTree(table)
    elif isinstance(table,str):
        # String leaf
        return KeyedTree(table)
    elif isinstance(table,frozenset):
        # Set leaf (e.g., ActionSet for a policy)
        return KeyedTree(table)
    elif table.has_key('if'):
        # Deterministic branch
        tree = KeyedTree()
        tree.makeBranch(table['if'],makeTree(table[True]),makeTree(table[False]))
        return tree
    elif table.has_key('distribution'):
        # Probabilistic branch
        tree = KeyedTree()
        branch = {}
        for subtable,prob in table['distribution']:
            subtree = makeTree(subtable)
            branch[subtree] = prob + branch.get(subtree,0.)
        tree.makeProbabilistic(TreeDistribution(branch))
        return tree
    else:
        # Leaf
        return KeyedTree(table)
