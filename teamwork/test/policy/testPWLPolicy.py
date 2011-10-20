import bz2
import unittest
from xml.dom.minidom import parseString

from teamwork.math.KeyedVector import KeyedVector
from teamwork.multiagent.PsychAgents import PsychAgents
from teamwork.multiagent.GenericSociety import GenericSociety
from teamwork.agent.Entities import PsychEntity

class TestPWLPolicy(unittest.TestCase):
    """Uses the meeting scenario to test various PWL policy manipulations
    """
    
    def setUp(self):
        f = bz2.BZ2File('examples/meeting.scn','r')
        doc = parseString(f.read())
        f.close()
        self.scenario = PsychAgents()
        self.scenario.parse(doc.documentElement,PsychEntity,GenericSociety)
        self.scenario.initialize()
        
    def testSE(self):
        self.assertEqual(len(self.scenario.state.domain()),1)
        self.assertEqual(len(self.scenario),2)
        agent1,agent2 = self.scenario.members()
        # Verify possible worlds
        worlds = self.scenario.getWorlds()
        self.assertEqual(len(worlds),16)
        # Verify joint reward function
        R = self.scenario.jointReward()
        self.assertEqual(len(R),len(agent1.actions.getOptions())*
                         len(agent2.actions.getOptions()))
        # Verify transition matrix
        T = self.scenario.getDynamicsMatrix()
        self.assertEqual(len(R),len(T))
        self.scenario.nullPolicy()
        # Verify state estimator
        SE = agent1.getEstimator(self.scenario)
        self.assertEqual(len(SE),len(agent1.getOmega()))
        for omega in agent1.getOmega():
            self.assertEqual(len(SE[omega]),1)
        rule = SE[omega].rules[0]
        self.assertEqual(len(rule['values']),len(agent1.actions.getOptions()))
        numerators = {}
        for option1 in agent1.actions.getOptions():
            options = {agent1.name: option1}
            options[agent2.name],explanation = agent2.applyPolicy()
            actionKey = self.scenario.makeActionKey(options)
            state0 = self.scenario.state2world()
            state1 = T[actionKey] * state0
            self.assertAlmostEqual(sum(state1.getArray()),1.,8)
            O = agent1.getObservationMatrix(options,self.scenario.getWorlds())
            for omega in agent1.getOmega():
                belief = KeyedVector()
                for key in state1.keys():
                    belief[key] = O[omega][key]*state1[key]
                try:
                    numerators[omega][str(option1)] = belief
                except KeyError:
                    numerators[omega] = {str(option1): belief}
        for omega in agent1.getOmega():
            vectors = numerators[omega].values()
            for option1 in agent1.actions.getOptions():
                numerator = numerators[omega][str(option1)]
                denominator = sum(numerator.getArray())
                belief = SE[omega].rules[0]['values'][str(option1[0])]*state0
                if denominator > 1e-8:
                    numerator *= 1./denominator
                    belief *= 1./sum(belief.getArray())
                    self.assertAlmostEqual(sum(numerator.getArray()),1.,8)
                    self.assertAlmostEqual(sum(belief.getArray()),1.,8)
                else:
                    # Impossible observations: if we stay where we are (bottom-right), we see left wall
                    self.assertEqual(str(omega),'right')
                    self.assert_(option1[0]['type'] in ['down','left','stay'])
                    self.assertAlmostEqual(sum(belief.getArray()),0.,8)
            
if __name__ == '__main__':
    unittest.main()
