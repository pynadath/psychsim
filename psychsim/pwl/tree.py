from xml.dom.minidom import Document,Node

from psychsim.probability import Distribution
from psychsim.action import Action

from psychsim.pwl.keys import CONSTANT,makeFuture,makePresent,isFuture
from psychsim.pwl.vector import KeyedVector
from psychsim.pwl.matrix import KeyedMatrix,setToConstantMatrix
from psychsim.pwl.plane import KeyedPlane,equalRow

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
#        assert self.leaf == (len(self.children) == 1 and not isinstance(self.children,Distribution))
        return self.leaf

    def getLeaf(self):
        return self.children[None]

    def makeLeaf(self,leaf):
        self.children = {None: leaf}
        self.leaf = True
        self.branch = None

    def makeBranch(self,plane,children):
        self.children = children
        self.branch = plane
        self.leaf = False

    def makeProbabilistic(self,distribution):
        assert isinstance(distribution,Distribution)
        assert len(distribution) > 1
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
                    self._keysIn |= set(self.branch.keys())
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

    def keys(self):
        return self.getKeysIn() | self.getKeysOut()
        
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
            subindex = self.branch.evaluate(index)
            return self.children[subindex][index]

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
            tree.makeBranch(self.branch.desymbolize(table),
                            {value: self.children[value].desymbolize(table) \
                             for value in self.children})
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
            tMatrix = self.getLeaf()
            assert len(tMatrix) == 1,'Unable to handle dynamics of more than one feature'
            assert makeFuture(key) in tMatrix,'Are you sure you should be flooring me on a key I don\'t have?'
            del self.children[None]
            fMatrix = setToConstantMatrix(key,lo)
            branch = KeyedPlane(KeyedVector(tMatrix[makeFuture(key)]),lo)
            self.makeBranch(branch,{True: KeyedTree(tMatrix),
                                    False: KeyedTree(fMatrix)})
        elif self.branch:
            for child in self.children.values():
                child.floor(key,lo)
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
            assert makeFuture(key) in fMatrix,'Are you sure you should be ceiling me on a key I don\'t have?'
            del self.children[None]
            tMatrix = setToConstantMatrix(key,hi)
            branch = KeyedPlane(KeyedVector(fMatrix[makeFuture(key)]),hi)
            self.makeBranch(branch,{True: KeyedTree(tMatrix),
                                    False: KeyedTree(fMatrix)})
        elif self.branch:
            for child in self.children.values():
                child.ceil(key,hi)
        else:
            for child in self.children.domain():
                prob = self.children[child]
                del self.children[child]
                self[child.ceil(key,hi)] = prob
        return self

    def makeFuture(self,keyList=None):
        self.changeTense(True,keyList)

    def makePresent(self,keyList=None):
        self.changeTense(False,keyList)
        
    def changeTense(self,future=True,keyList=None):
        """
        Transforms this vector to refer to only future versions of its columns
        @param keyList: If present, only references to these keys are made future
        """
        if keyList is None:
            keyList = self.keys()
        if self.isProbabilistic():
            for child in self.children.domain():
                prob = self.children[child]
                del self.children[child]
                child.changeTense(future,keyList)
                self.children[child] = prob
        else:
            if not self.isLeaf():
                self.branch.changeTense(future,keyList)
            for value,child in self.children.items():
                child.changeTense(future,keyList)
        self._string = None
        self._keysIn = None
            
    def scale(self,table):
        tree = self.__class__()
        if self.isLeaf():
            tree.makeLeaf(self.children[None].scale(table))
        elif self.branch:
            tree.makeBranch(self.branch.scale(table),
                            {value: self.children[value].scale(table) for value in self.children})
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
        elif self.isProbabilistic():
            if other.isProbabilistic():
                return self.children == other.children
            else:
                return False
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
        elif isinstance(other,KeyedVector):
            return self[other]*other
        elif isinstance(other,float) or isinstance(other,int):
            return other*self
        else:
            return NotImplemented
        
    def __rmul__(self,other):
        if isinstance(other,float) or isinstance(other,int):
            tree = self.__class__()
            if self.isLeaf():
                tree.makeLeaf(other*self.children[None])
            elif self.isProbabilistic():
                dist = {}
                for child in self.children.domain():
                    prod = other*child
                    dist[prod] = dist.get(prod,0.)+self.children[child]
                tree.makeProbabilistic(TreeDistribution(dist))
            else:
                tree.makeBranch(self.branch,
                                {value: other*self.children[value] for value in self.children})
            return tree
        else:
            return NotImplemented

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
            if isinstance(leaf1,tuple):
                # (ER weights,action)
                weights = leaf1[0] - leaf2[0]
            else:
                # Assume vectors
                weights = leaf1 - leaf2
            weights.prune()
            if CONSTANT in weights:
                threshold = -weights[CONSTANT]
                del weights[CONSTANT]
            else:
                threshold = 0.
            if len(weights) == 0:
                if 0. > threshold:
                    # Must be true
                    result.graft(KeyedTree(leaf1))
                else:
                    # Must be false
                    result.graft(KeyedTree(leaf2))
            else:
                alpha = weights.normalize()
                result.makeBranch(KeyedPlane(weights,threshold*alpha),{True: KeyedTree(leaf1),False: KeyedTree(leaf2)})
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
            elif self.isProbabilistic():
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
                trees = {value: self.children[value].compose(other,leafOp,planeOp) \
                         for value in self.children}
                protoTree = None
                for tree in trees.values():
                    if protoTree is None:
                        protoTree = tree
                    elif tree != protoTree:
                        if planeOp is None or not isinstance(other.children[None],KeyedMatrix):
                            plane = self.branch
                        else:
                            plane = KeyedPlane([(planeOp(p,other.children[None]),t,c)
                                                for p,t,c in self.branch.planes])
                            plane.minimize()
                        result.makeBranch(plane,trees)
                        break
                else:
                    result.graft(protoTree)
        elif other.isProbabilistic():
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
            trees = {value: self.compose(other.children[value],leafOp,planeOp) \
                     for value in other.children}
            protoTree = None
            for tree in trees.values():
                if protoTree is None:
                    protoTree = tree
                elif tree != protoTree:
                    result.makeBranch(other.branch,trees)
                    break
            else:
                result.graft(protoTree)
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
                if len(distribution) > 1:
                    result.makeProbabilistic(distribution)
                else:
                    result.graft(distribution.first())
        else:
            # Deterministic branch
            if planeOp:
                branch = planeOp(self.branch)
            else:
                branch = self.branch
            first = None
            children = {value: self.children[value].map(leafOp,planeOp,distOp) for value in self.children}
            for child in children.values():
                if first is None:
                    first = child
                elif first != child:
                    # Not all children are identical
                    result.makeBranch(branch,children)
                    break
            else:
                # All children are the same, so branch is unnecessary
                result.graft(first)
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
                self.makeBranch(root.branch,{value: root.children[value] for value in root.children})
        else:
            # Leaf node (not a very smart use of graft, but who are we to judge)
            self.makeLeaf(root)

    def sampleLeaf(self,vector,mostlikely=False):
        """
        :param mostlikely: if True, then only the most likely branches are chosen at each probabilistic branch
        :type mostlikely: bool
        :return: a leaf node sampled from the distribution over leaf nodes for the given vector
        """
        if self.isLeaf():
            return self.children[None]
        elif self.branch is None:
            # Probabilistic branch
            if mostlikely:
                return self.children.max().sampleLeaf(vector,mostlikely)
            else:
                return self.children.sample().sampleLeaf(vector,mostlikely)
        else:
            # Deterministic branch
            return self.children[self.branch.evaluate(vector)].sampleLeaf(vector,mostlikely)


    def sample(self,mostlikely=False,vector=None):
        """
        :param mostlikely: if True, then only the most likely branches are chosen at each probabilistic branch
        :type mostlikely: bool
        :param vector: if provided, return the leaf node corresponding to the given possible world
        :type vector: KeyedVector
        :return: a tree sampled from all of the probabilistic branches
        """
        if vector is not None:
            return self.sampleLeaf(vector,mostlikely)
        result = self.__class__()
        if self.isLeaf():
            result.makeLeaf(self.getLeaf())
        elif self.isProbabilistic():
            if mostlikely:
                child = self.children.max()
            else:
                child = self.children.sample()
            result.graft(child.sample(mostlikely))
        else:
            result.makeBranch(self.branch,{value: self.children[value].sample(mostlikely) for value in self.children})
        return result
        
    def prune(self,path=[],variables={}):
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
                child = tree.prune(path,variables)
                if child.isProbabilistic():
                    for grandchild in child.children.domain():
                        subprob = child.children[grandchild]
                        try:
                            distribution[grandchild] += prob*subprob
                        except KeyError:
                            distribution[grandchild] = prob*subprob
                else:
                    try:
                        distribution[child] += prob
                    except KeyError:
                        distribution[child] = prob
            if len(distribution) == 1:
                result.graft(child)
            else:
                result.makeProbabilistic(distribution)
        else:
            # Deterministic branch
            if variables:
                poss = self.branch.possible(variables)
                if poss is not None:
                    if len(poss) == 1:
                        result.graft(self.children[poss[0]].prune(path,variables))
                        return result
                    elif len(poss) < len(self.children):
                        print(poss)
                        exit()
                vector = self.branch.planes[0][0].keys()
            for branch,value in path:
                conflict = self.branch.compare(branch,value)
                if conflict is not None:
                    result.graft(self.children[conflict].prune(path,variables))
                    break
            else:
                # No matches
                for weights,threshold,comparison in self.branch.planes:
                    if len(weights) == 1 and CONSTANT in weights:
                        value = self.branch.evaluate(weights[CONSTANT])
                        result.graft(self.children[value].prune(path,variables))
                        break
                else:
                    result.makeBranch(self.branch,
                                      {value: self.children[value].prune(path+[(self.branch,value)],variables) 
                                       for value in self.children})
        return result
                
    def minimizePlanes(self):
        """
        Modifies tree in place so that there are no constant factors in branch weights
        """
        if self.isProbabilistic():
            for child in self.children.domain():
                child.minimizePlanes()
        elif not self.isLeaf():
            self.branch.minimize()
            self.children[True].minimizePlanes()
            self.children[False].minimizePlanes()

    def leaves(self):
        """
        :warning: May return a list containing duplicates
        """
        if self.isLeaf():
            return [self.children[None]]
        elif self.isProbabilistic():
            return sum([child.leaves() for child in self.children.domain()],[])
        else:
            return sum([child.leaves() for child in self.children.values()],[])

    def __hash__(self):
        return hash(tuple(self.children.items()))
