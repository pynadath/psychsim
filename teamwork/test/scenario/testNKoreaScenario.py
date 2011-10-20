import unittest
from xml.dom.minidom import parse
from teamwork.multiagent.sequential import SequentialAgents
from teamwork.agent.Entities import *


class TestNKoreaScenario(unittest.TestCase):
    debug = None
    
    def setUp(self):
        doc = parse("nkorea.xml")
        self.scenario = SequentialAgents()
        self.scenario.parse(doc.documentElement, PsychEntity);
        #self.scenario.compileDynamics()

    def testMicrostep(self):
        result = self.scenario.microstep([{'name':'NK Soldier'}], hypothetical=True, explain=True)
        result = self.scenario.microstep([{'name':'NK Soldier'}], explain=True)

    def testMessage(self):
        factor = {}
        factor['topic'] = 'state'
        factor['lhs'] = ['entities', 'NK Pol. Off.', 'state', 'Political Power']
        dist = Distribution()
        dist[-1.0] = 1
        factor['value'] = dist
        factor['relation'] = '='
        msg = Message({'factors':[factor]})
        msg.forceAccept()
        receives = []
        overhears = []
        receives.append('NK CDR')
        overhears.append('NK Pol. Off.')
        result = self.scenario.performMsg(msg, 'NK Soldier', receives, overhears)

    def testAction(self):
        actor = self.scenario['NK Pol. Off.']
        options = actor.actions.getOptions()
        for actlist in options:
            if actlist[0]['actor'] == 'NK Pol. Off.' and actlist[0]['type'] == 'Denounce Group' and actlist[0]['object'] == 'NK Sec. Off.':
                action = actlist[0]
                break
        turn = [{'name':'NK Pol. Off.', 'choices':[[action]]}]
        result = self.scenario.microstep(turn, hypothetical=False, explain=True)

        
if __name__ == '__main__':
    unittest.main()
