from teamwork.agent.Entities import *
from teamwork.multiagent.sequential import *
from teamwork.multiagent.GenericSociety import *
from teamwork.agent.DefaultBased import createEntity
from teamwork.examples.InfoShare.PortClasses import *
from teamwork.math.ProbabilityTree import *

import unittest

class TestRecursiveAgent(unittest.TestCase):
    def setUp(self):
        """Creates the instantiated scenario used for testing"""
        society = GenericSociety()
        society.importDict(classHierarchy)
        entities = []
        self.instances = {'World':1,'FederalAuthority':1,
                          'FirstResponder':1,'Shipper':1}
        for cls,num in self.instances.items():
            for index in range(num):
                if num > 1:
                    name = '%s%d' % (cls,index)
                else:
                    name = cls
            entities.append(createEntity(cls,name,society,PsychEntity))
        self.entities = SequentialAgents(entities)
        self.entities.applyDefaults()
        # Set up the spec of the desired test action
        entity = self.entities['FirstResponder']
        options = entity.actions.getOptions()
        self.inspect = None
        self.pass_ = None
        for act in options:
            if act[0]['type'] == 'inspect':
                self.inspect = act
            elif act[0]['type'] == 'pass':
                self.pass_ = act
        self.assert_(self.inspect)
        self.assert_(self.pass_)

    def testDynamics(self):
        parent = self.entities['FederalAuthority']
        entity = parent.getEntity('FirstResponder')
        state = parent.entities.getState()
        actions = {entity.name:self.pass_}
        dynamics = parent.entities.getDynamics(actions)['state'].getTree()
        goals = parent.getGoalTree()
        print goals*dynamics
        
if __name__ == '__main__':
    unittest.main()
