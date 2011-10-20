from teamwork.agent.DefaultBased import *
from teamwork.agent.Entities import *
from teamwork.multiagent.sequential import *
from teamwork.multiagent.GenericSociety import *
from teamwork.action.PsychActions import *
from ThespianActions import ThespianAction
from ThespianMessage import *
from ThespianGeneric import *

from teamwork.dynamics.pwlDynamics import *
                 
class ThespianAgents(SequentialAgents):
    
    sceneID = 6
    
    def generateOrder(self,entities=None):
        """Creates a new order vector.  Orders the agents according to the comparison  method on the member agents
        @return: the turn state vector suitable for the initial state of the simulation
        @rtype: L{KeyedVector}
        """
        if entities is None:
            entities = self.activeMembers()
            
        # Create ordered list of relevant agents
        if self.sceneID == '-1':
            entities = ['student','Kamela','Xaled','Abasin','Hamed']
        elif self.sceneID == '6':
            newEntities = list(range(len(entities)))
            for index in range(len(entities)):
                agent = entities[index]
                if agent.name == 'usr':
                    newEntities[0] = agent
                elif agent.name == 'streetrat':
                    newEntities[1] = agent
                elif agent.name == 'labrat1':
                    newEntities[2] = agent
                elif agent.name == 'labrat2':
                    newEntities[3] = agent
                elif agent.name == 'otherTeam':
                    newEntities[4] = agent
                elif agent.name == 'timer':
                    newEntities[5] = agent              
        else:
            entities.sort()
            
        return SequentialAgents.generateOrder(self,entities)



    def createTurnDynamics(self,actions):
        """Computes the change in turn due to the specified actions
        @param actions: the actions being performed, indexed by actor name
        @type actions: C{dict:strS{->}L{teamwork.action.PsychActions.Action}[]}
        @return: a decision tree representing the changes to the standing turn order vector based on the specified actions
        @rtype: L{KeyedTree}
        """
        
        assert(len(actions) == 1)
        ## Thespian, update position if activeMembers changes
        #need_to_update_generateOrder = 0
        #active = self.activeMembers()
        #for activeEntity in active:
        #    if not self.positions.has_key(activeEntity.name):
        #        need_to_update_generateOrder = 1
        #        break
        #
        #if need_to_update_generateOrder:
        #    self.generateOrder()

        ## updat need_to_update_turn
        ## special for Thespian
        actor,action = actions.items()[0]
        need_to_update_turn = 1
##        for act in action:
####            if isinstance(act,ThespianMessage) or  isinstance(act,ThespianAction):
##            try:
##                if act['type']!='wait':
##                    need_to_update_turn = 0
##            except:
##                try:
##                    if not string.find(act,'wait')>-1:
##                        need_to_update_turn = 0
##                except:
##                    pass

        # Unless the actor is taking another turn, then no change
        
        ## hack for now, not sure how to not compile actions that not possible to happen
        actor = actions.keys()[0]
        if not actor in self.activeMembers():
            need_to_update_turn = 0
        
        unchangedMatrix = KeyedMatrix()
        for agent in self.activeMembers():
            key = StateKey({'entity':agent.name,
                            'feature':self.turnFeature})
            row = KeyedVector()
            row[key] = 1.
            unchangedMatrix[key] = row
        row = KeyedVector()
        row[keyConstant] = 1.
        unchangedMatrix[keyConstant] = row
        # Check whether anyone ever has a turn
##        if len(self) == 0:
        if len(self) == 0 or  need_to_update_turn == 0:
            tree = KeyedTree()
            tree.makeLeaf(unchangedMatrix)
            return tree
        actor = actions.keys()[0]
        # Test whether anybody's left to act after these new actions
        resetWeights = KeyedVector()
        for agent in self.activeMembers():
            if not actions.has_key(agent.name):
                resetWeights[StateKey({'entity':agent.name,
                                       'feature':self.turnFeature})] = 1.
        resetPlane = KeyedPlane(resetWeights,0.0001)
        # If so, move the leftover actors up in the turn order
        updateMatrix = KeyedMatrix()
        for agent in self.activeMembers():
            key = StateKey({'entity':agent.name,
                            'feature':self.turnFeature})
            row = KeyedVector()
            if actions.has_key(agent.name):
                # Reset activation to 0.
                pass
            elif self.positions[agent.name] < self.positions[actor]:
                # If we're behind the actor, then move up in the order
                row[key] = 2.
            else:
                # If we're ahead of the actor, stay where we are
                row[key] = 1.
            updateMatrix[key] = row
        row = KeyedVector()
        row[keyConstant] = 1.
        updateMatrix[keyConstant] = row
        # Test whether actor is sneaking in a second turn
        alreadyActed = ThresholdRow(keys=[{'entity':actor,
                                           'feature':self.turnFeature}])
        updateTree = KeyedTree()
        updateTree.branch(KeyedPlane(alreadyActed,0.),
                          unchangedMatrix,updateMatrix)
        # If nobody left to act, start the turn order from the beginning
        resetMatrix = KeyedMatrix()
        for agent in self.activeMembers():
            key = StateKey({'entity':agent.name,
                            'feature':self.turnFeature})
            row = KeyedVector()
            row[keyConstant] = self.positions[agent.name]
            resetMatrix[key] = row
        row = KeyedVector()
        row[keyConstant] = 1.
        resetMatrix[keyConstant] = row
        # Create branch on number of people left to act
        tree = KeyedTree()
        tree.branch(resetPlane,resetMatrix,updateTree)
        return tree



