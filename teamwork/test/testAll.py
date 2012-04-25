"""
Test case that also illustrates basic operation of the PsychSim API
"""
import unittest

# keys for labeling state features
from teamwork.math.Keys import StateKey,ObservationKey,keyConstant
# dynamics vectors
from teamwork.math.KeyedVector import KeyedVector,ClassRow,IdentityRow,\
    ThresholdRow,RelationshipRow,DifferenceRow
# dynamics matrices
from teamwork.math.KeyedMatrix import IdentityMatrix,DiminishMatrix,\
    IncrementMatrix,ScaleMatrix,SetToConstantMatrix,SetToFeatureMatrix,\
    SetToFeaturePlusMatrix,SetToDiffMatrix
# dynamics hyperplanes
from teamwork.math.KeyedTree import KeyedPlane,makePlane,makeIdentityPlane
# probability distributions
from teamwork.math.probability import Distribution
# dynamics probabilistic trees
from teamwork.math.ProbabilityTree import ProbabilityTree
# generic class of entity
from teamwork.agent.Generic import GenericModel
# hierarchy of generic classes
from teamwork.multiagent.GenericSociety import GenericSociety
# instantiated scenario
from teamwork.multiagent.PsychAgents import PsychAgents
# possible decisions of entities and left-hand side for rule
from teamwork.action.PsychActions import Action,ActionCondition
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

        #####################
        # Hyperplane examples
        #####################
        examples = {
            # if my welfare is positive (i.e., > 0)
            'threshold': {'class': ThresholdRow,
                          'keys': [{'entity':'self','feature':'welfare'}],
                          'threshold': 0.0},
            # if I am object of the action (i.e., person being picked on)
            # boolean test, so threshold of 0.5 is used by convention
            'identity': {'class': IdentityRow,
                         'keys': [{'entity': 'object','relationship':'equals'}],
                         'threshold': 0.5},
            # if the actor is a teacher (boolean test)
            'class': {'class': ClassRow,
                      'keys': [{'entity':'actor','value':teacher.name}],
                      'threshold': 0.5},
            # if the object is my victim (boolean test)
            'relation': {'class': RelationshipRow,
                         'keys': [{'feature':'victim','relatee':'object'}],
                         'threshold': 0.5},
            # if my welfare is significantly greater than my victim's
            'diff': {'class': DifferenceRow,
                     'keys': [{'entity': 'self','feature':'welfare'},
                              {'entity':'victim','feature':'welfare'}],
                     'threshold': 0.3}
            }
        # Iterate through examples using "makePlane" helper function
        for label,args in examples.items():
            plane = makePlane(args['class'],args['keys'],args['threshold'])
        # Make a hyperplane without using any subclass helper
        # if my welfare is positive (in raw vector form: 1.0*my welfare > 0.)
        key = StateKey({'entity': 'self','feature': 'welfare'})
        plane = KeyedPlane(KeyedVector({key: 1.}),0.)
        # Make a probabilistic branch
        # 75% chance of diminish, 25% of no change
        plane = Distribution({diminish: .75, identity: .25})
        ##########################
        # /Hyperplane examples
        ##########################

        # if I am object (i.e., person being picked on), using helper function
        plane = makeIdentityPlane('object')
        # If I am object, then diminish, else identity
        tree.branch(plane,falseTree=identity,trueTree=diminish)

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
        # Effect of "punish class" on "welfare"
        student.dynamics['welfare'][str(condition)] = {'condition': condition,
                                                       'tree': tree}
        # Leave welfare unchanged
        identity = ProbabilityTree(IdentityMatrix('welfare'))
        # Move "welfare" 20% closer to -1
        diminish = ProbabilityTree(DiminishMatrix('welfare',value=-0.2))
        # if I am a student (i.e., class member being punished), then diminish, else identity
        plane = KeyedPlane(ClassRow(keys=[{'entity':'self','value':student.name}]),0.5)
        tree.branch(plane,falseTree=identity,trueTree=diminish)

        ##########################
        # Matrix examples
        ##########################
        # Leave feature unchanged
        # w' = w
        matrix = IdentityMatrix('welfare')
        # Change by constant amount
        # w' = w - 0.1
        matrix = IncrementMatrix('welfare',value=-0.1)
        # Change by percentage of other feature
        # w' = w - 25% of actor's welfare
        matrix = ScaleMatrix('welfare',StateKey({'entity': 'actor',
                                                 'feature': 'welfare'}),-0.25)
        # Approach 1/-1 by a percentage of distance
        # w' = w + 20% of (1-w)
        matrix = DiminishMatrix('welfare',value=0.2)
        # Set to a fixed value
        # w' = 1
        matrix = SetToConstantMatrix('welfare',value=1.)
        # Set to a percentage of some other feature's value
        # w' = actor's welfare
        matrix = SetToFeatureMatrix('welfare',StateKey({'entity':'actor',
                                                        'feature':'welfare'}),1.)
        # Set to a percentage of some other feature's value plus fixed delta
        # w' = actor's welfare - 0.1
        matrix = SetToFeaturePlusMatrix('welfare',
                                        [StateKey({'entity':'actor',
                                                   'feature':'welfare'}),
                                         keyConstant],value=[1.,-0.1])
        # Set to a weighted difference of two features' values
        # w' = actor's welfare - object's welfare
        matrix = SetToDiffMatrix('welfare',[StateKey({'entity':'actor',
                                                      'feature':'welfare'}),
                                            StateKey({'entity':'object',
                                                      'feature':'welfare'})],
                                 value=[1.,1.])
        ##########################
        # /Matrix examples
        ##########################

        # Create goal for students to improve their own welfare
        goal = maxGoal(StateKey({'entity':'self','feature':'welfare'}))
        student.setGoalWeight(goal,1.,False)
        # Create goal for students to decrease welfare of their victims
        goal = minGoal(StateKey({'entity':'victim','feature':'welfare'}))
        student.setGoalWeight(goal,1.,False)
        # Create goals for teachers to improve their students' welfare
        goal = maxGoal(StateKey({'entity':'Student','feature':'welfare'}))
        teacher.setGoalWeight(goal,1.,False)

        # Observation if the teacher hears laughter but nothing else
        key = ObservationKey({'type': 'laughter'})
        teacher.omega[key] = True

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
        # Verify observations
        self.assertEqual(len(scenario['Bill'].omega),2)
        self.assertEqual(len(scenario['Otto'].omega),2)
        self.assertEqual(len(scenario['Victor'].omega),2)
        self.assertEqual(len(scenario['Mrs Thompson'].omega),3)

if __name__ == '__main__':
    unittest.main()
