from PsychAgents import PsychAgents
from teamwork.math.matrices import epsilon
from teamwork.math.Keys import StateKey,keyConstant
from teamwork.math.KeyedVector import KeyedVector,ThresholdRow
from teamwork.math.KeyedMatrix import KeyedMatrix
from teamwork.math.KeyedTree import KeyedPlane,KeyedTree

class SequentialAgents(PsychAgents):
    """A utility class that supports sequential turns by a group of agents.  The order is determined by the ordering methods on the component agent classes.
    @warning: sequentiality is required, so don't try having multiple agents act at the same time.
    """
    def OLDgenerateOrder(self,entities=None):
        """Creates a new order vector.  Orders the agents according to the comparison  method on the member agents
        @param entities: the ordered list of entities to use (if omitted, defaults to the sorted list of active members)
        @type entities: L{teamwork.agent.Agent.Agent}[]
        @return: the turn state vector suitable for the initial state of the simulation
        @rtype: L{KeyedVector}
        """
        self._turnDynamics.clear()
        if entities is None:
            entities = self.activeMembers()
            entities.sort()
        elif isinstance(entities[0],list):
            # Not a serial turn order
            return PsychAgents.generateOrder(self,entities)
        order = KeyedVector()
        for index in range(len(entities)):
            if isinstance(entities[index],str):
                agent = entities[index]
            else:
                agent = entities[index].name
            value = self.pos2float(index)
#            self.positions[agent] = value
            order[StateKey({'entity':agent,
                            'feature':self.turnFeature})] = value
        order[keyConstant] = 1.
        order.freeze()
        return order

    def createTurnDynamics(self,actions):
        """Computes the change in turn due to the specified actions
        @param actions: the actions being performed, indexed by actor name
        @type actions: C{dict:strS{->}L{teamwork.action.PsychActions.Action}[]}
        @return: a decision tree representing the changes to the standing turn order vector based on the specified actions
        @rtype: L{KeyedTree}
        """
        if len(actions) != 1:
            return PsychAgents.createTurnDynamics(self,actions)
        # Unless the actor is taking another turn, then no change
        unchangedMatrix = KeyedMatrix()
        for key in self.order.keys():
            row = KeyedVector()
            row[key] = 1.
            unchangedMatrix[key] = row
        row = KeyedVector()
        row[keyConstant] = 1.
        unchangedMatrix[keyConstant] = row
        # Check whether anyone ever has a turn
        if len(self) == 0:
            tree = KeyedTree()
            tree.makeLeaf(unchangedMatrix)
            return tree
        actor = actions.keys()[0]
        # Test whether anybody's left to act after these new actions
        resetWeights = KeyedVector()
        for key in self.order.keys():
            if isinstance(key,StateKey) and not actions.has_key(key['entity']):
                resetWeights[key] = 1.
        resetPlane = KeyedPlane(resetWeights,0.0001)
        # If so, move the leftover actors up in the turn order
        updateMatrix = KeyedMatrix()
        for key in self.order.keys():
            row = KeyedVector()
            if isinstance(key,StateKey):
                if actions.has_key(key['entity']):
                    # Reset activation
                    value = pow(2,len(self.activeMembers())-1)
                    row[keyConstant] = 1./value*self.threshold + epsilon
                else:
                    # Move up in the order
                    row[key] = 2.
            else:
                # Constant
                row[key] = 1.
            updateMatrix[key] = row
        # Test whether actor is sneaking in a second turn
        alreadyActed = ThresholdRow(keys=[{'entity':actor,
                                           'feature':self.turnFeature}])
        updateTree = KeyedTree()
        updateTree.branch(KeyedPlane(alreadyActed,0.),
                          unchangedMatrix,updateMatrix)
        # If nobody left to act, start the turn order from the beginning
        resetMatrix = KeyedMatrix()
        for key in self.order.keys():
            row = KeyedVector()
            resetMatrix[key] = row
        for position in range(len(self.initialOrder)):
            value = self.pos2float(position)
            if isinstance(self.initialOrder[position],list):
                for name in self.initialOrder[position]:
                    key = StateKey({'entity': name,'feature': self.turnFeature})
                    resetMatrix.set(key, keyConstant, value)
            else:
                key = StateKey({'entity': self.initialOrder[position],'feature': self.turnFeature})
                resetMatrix.set(key, keyConstant, value)
        resetMatrix.set(keyConstant,keyConstant,1.)
        # Create branch on number of people left to act
        tree = KeyedTree()
        tree.branch(resetPlane,resetMatrix,updateTree)
        return tree
