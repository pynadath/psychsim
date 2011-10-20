from teamwork.action.PsychActions import *
import unittest

class TestActionCondition(unittest.TestCase):
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
        
    def testAddDel(self):
        condition = ActionCondition()
        # Test adding
        for index in range(len(self.verbs)):
            condition.addCondition(self.verbs[index])
            self.assertEqual(len(condition),index+1)
        # Test for no duplication
        for index in range(len(self.verbs)):
            condition.addCondition(self.verbs[index])
            self.assertEqual(len(condition),len(self.verbs))
        # Test deleting
        for index in range(len(self.verbs)):
            condition.delCondition(self.verbs[index])
            self.assertEqual(len(condition),len(self.verbs)-index-1)

    def createOLOR(self):
        """@return: test condition on "OL and OR"
        """
        condition = ActionCondition()
        condition.addCondition('OpenLeft')
        condition.addCondition('OpenRight')
        return condition

    def createListen(self):
        """
        @return: test condition on only "Listen"s
        """
        condition = ActionCondition(True)
        condition.addCondition('Listen')
        return condition


    def createListenCount(self):
        """
        @return: test condition on number of "Listen"s
        """
        condition = ActionCondition(False,True)
        condition.addCondition('Listen')
        return condition

    def verifyOLOR(self,condition):
        """
        Verifies a condition on OpenLeft+OpenRight
        """
        for joint in self.joints:
            verbs = map(lambda o: o[0]['type'],joint.values())
            if condition.match(joint):
                self.assertNotEqual(verbs[0],verbs[1])
                self.assertNotEqual(verbs[0],'Listen')
                self.assertNotEqual('Listen',verbs[1])
            else:
                self.assert_('Listen' in verbs or verbs[0] == verbs[1])

    def verifyOL(self,condition):
        """
        Verifies a condition on OpenLeft
        """
        for joint in self.joints:
            verbs = map(lambda o: o[0]['type'],joint.values())
            if condition.match(joint):
                self.assert_('OpenLeft' in verbs)
            else:
                self.assertNotEqual(verbs[0],'OpenLeft')
                self.assertNotEqual(verbs[1],'OpenLeft')

    def verifyListen(self,condition):
        """
        Verifies a condition on only Listen
        """
        for joint in self.joints:
            verbs = map(lambda o: o[0]['type'],joint.values())
            if condition.match(joint):
                self.assertEqual(verbs[0],'Listen')
                self.assertEqual(verbs[1],'Listen')
            else:
                self.assert_(verbs[0] != 'Listen' or verbs[1] != 'Listen')

    def testMatch(self):
        # Test condition on "OL" + "OR"
        condition = self.createOLOR()
        self.verifyOLOR(condition)
        # Test condition on "OL"
        condition.delCondition('OpenRight')
        self.verifyOL(condition)
        # Test condition on only "Listen"s
        condition = self.createListen()
        self.verifyListen(condition)

    def testCount(self):
        # Test condition on Listen counts
        condition = self.createListenCount()
        for joint in self.joints:
            verbs = map(lambda o: o[0]['type'],joint.values())
            self.assertEqual(verbs.count('Listen'),condition.match(joint))

    def testXML(self):
        # Test condition on "OL" + "OR"
        condition = self.createOLOR()
        doc = condition.__xml__()
        condition = ActionCondition()
        condition.parse(doc.documentElement)
        self.verifyOLOR(condition)
        # Test condition on "OL"
        condition.delCondition('OpenRight')
        doc = condition.__xml__()
        condition = ActionCondition()
        condition.parse(doc.documentElement)
        self.verifyOL(condition)
        # Test condition on only "Listen"s
        condition = self.createListen()
        doc = condition.__xml__()
        condition = ActionCondition()
        condition.parse(doc.documentElement)
        self.verifyListen(condition)
        
if __name__ == '__main__':
    unittest.main()
