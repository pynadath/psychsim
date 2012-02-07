"""
Test case that also illustrates basic operation of the PsychSim API
"""
import unittest

# keys for labeling state features
from teamwork.math.Keys import StateKey
# dynamics vectors
from teamwork.math.KeyedVector import ClassRow
# dynamics matrices
from teamwork.math.KeyedMatrix import IdentityMatrix,DiminishMatrix
# dynamics hyperplanes
from teamwork.math.KeyedTree import KeyedPlane,makeIdentityPlane
# generic class of entity
from teamwork.agent.Generic import GenericModel
# hierarchy of generic classes
from teamwork.multiagent.GenericSociety import GenericSociety
# instantiated scenario
from teamwork.multiagent.PsychAgents import PsychAgents
# possible decisions of entities and left-hand side for rule
from teamwork.action.PsychActions import Action,ActionCondition
# PWL trees
from teamwork.math.ProbabilityTree import ProbabilityTree
# max/min goals for agents
from teamwork.reward.goal import maxGoal,minGoal

class TestPsychSim(unittest.TestCase):

    def testSociety(self):
        """
        Test the creation of classroom models, instantiation of scenario,
        and simulation of scenario
        """
        #################
        # Create models
        #################
        # Create a hierarchy of generic classes
        society = GenericSociety()
        # Create a base class
        entity = GenericModel('Entity')
        # Insert class into hierarchy
        society.addMember(entity)
        # Create a subclass for students
        student = GenericModel('Student')
        # Add parent
        student.parentModels.append(entity.name)
        # Insert subclass into hierarchy
        society.addMember(student)
        # Create a subclass for teacher
        teacher = GenericModel('Teacher')
        # Add parent
        teacher.parentModels.append(entity.name)
        # Insert subclass into hierarchy
        society.addMember(teacher)

        # Add possible static relationship
        student.relationships['victim'] = [student.name]

        # Add state features
        student.setState('welfare',0.3)

        # Create NOP action
        doNothing = Action({'actor':'self','type': 'do nothing'})
        entity.actions.directAdd([doNothing])

        # Create "pick on" action
        pickOn = Action({'actor':'self','type': 'pick on','object':student.name})
        student.actions.directAdd([pickOn])
        # Create dynamics of "pick on"
        tree = ProbabilityTree()
        condition = ActionCondition()
        condition.addCondition(pickOn['type'])
        # Effect of "pick on" on "welfare"
        student.dynamics['welfare'] = {str(condition): {'condition': condition,
                                                        'tree': tree}}
        # Leave welfare unchanged
        identity = ProbabilityTree(IdentityMatrix('welfare'))
        # Move "welfare" 20% closer to -1
        diminish = ProbabilityTree(DiminishMatrix('welfare',value=-0.2))
        # if I am object (i.e., person being picked on), then diminish, else identity
        tree.branch(makeIdentityPlane('object'),
                    falseTree=identity,trueTree=diminish)

        # Create "punish" action
        punish = Action({'actor':'self','type': 'punish','object':student.name})
        teacher.actions.directAdd([punish])
        # Create dynamics of "punish"
        tree = ProbabilityTree()
        condition = ActionCondition()
        condition.addCondition(punish['type'])
        # Effect of "punish" on "welfare"
        student.dynamics['welfare'][str(condition)] = {'condition': condition,
                                                       'tree': tree}
        # Leave welfare unchanged
        identity = ProbabilityTree(IdentityMatrix('welfare'))
        # Move "welfare" 20% closer to -1
        diminish = ProbabilityTree(DiminishMatrix('welfare',value=-0.2))
        # if I am object (i.e., person being punished), then diminish, else identity
        tree.branch(makeIdentityPlane('object'),
                    falseTree=identity,trueTree=diminish)

        # Create "punish class" action
        punishAll = Action({'actor':'self','type': 'punish class'})
        teacher.actions.directAdd([punishAll])
        # Create dynamics of "punish class"
        tree = ProbabilityTree()
        condition = ActionCondition()
        condition.addCondition(punishAll['type'])
        # Effect of "punish cass" on "welfare"
        student.dynamics['welfare'][str(condition)] = {'condition': condition,
                                                       'tree': tree}
        # Leave welfare unchanged
        identity = ProbabilityTree(IdentityMatrix('welfare'))
        # Move "welfare" 20% closer to -1
        diminish = ProbabilityTree(DiminishMatrix('welfare',value=-0.2))
        # if I am a student (i.e., class member being punished), then diminish, else identity
        plane = KeyedPlane(ClassRow(keys=[{'entity':'self','value':student.name}]),0.5)
        tree.branch(plane,falseTree=identity,trueTree=diminish)

        # Create goal for students to improve their own welfare
        goal = maxGoal(StateKey({'entity':'self','feature':'welfare'}))
        student.setGoalWeight(goal,1.,False)
        # Create goal for students to decrease welfare of their victims
        goal = minGoal(StateKey({'entity':'victim','feature':'welfare'}))
        student.setGoalWeight(goal,1.,False)
        # Create goals for teachers to improve their students' welfare
        goal = maxGoal(StateKey({'entity':'Student','feature':'welfare'}))
        teacher.setGoalWeight(goal,1.,False)

        #################
        # Create scenario
        #################
        scenario = society.instantiate({'Bill': student.name,
                                        'Victor': student.name,
                                        'Otto': student.name,
                                        'Mrs Thompson': teacher.name})
        scenario['Bill'].relationships['victim'] = ['Victor']
        scenario.applyDefaults()
        # Serialize turn-taking in desired order
        scenario.initializeOrder([[scenario['Bill']],[scenario['Otto']],
                                  [scenario['Mrs Thompson']]])
        print scenario['Victor'].dynamics['welfare'].keys()

        #################
        # Run scenario
        #################
        states = [scenario.state.expectation()]
        for t in range(3):
            result = scenario.microstep()
            states.append(scenario.state.expectation())
            #################
            # Verify results
            #################
            decision = result['decision']
            self.assertEqual(len(decision),1)
            actor = decision.keys()[0]
            self.assert_(scenario.has_key(actor))
            action = decision[actor]
            self.assert_(action in scenario[actor].actions.getOptions())
        
        #################
        # Verify scenario
        #################
        self.assertEqual(len(society),3)
        self.assertEqual(len(scenario),4)
        # Verify action spaces
        self.assertEqual(len(scenario['Bill'].actions.getOptions()),3)
        self.assertEqual(len(scenario['Otto'].actions.getOptions()),3)
        self.assertEqual(len(scenario['Victor'].actions.getOptions()),3)
        self.assertEqual(len(scenario['Mrs Thompson'].actions.getOptions()),5)
        # Verify goals
        self.assertEqual(len(scenario['Bill'].goals),2)
        self.assertEqual(len(scenario['Otto'].goals),1)
        self.assertEqual(len(scenario['Victor'].goals),1)
        self.assertEqual(len(scenario['Mrs Thompson'].goals),3)

if __name__ == '__main__':
    unittest.main()
