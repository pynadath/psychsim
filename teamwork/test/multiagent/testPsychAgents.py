from teamwork.math.Keys import StateKey
from teamwork.action.PsychActions import Action
from teamwork.multiagent.PsychAgents import loadScenario
import os
import unittest

class TestPsychAgents(unittest.TestCase):
    debug = False
    
    def setUp(self):
        """Creates the instantiated scenario used for testing"""
        self.scenario = loadScenario(os.path.join(os.path.dirname(__file__),'..','..',
                                                'examples','school','school.scn'))
        self.scenario.initialize()
        
    def testInitial(self):
        """Tests that the instantiated scenario is what it should be"""
        # Test proper membership
        self.assertEqual(len(self.scenario),4)
        self.assertEqual(len(self.scenario.members()),4)
        self.assert_(self.scenario.has_key('Bill'))
        self.assert_(self.scenario.has_key('Mrs. Thompson'))
        self.assert_(self.scenario.has_key('Otto'))
        self.assert_(self.scenario.has_key('Victor'))
        # Test state values
        for agent in self.scenario.members():
            self.assertEqual(len(agent.getStateFeatures()),1)
            happiness = agent.getState('happiness')
            self.assertEqual(len(happiness),1)
            self.assertAlmostEqual(happiness.expectation(),0.)
        # Test action space
        for agent in self.scenario.members():
            if agent.instanceof('teacher'):
                self.assertEqual(agent.name,'Mrs. Thompson')
                self.assertEqual(len(agent.actions.getOptions()),5)
            else:
                self.assertEqual(len(agent.actions.getOptions()),5)
        # Test goals
        for agent in self.scenario.members():
            if agent.instanceof('teacher'):
                self.assertEqual(len(agent.goals),4)
            else:
                self.assertEqual(len(agent.goals),1)
        # Test order
        self.assertEqual(len(self.scenario.order),5)
        for agent in self.scenario.members():
            key = StateKey({'entity': agent.name,'feature': self.scenario.turnFeature})
            self.assert_(self.scenario.order.has_key(key))

    def testEffects(self):
        old = self.scenario.state.expectation()
        # Bill picks on Victor
        bully = self.scenario['Bill']
        for option in bully.actions.getOptions():
            if len(option) == 1 and option[0]['type'] == 'pick on' and option[0]['object'] == 'Victor':
                break
        else:
            self.fail('Missing pick on action')
        self.scenario.microstep([{'name':bully.name,'choices': [option]}])
        # Test effect of picking on
        self.assertEqual(len(self.scenario.state),1)
        new = self.scenario.state.expectation()
        delta = new - old
        for key in delta.keys():
            if isinstance(key,StateKey) and key['entity'] == 'Victor' and \
                    key['feature'] == 'happiness':
                self.assertAlmostEqual(delta[key],-.2,8)
            else:
                self.assertAlmostEqual(delta[key],0.,8)
        # Test turn order
        next = self.scenario.next()
        self.assertEqual(len(next),1)
        self.assertNotEqual(next[0]['name'],'Bill')
        # Test Mrs. Thompson punishes all
        teacher = self.scenario['Mrs. Thompson']
        for option in teacher.actions.getOptions():
            if len(option) == 1 and option[0]['type'] == 'punish all':
                break
        else:
            self.fail('Missing punish all action')
        old = new
        self.scenario.microstep([{'name':teacher.name,'choices': [option]}])
        # Test effect of picking on
        self.assertEqual(len(self.scenario.state),1)
        new = self.scenario.state.expectation()
        delta = new - old
        for key in delta.keys():
            if isinstance(key,StateKey) and key['entity'] == 'Victor' and \
                    key['feature'] == 'happiness':
                self.assertAlmostEqual(delta[key],-.08,8)
            elif isinstance(key,StateKey) and key['feature'] == 'happiness' and \
                    (key['entity'] == 'Bill' or key['entity'] == 'Otto'):
                self.assertAlmostEqual(delta[key],-.1,8)
            else:
                self.assertAlmostEqual(delta[key],0.,8)
        # Test turn order
        next = self.scenario.next()
        self.assertEqual(len(next),1)
        self.assertNotEqual(next[0]['name'],'Bill')
        self.assertNotEqual(next[0]['name'],'Mrs. Thompson')

    def testDecision(self):
        # Hypothetical step
        old = self.scenario.state.expectation()
        result = self.scenario.microstep(hypothetical=True,explain=True)
        # Make sure hypothetical step had no effect on state
        new = self.scenario.state.expectation()
        delta = new - old
        for key in delta.keys():
            self.assertAlmostEqual(delta[key],0.,8)
        # Make sure bully got first turn and chose a legal action
        bully = self.scenario['Bill']
        self.assertEqual(len(result['decision']),1)
        self.assertEqual(result['decision'].keys(),[bully.name])
        decision = result['decision'][bully.name]
        for option in bully.actions.getOptions():
            if option == decision:
                break
        else:
            self.fail('Decision not in bully action space')
        # Check explanation
        turn = result['explanation'].documentElement.firstChild
        exp = None
        while turn:
            if turn.nodeType == turn.ELEMENT_NODE and turn.tagName == 'turn':
                node = turn.firstChild
                while node:
                    if node.nodeType == node.ELEMENT_NODE:
                        if node.tagName == 'decision':
                            # Verify that decision in explanation structure matches real decision
                            option = []
                            actionNode = node.firstChild
                            while actionNode:
                                action = Action()
                                action.parse(actionNode)
                                option.append(action)
                                actionNode = actionNode.nextSibling
                            self.assertEqual(option,decision)
                        elif node.tagName == 'explanation':
                            # Make sure no other explanation node exists
                            self.assert_(exp is None)
                            exp = node
                        else:
                            self.fail('Unknown explanation node: %s' % (node.tagName))
                    node = node.nextSibling
            turn = turn.nextSibling
        # Verify explanation
        node = exp.firstChild
        value = float(exp.getAttribute('value'))
        first = True
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                if node.tagName == 'expectations':
                    # Verify projection of chosen action
                    turn = node.firstChild
                    while turn:
                        self.assertEqual(turn.tagName,'turn')
                        option = []
                        actionNode = turn.firstChild
                        while actionNode:
                            if actionNode.tagName == 'action':
                                action = Action()
                                action.parse(actionNode)
                                option.append(action)
                            actionNode = actionNode.nextSibling
                        if first:
                            self.assertEqual(action['actor'],bully.name)
                            self.assertEqual(option,decision)
                            first = False
                        actions = {action['actor']: option}
                        delta = self.scenario.hypotheticalAct(actions)
                        turn = turn.nextSibling
            node = node.nextSibling