#        return hash(str(self))

    def __str__(self):
        if self._string is None:
            if self.isLeaf():
                self._string = str(self.children[None])
            elif self.isProbabilistic():
                # Probabilistic branch
                self._string = '\n'.join(map(lambda el: '%d%%: %s' % (100.*self.children[el],str(el)),self.children.domain()))
            else:
                # Deterministic branch
                if len(self.branch.planes) == 1 and isinstance(self.branch.planes[0][1],list):
                    thresholds = self.branch.planes[0][1][:]
                    if self.branch.planes[0][2] < 0:
                        thresholds.append(1.)
                    elif self.branch.planes[0][2] > 0:
                        thresholds.insert(0,0.)
                    children = '\n'.join(['%s\t%s' % (thresholds[value] if isinstance(value,int) else 'Otherwise',
                                                      str(self.children[value]).replace('\n','\n\t'))
                                          for value in self.children])
                else:
                    children = '\n'.join(['%s\t%s' % (value,str(self.children[value]).replace('\n','\n\t')) for value in self.children])
                self._string = 'if %s\n%s'  % (str(self.branch),children)
                                               
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
                elif isinstance(value,int):
                    node = doc.createElement('int')
                    node.appendChild(doc.createTextNode(str(value)))
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
                elif node.tagName == 'plane':
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
                elif node.tagName == 'int':
                    key = int(node.getAttribute('key'))
                    children[key] = KeyedTree(node)
                elif node.tagName == 'none':
                    key = eval(node.getAttribute('key'))
                    children[key] = None
            node = node.nextSibling
        if plane:
            self.makeBranch(plane,children)
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
    elif isinstance(table,KeyedTree):
        return table
    elif 'if' in table:
        # Binary deterministic branch
        tree = KeyedTree()
        children = {key: makeTree(table[key]) for key in table if key != 'if'}
        tree.makeBranch(table['if'],children)
        return tree
    elif 'case' in table:
        # Non-binary deterministic branch
        keys = set(table.keys())
        keys.remove('case')
        if 'otherwise' in table:
            tree = table['otherwise']
            keys.remove('otherwise')
        else:
            # No default, assume entries are exhaustive and take anyone as the last
            tree = table[keys.pop()]
        for key in keys:
            if isinstance(table['case'],str):
                tree = {'if': equalRow(table['case'],key),
                        True: table[key], False: tree}
            else:
                return NotImplemented
        return makeTree(tree)
    elif 'distribution'in table:
        # Probabilistic branch
        tree = KeyedTree()
        branch = {}
        for subtable,prob in table['distribution']:
            branch[makeTree(subtable)] = prob
        tree.makeProbabilistic(TreeDistribution(branch))
        return tree
    else:
        # Leaf
        return KeyedTree(table)

def collapseDynamics(tree,effects,variables={}):
    effects.reverse()
    present = tree.getKeysIn()
    tree.makeFuture(present)
    for stage in effects:
        subtree = None
        for key,dynamics in stage.items():
            if dynamics and makeFuture(key) in tree.getKeysIn():
                assert len(dynamics) == 1
                if subtree is None:
                    subtree = dynamics[0]
                else:
                    subtree += dynamics[0]
        if subtree:
            if tree is None:
                tree = subtree
            else:
                for key in tree.getKeysIn():
                    if not key in subtree.getKeysOut():
                        fun = lambda m: KeyedMatrix(list(m.items())+[(key,KeyedVector({key: 1.}))])
                        subtree = subtree.map(fun)
                tree = tree*subtree
    future = [key for key in tree.getKeysIn() if isFuture(key)]
    if future:
        tree.makePresent(future)
    return tree.prune(variables=variables)
