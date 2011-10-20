from teamwork.agent.Entities import *
from teamwork.agent.Generic import *
from teamwork.multiagent.sequential import *
from teamwork.multiagent.GenericSociety import *
from teamwork.agent.DefaultBased import createEntity
from teamwork.examples.PSYOP.Society import *
import unittest

class TestXML(unittest.TestCase):
    """Tests the XML packing and unpacking of scenarios (and some of the components)"""
    
    def setUp(self):
        """Creates the instantiated scenario used for testing"""
        self.society = GenericSociety()
        self.society.importDict(classHierarchy)
        entities = []
        self.instances = {'Turkomen':['ITF'],
                          'Kurds':['KDP'],
                          'US':['US'],
                          'GeographicArea':['NorthernIraq']
                          }
        for cls,names in self.instances.items():
            for name in names:
                entity = createEntity(cls,name,self.society,PsychEntity)
                entities.append(entity)
                if cls in ['Turkomen','Kurds']:
                    entity.relationships = {'location':['NorthernIraq']}
        self.entities = SequentialAgents(entities)
        self.entities.applyDefaults()
        self.entities.compileDynamics()

    def verifyEntities(self,e1,e2):
        """Tests the equality of the two given entities
        """
        self.assertEqual(e1.name,e2.name)
        # Test state
        self.assertEqual(e1.state,e2.state)
        for feature in e1.getStateFeatures():
            self.assert_(feature in e2.getStateFeatures())
        for feature in e2.getStateFeatures():
            self.assert_(feature in e1.getStateFeatures())
        # Test beliefs
        for belief in e1.getEntityBeliefs():
            self.verifyEntities(belief,e2[belief.name])
        for belief in e2.getEntityBeliefs():
            self.assert_(belief.name in e1.getEntities())
        if e1.parent:
            self.assertEqual(e1.parent.ancestry(),e2.parent.ancestry())
        else:
            self.assertEqual(e2.parent,None)
        # Test actions
        for action in e1.actions.getOptions():
            self.assert_(action in e2.actions.getOptions())
        for action in e2.actions.getOptions():
            self.assert_(action in e1.actions.getOptions())
        # Test relationships
        for label,agents in e1.relationships.items():
            self.assert_(e2.relationships.has_key(label))
            for name in agents:
                self.assert_(name in e2.relationships[label])
        for label,agents in e2.relationships.items():
            self.assert_(e1.relationships.has_key(label))
            for name in agents:
                self.assert_(name in e1.relationships[label])
        # Test goals
        for goal in e1.getGoals():
            self.assertAlmostEqual(e1.getGoalWeight(goal),e2.getGoalWeight(goal),8,
                                   '%s has incorrect weight for goal %s' % \
                                   (e2.ancestry(),goal))
        for goal in e2.getGoals():
            self.assertAlmostEqual(e1.getGoalWeight(goal),e2.getGoalWeight(goal),8)
        # Test dynamics
        for feature,subDict in e1.dynamics.items():
            self.assert_(e2.dynamics.has_key(feature))
            for actType,dynamics in subDict.items():
                if isinstance(actType,str):
                    self.assert_(e2.dynamics[feature].has_key(actType),
                                 '%s missing dynamics of %s in response to %s' % \
                                 (e2.ancestry(),feature,actType))
                    tree1 = dynamics.getTree()
                    tree2 = e2.dynamics[feature][actType].getTree()
                    self.assertEqual(tree2,tree1,
                                     'Error in %s\'s dynamics of %s in response to %s' % \
                                     (e2.ancestry(),feature,actType))

    def DONTtestEntityXML(self):
        for entity in self.entities.members():
            doc = entity.__xml__()
            new = PsychEntity('dummy')
            new.parse(doc.documentElement)
            self.verifyEntities(entity,new)
        
    def testScenarioXML(self):
        doc = self.entities.__xml__()
        entities = SequentialAgents()
        entities.parse(doc.documentElement,PsychEntity)
        for entity in self.entities.members():
            self.verifyEntities(entity,entities[entity.name])
        self.assertEqual(len(self.entities.dynamics),len(entities.dynamics))
        for action,old in self.entities.dynamics.items():
            self.assert_(entities.dynamics.has_key(action))
            new = entities.dynamics[action]
            self.assert_(new.has_key('state'),
                         'Missing state dynamics for %s' % (action))
            self.assertEqual(old['state'].getTree(),new['state'].getTree())
            self.assert_(new.has_key('actions'),
                         'Missing action dynamics for %s' % (action))
            self.assertEqual(old['actions'],new['actions'])
            
    def DONTtestSocietyXML(self):
        doc = self.society.__xml__()
        society = GenericSociety()
        society.parse(doc.documentElement)
        for entity in self.society.members():
            self.verifyEntities(entity,society[entity.name])
            
if __name__ == '__main__':
    unittest.main()
