"""Goals as piecewise linear reward functions
@author: David V. Pynadath <pynadath@ict.usc.edu>
"""
import copy
from xml.dom.minidom import Document
from teamwork.math.Keys import Key,StateKey,ActionKey,keyConstant
from teamwork.math.KeyedVector import KeyedVector
from teamwork.math.KeyedMatrix import ActionCountMatrix,IdentityMatrix
from teamwork.math.ProbabilityTree import ProbabilityTree
from teamwork.action.PsychActions import ActionCondition

class PWLGoal:
    """A reward subfunction represented as a PWL function of some vector (typically the world state)
    @ivar dependency: set of decision trees that represent the reward subfunction over possible action triggers.  It is a list of triples (L{ActionCondition},L{ProbabilityTree},dict).  The third element is a cache of instantiated L{ProbabilityTree}s associated with actions.
    @type dependency: list
    @ivar keys: set of L{Key} instances that this goal depends on
    @type keys: L{Key}[]
    @ivar max: C{True} iff this goal represents a positive incentive; otherwise, it is a disincentive (default is C{True})
    @type max: bool
    @cvar goalFeature: special feature string used to indicate the goals of another agent
    @type goalFeature: str
    """
    goalFeature = 'goals'

    def __init__(self):
        self.max = True
        self.dependency = []
        self.keys = []
        self.cache = {}

    def addDependency(self,condition,tree=None):
        """
        Adds a new dependency to this subfunction
        @param condition: the trigger condition for this dependency
        @type condition: L{ActionCondition}
        @param tree: the PWL function to compute when triggered (ignored if the condition is a counting one)
        @type tree: L{ProbabilityTree}
        """
        self.dependency.append((condition,tree,{}))
        self.cache.clear()

    def toKey(self):
        if len(self.keys) == 1:
            return self.keys[0]
        else:
            raise NotImplementedError,'Unable to manipulate goals over: %s' % \
                (', '.join(map(str,self.keys)))

    def getTree(self,actions={}):
        """
        @param actions: the actions being performed (default is no actions)
        @type actions: strS{->}L{Action}[]
        @return: the decision tree representation of this reward function when the given actions are performed
        @rtype: L{ProbabilityTree}
        """
        for entry in self.dependency:
            if entry[0].count:
                # We want an action count
                weight = self._sign(float(entry[0].match(actions)))
                return ProbabilityTree(KeyedVector({keyConstant: weight}))
            elif entry[0].match(actions):
                # Apply this entry to given context
                tree = entry[1]
                if self.max:
                    tree = copy.deepcopy(tree)
                else:
                    tree = -tree
                return tree
        else:
            # Null reward
            return ProbabilityTree(KeyedVector())
        
    def reward(self,context,actions={}):
        for entry in self.dependency:
            if entry[0].count:
                # We want an action count
                return self._sign(float(entry[0].match(actions)))
            elif entry[0].match(actions):
                # Apply this entry to given context
                return self._sign(entry[1][context['state']]*context['state'])
        else:
            # Null reward
            return 0.

    def _sign(self,value):
        """Applies the appropriate sign to a goal magnitude
        @param value: the (presumably nonnegative) magnitude of the reward
        @type value: float
        @return: the appropriately signed reward value
        @rtype: float
        """
        if self.max:
            return value
        else:
            return -value

    def isMax(self):
        return self.max

    def isMeta(self):
        """
        @return: C{True} iff this is a goal on another agent's goals
        @rtype: bool
        """
        key = self.toKey()
        return isinstance(key,StateKey) and key['feature'] == self.goalFeature

    def instantiate(self,table={}):
        """Specializes an abstract goal in response to the given set of instantiated entities
        @rtype: L{PWLGoal}[]
        """
        goals = []
        if len(self.keys) != 1:
            raise NotImplementedError,'Unable to instantiate goals over %d keys' %\
                (len(self.keys))
        key = self.keys[0]
        newTable = copy.copy(table)
        for newKey in key.instantiate(table):
            if isinstance(key,StateKey):
                if key['entity'] != 'self':
                    newTable[key['entity']] = newKey['entity']
            elif isinstance(key,ActionKey):
                pass
            else:
                raise NotImplementedError,'Unable to instantiate goals on %s' % (key.__class__.__name__)
            goal = PWLGoal()
            goal.max = self.max
            goal.keys.append(newKey)
            for condition,tree,cache in self.dependency:
                tree = tree.instantiate(newTable)
                # Change leaf matrices into vectors
                remaining = [tree]
                while remaining:
                    subtree = remaining.pop()
                    remaining += subtree.children()
                    if subtree.isLeaf():
                        subtree.makeLeaf(subtree.getValue()[newKey])
                goal.addDependency(condition,tree)
            goals.append(goal)
        return goals

    def renameEntity(self,old,new):
        # Update my keys
        for index in range(len(self.keys)):
            if isinstance(self.keys[index],StateKey) and \
                   self.keys[index]['entity'] == old:
                args = {}
                args.update(self.keys[index])
                args['entity'] = new
                self.keys[index] = StateKey(args)
        # Update my dependencies
        for condition,tree,cache in self.dependency:
            tree.renameEntity(old,new)
                
    def __str__(self):
        label = ','.join(map(str,self.keys))
        if self.max:
            return 'Maximize %s' % (label)
        else:
            return 'Minimize %s' % (label)

    def __hash__(self):
        return hash(str(self))

    def __xml__(self):
        doc = Document()
        root = doc.createElement('goal')
        doc.appendChild(root)
        root.setAttribute('max',str(self.max))
        for key in self.keys:
            root.appendChild(key.__xml__().documentElement)
        for condition,tree,cache in self.dependency:
            root.appendChild(condition.__xml__().documentElement)
            root.appendChild(tree.__xml__().documentElement)
        return doc

    def parse(self,element):
        self.max = not (str(element.getAttribute('max')) == str(False))
        node = element.firstChild
        condition = None
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                if node.tagName == 'key':
                    key = Key()
                    self.keys.append(key.parse(node))
                elif node.tagName == 'condition':
                    condition = ActionCondition()
                    condition.parse(node)
                elif node.tagName == 'tree':
                    tree = ProbabilityTree()
                    try:
                        tree.parse(node,KeyedVector)
                    except AssertionError:
                        # I'm a hack to handle matrix-based goal representations
                        # which should be phased out at some point
                        tree.parse(node)
                    assert not condition is None
                    self.addDependency(condition,tree)
                    condition = None
            node = node.nextSibling
        self.cache.clear()
        return self

def maxGoal(key):
    """Creates a L{PWLGoal} corresponding to a maximization goal
    @param key: the L{Key} that points to the vector element to be maximized
    @type key: L{Key}
    @rtype: L{PWLGoal}
    """
    goal = PWLGoal()
    goal.max = True
    goal.keys.append(key)
    if isinstance(key,StateKey):
        matrix = IdentityMatrix(source=key)
    elif isinstance(key,ActionKey):
        matrix = ActionCountMatrix(key,key,0.)
    else:
        raise NotImplementedError,'Unable to make simple goal on %s' % (str(key))
    tree = ProbabilityTree()
    tree.makeLeaf(matrix)
    goal.addDependency(ActionCondition(),tree)
    return goal

def minGoal(key):
    """Creates a L{PWLGoal} corresponding to a minimization goal
    @param key: the L{Key} that points to the vector element to be minimized
    @type key: L{Key}
    @rtype: L{PWLGoal}
    """
    goal = maxGoal(key)
    goal.max = False
    return goal
