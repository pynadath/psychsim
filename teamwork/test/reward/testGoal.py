from teamwork.math.Keys import StateKey,ActionKey,keyConstant
from teamwork.math.KeyedVector import KeyedVector
from teamwork.math.probability import Distribution
from teamwork.math.ProbabilityTree import ProbabilityTree
from teamwork.action.PsychActions import Action,ActionCondition
from teamwork.reward.goal import *
import unittest

class TestPWLGoal(unittest.TestCase):
    """Unit test for L{PWLGoal} class
    """
    def setUp(self):
        self.verbs = ['Listen','OpenLeft','OpenRight']
        self.players = ['Player 1','Player 2']
        self.joints = []
        for index in range(pow(len(self.verbs),len(self.players))):
            joint = {}
            for player in self.players:
                subIndex = index % len(self.verbs)
                joint[player] = [Action({'actor': player,
                                         'type': self.verbs[subIndex]})]
                index /= len(self.verbs)
            self.joints.append(joint)
        self.tiger = StateKey({'entity': 'Tiger','feature': 'position'})
        self.left = KeyedVector({self.tiger: 0.,keyConstant: 1.})
        self.right = KeyedVector({self.tiger: 1.,keyConstant: 1.})
        self.state = Distribution({self.left: 0.5, self.right: 0.5})

    def createCountGoal(self,verb):
        key = ActionKey({'type': verb})
        goal = PWLGoal()
        goal.keys.append(key)
        condition = ActionCondition(count=True)
        condition.addCondition(verb)
        goal.addDependency(condition)
        return goal

    def testCountGoal(self):
        """Goal that increases with the number of actions
        """
        for verb in self.verbs:
            goal = self.createCountGoal(verb)
            for actions in self.joints:
                count = map(lambda a: a[0]['type'],actions.values()).count(verb)
                reward = goal.reward({'state': self.state},actions)
                self.assertAlmostEqual(float(count),reward,9)

    def createMiscoordinatedGoal(self):
        goal = PWLGoal()
        goal.keys.append(self.tiger)
        condition = ActionCondition()
        condition.addCondition('OpenLeft')
        condition.addCondition('OpenRight')
        goal.addDependency(condition,
                           ProbabilityTree(KeyedVector({keyConstant: -1.})))
        condition = ActionCondition()
        condition.addCondition('OpenRight')
        condition.addCondition('Listen')
        goal.addDependency(condition,
                           ProbabilityTree(KeyedVector({self.tiger: -1.1,
                                                        keyConstant: 0.1})))
        condition = ActionCondition()
        condition.addCondition('Listen')
        condition.addCondition('OpenLeft')
        goal.addDependency(condition,
                           ProbabilityTree(KeyedVector({self.tiger: 1.1,
                                                        keyConstant: -1.})))
        return goal

    def testMiscoordinatedGoal(self):
        """Goal that triggers when a player opens a door single-handedly
        """
        goal = self.createMiscoordinatedGoal()
        for actions in self.joints:
            left = filter(lambda a: a[0]['type'] == 'OpenLeft',
                          actions.values())
            right = filter(lambda a: a[0]['type'] == 'OpenRight',
                           actions.values())
            rewardL = goal.reward({'state': self.left},actions)
            rewardR = goal.reward({'state': self.right},actions)
            rewardB = goal.reward({'state': self.state},actions)
            if len(left) == 1:
                if len(right) == 1:
                    # OpenLeft, OpenRight
                    self.assertAlmostEqual(rewardL,-1.,10)
                    self.assertAlmostEqual(rewardR,-1.,10)
                    self.assertEqual(len(rewardB),1)
                    self.assertAlmostEqual(rewardB.domain()[0],-1.,10)
                    self.assertAlmostEqual(rewardB.values()[0],1.,10)
                else:
                    # OpenLeft,Listen
                    self.assertAlmostEqual(rewardL,-1.,10)
                    self.assertAlmostEqual(rewardR,.1,10)
                    self.assertEqual(len(rewardB),2)
                    values = rewardB.domain()
                    values.sort()
                    self.assertAlmostEqual(values[0],-1.,10)
                    self.assertAlmostEqual(values[1],0.1,10)
                    self.assertAlmostEqual(rewardB.values()[0],0.5,10)
                    self.assertAlmostEqual(rewardB.values()[1],0.5,10)
            elif len(right) == 1:
                # OpenRight,Listen
                self.assertAlmostEqual(rewardL,0.1,10)
                self.assertAlmostEqual(rewardR,-1.,10)
                self.assertEqual(len(rewardB),2)
                values = rewardB.domain()
                values.sort()
                self.assertAlmostEqual(values[0],-1.,10)
                self.assertAlmostEqual(values[1],0.1,10)
                self.assertAlmostEqual(rewardB.values()[0],0.5,10)
                self.assertAlmostEqual(rewardB.values()[1],0.5,10)
            else:
                # Something irrelevant
                self.assertAlmostEqual(rewardL,0.,10)
                self.assertAlmostEqual(rewardR,0.,10)
                self.assertAlmostEqual(rewardB,0.,10)

    def createCoordinatedGoal(self,side):
        goal = PWLGoal()
        goal.keys.append(self.tiger)
        condition = ActionCondition(only=True)
        if side > 0.5:
            verb = 'OpenRight'
        else:
            verb = 'OpenLeft'
        condition.addCondition(verb)
        if side > 0.5:
            tree= ProbabilityTree(KeyedVector({self.tiger: -0.7,
                                               keyConstant: 0.2}))
        else:
            tree= ProbabilityTree(KeyedVector({self.tiger: 0.7,
                                               keyConstant: -0.5}))
        goal.addDependency(condition,tree)
        return goal

    def testCoordinatedGoal(self):
        """Goal that triggers when both players choose the same door
        """
        # Test opening left door
        goal = self.createCoordinatedGoal(0.)
        for actions in self.joints:
            rewardL = goal.reward({'state': self.left},actions)
            rewardR = goal.reward({'state': self.right},actions)
            rewardB = goal.reward({'state': self.state},actions)
            if len(actions) == len(filter(lambda a: a[0]['type'] == 'OpenLeft',
                                          actions.values())):
                self.assertAlmostEqual(rewardL,-0.5,10)
                self.assertAlmostEqual(rewardR,0.2,10)
                self.assertEqual(len(rewardB),2)
                self.assertAlmostEqual(rewardB.values()[0],0.5,10)
                self.assertAlmostEqual(rewardB.values()[1],0.5,10)
                values = rewardB.domain()
                values.sort()
                self.assertAlmostEqual(values[0],-0.5,10)
                self.assertAlmostEqual(values[1],0.2,10)
            else:
                self.assertAlmostEqual(rewardL,0.,10)
                self.assertAlmostEqual(rewardR,0.,10)
                self.assertAlmostEqual(rewardB,0.,10)
        # Test opening right door
        goal = self.createCoordinatedGoal(1.)
        for actions in self.joints:
            rewardL = goal.reward({'state': self.left},actions)
            rewardR = goal.reward({'state': self.right},actions)
            rewardB = goal.reward({'state': self.state},actions)
            if len(actions) == len(filter(lambda a: a[0]['type'] == 'OpenRight',
                                          actions.values())):
                self.assertAlmostEqual(rewardL,0.2,10)
                self.assertAlmostEqual(rewardR,-0.5,10)
                self.assertEqual(len(rewardB),2)
                self.assertAlmostEqual(rewardB.values()[0],0.5,10)
                self.assertAlmostEqual(rewardB.values()[1],0.5,10)
                values = rewardB.domain()
                values.sort()
                self.assertAlmostEqual(values[0],-0.5,10)
                self.assertAlmostEqual(values[1],0.2,10)
            else:
                self.assertAlmostEqual(rewardL,0.,10)
                self.assertAlmostEqual(rewardR,0.,10)
                self.assertAlmostEqual(rewardB,0.,10)
        
if __name__ == '__main__':
    unittest.main()
