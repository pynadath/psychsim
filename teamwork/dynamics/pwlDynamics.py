"""Dynamics objects for the PWL implementation
@var constantDynamics: a reusable instance of dynamics for the constant value in the state vector
@type constantDynamics: L{PWLDynamics}
"""
import copy
from xml.dom.minidom import Document
from teamwork.action.PsychActions import Action
from teamwork.math.Keys import keyConstant
#from teamwork.math.matrices import *
from teamwork.math.KeyedVector import KeyedVector
from teamwork.math.KeyedMatrix import KeyedMatrix,IdentityMatrix
from teamwork.math.ProbabilityTree import ProbabilityTree,createBranchTree,createNodeTree
import arbitraryDynamics

class PWLDynamics(arbitraryDynamics.BaseDynamics):
    """Class of objects that represent the dynamics of a specific
    state/belief feature in the simulation
    @ivar effects: table of roles affected, containing keys 'actor','object','other'.  If the value is C{True}, then the dynamics object affects that role
    @type effects: strS{->}bool
    """

    def __init__(self,args=None):
        arbitraryDynamics.BaseDynamics.__init__(self,args)
        self.effects = {}

    def extractTable(self,entity,action,table={}):
        """Helper function that extracts the context used in instantiating dynamics
        @rtype: dict
        """
        if len(table) == 0:
            # Extract fields from action
            table = dict(action)
        # Add self field
        table['self'] = entity
        # Extract relationship fillers
        for relationship,entities in entity.relationships.items():
            if len(entities) == 1:
                table[relationship] = entities[0]
        # Extract class fillers
        for entity in entity.world.members():
            for cls in entity.classes:
                try:
                    table[cls].append(entity.name)
                except KeyError:
                    table[cls] = [entity.name]
        return table
    
    def instantiate(self,entity,actions):
        """Returns a new L{PWLDynamics} instance that has been specialized to apply to only the specified entity in response to the specified instantiated action.  This produces a more compact decision tree where branches irrelevant to the given entity and action have been pruned away.
        @type actions: dict
        @rtype: L{PWLDynamics}
        """
        if isinstance(actions,Action):
            actions = [actions]
        else:
            actions = sum(actions.values(),[])
        if len(actions) == 0:
            table = self.extractTable(entity,{})
        else:
            table = {}
            for action in actions:
                table = self.extractTable(entity,action,table)
        args = copy.copy(self.args)
        args['tree'] = self.getTree().instantiate(table)
        args['tree'].prune()
        return self.__class__(args)

    def instantiateAndApply(self,state,entity=None,action=None,
                            table={},tree=None):
        """Performs both L{instantiate} and L{apply} in a single call, but does a minimal instantiation, by ignoring branches that are irrelevant in the given state
        @param entity: the entity performing the update
        @type entity: L{Agent<teamwork.agent.Agent.Agent>}
        @param action: the action being applied
        @type action: L{Action<teamwork.action.PsychActions.Action>}
        @param state: the current state of the world
        @type state: L{Distribution}(L{KeyedVector})
        @rtype: L{Distribution}(L{KeyedMatrix})
        """
        if not table:
            table = self.extractTable(entity,action)
        if tree is None:
            tree = self.getTree()
        if tree.isLeaf():
            return tree.getValue().instantiate(table)
        else:
            falseTree,trueTree = tree.getValue()
            value = True
            for plane in tree.split:
                result = plane.instantiate(table)
                if isinstance(result,plane.__class__):
                    value = result.test(state)
                elif result < 0:
                    value = False
                if not value:
                    break
            if value:
                return self.instantiateAndApply(state,table=table,
                                                tree=trueTree)
            else:
                return self.instantiateAndApply(state,table=table,
                                                tree=falseTree)
            
    def isAdditive(self):
        """
        @return: C{True} iff is additive; otherwise, should be composed
        @rtype: bool
        """
        try:
            return self.args['additive']
        except KeyError:
            # Additive by default
            return True

    def makeAdditive(self):
        """
        Makes this dynamics function additive
        """
        self.args['additive'] = True
        self.getTree().makeAdditive()

    def makeNonadditive(self):
        """
        Makes this dynamics function additive (i.e., composed)
        """
        self.args['additive'] = False
        self.getTree().makeNonadditive()

    def getTree(self):
        """
        @return: the decision tree for this dynamics object
        @rtype: L{ProbabilityTree}"""
        return self.args['tree']
    
    def apply(self,state,debug=0):
        """Applies this dynamics function to the given state
        @rtype: L{Distribution}(L{KeyedMatrix})
        """
        tree = self.getTree()
        dynamics = tree[state]
        return dynamics

    def merge(self,other):
        """Merges the new dynamics into this one by calling L{KeyedMatrix.merge} on the leaves of the decision trees
        @type other: L{PWLDynamics}
        """
        myTree = self.getTree()
        yrTree = other.getTree()
        newTree = myTree.merge(yrTree,KeyedMatrix.merge)
        args = {}
        args.update(self.args)
        args['tree'] = newTree
        return self.__class__(args)

    def renameEntity(self,old,new):
        """
        @param old: the current name of the entity
        @param new: the new name of the entity
        @type old,new: str
        """
        self.getTree().renameEntity(old,new)
                
    def __add__(self,other):
        myTree = self.getTree()
        yrTree = other.getTree()
        newTree = myTree + yrTree
        args = {}
        args.update(self.args)
        args['tree'] = newTree
        return self.__class__(args)

    def __sub__(self,other):
        myTree = self.getTree()
        yrTree = other.getTree()
        newTree = myTree - yrTree
        args = {}
        args.update(self.args)
        args['tree'] = newTree
        return self.__class__(args)
                
    def __mul__(self,other):
        myTree = self.getTree()
        yrTree = other.getTree()
        newTree = myTree * yrTree
        args = {}
        args.update(self.args)
        args['tree'] = newTree
        return self.__class__(args)

    def fill(self,keys):
        """
        Fills in the branches and leaves to cover all of the mentioned keys.  For any key other than the one relevant to this dynamics function, an identity row is inserted
        @warning: irrevocably changes this dynamics function
        """
        for matrix in self.getTree().leaves():
            for key in keys:
                if not matrix.has_key(key):
                    matrix.set(key,key,1.)
        self.getTree().fill(keys)
        self.getTree().freeze()

    def __xml__(self):
        doc = Document()
        root = doc.createElement('dynamic')
        doc.appendChild(root)
        try:
            root.setAttribute('additive','%d' % (int(self.args['additive'])))
        except KeyError:
            root.setAttribute('additive','1')
        tree = self.getTree()
        root.appendChild(tree.__xml__().documentElement)
        return doc

    def parse(self,element):
        try:
            self.args['additive'] = bool(int(element.getAttribute('additive')))
        except ValueError:
            self.args['additive'] = True
        self.args['tree'] = ProbabilityTree()
        child = element.firstChild
        while child and child.nodeType != child.ELEMENT_NODE:
            child = child.nextSibling
        if child:
            self.args['tree'].parse(child)
        else:
            print element.toxml()
            raise UserWarning,'Dynamics element missing tree!'

    def __str__(self):
        return self.getTree().simpleText()
    
def NullDynamics():
    """
    @return: a dynamics object with a zero matrix
    @rtype: L{PWLDynamics}
    """
    dynamics = ProbabilityTree()
    dynamics.makeLeaf(KeyedMatrix())
    return PWLDynamics({'tree':dynamics})

def IdentityDynamics(feature):
    """
    @param feature: the feature to be held constant
    @type feature: str
    @return: a dynamics object with an identity matrix over the given feature
    @rtype: L{PWLDynamics}
    """
    dynamics = ProbabilityTree()
    dynamics.makeLeaf(IdentityMatrix(feature))
    return PWLDynamics({'tree':dynamics})

def ConstantDynamics():
    """
    @return: a dynamics object with an identity matrix over the constant value
    @rtype: L{KeyedMatrix}
    """
    row = KeyedVector({keyConstant:1.})
    matrix = KeyedMatrix()
    matrix[keyConstant] = row
    return matrix

constantDynamics = ConstantDynamics()
