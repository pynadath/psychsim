from action import Action
from agent import Agent
from pwl import makeTree, trueRow, thresholdRow, approachMatrix, addFeatureMatrix, setTrueMatrix, greaterThanRow, \
    noChangeMatrix, setToConstantMatrix, incrementMatrix, setFalseMatrix
from reward import maximizeFeature
from world import World, stateKey


# Main scenario class
class MoCA:

    def __init__(self, turnOrder):

        self.maxRounds = 15
        self.world = World()
        minMax = {'min': -10, 'max': 10}

        # Agents

        greta = Agent('Greta')
        child = Agent('Child')
        agents = [greta, child]
        self.world.addAgent(greta)
        self.world.addAgent(child)

        # World state

        # Child

        self.world.defineState(child.name, 'Liking', float, lo=minMax['min'], hi=minMax['max'],
                               description='Child liking level')
        child.setState('Liking', 0.8)

        self.world.defineState(child.name, 'KnowledgeIncrement', float, lo=minMax['min'], hi=minMax['max'],
                               description='How much a working unit improve the child knowledge')
        child.setState('KnowledgeIncrement', 0.2)
        self.world.defineState(child.name, 'TotalKnowledge', float, lo=minMax['min'], hi=minMax['max'],
                               description='Child total knowledge value')
        child.setState('TotalKnowledge', 0)
        self.world.defineState(child.name, 'FunIncrement', float, lo=minMax['min'], hi=minMax['max'],
                               description='How much a working unit improve the child fun')
        child.setState('FunIncrement', 0.0)
        self.world.defineState(child.name, 'TotalFun', float, lo=minMax['min'], hi=minMax['max'],
                               description='Child fun value')
        child.setState('TotalFun', 0)

        self.world.defineState(child.name, 'BestInClass', bool, description='Is the child the best in class')
        child.setState('BestInClass', False)
        self.world.defineState(child.name, 'BestInClassThreshold', float, lo=minMax['min'], hi=minMax['max'],
                               description='Threshold of knowledge needed to be the best in class')
        child.setState('BestInClassThreshold', 10.0)

        self.world.defineState(child.name, 'ForbidToParty', bool, description='Is the child forbid to party')
        child.setState('ForbidToParty', False)
        self.world.defineState(child.name, 'AllowedToPlay', bool, description='Is the child allowed to play')
        child.setState('AllowedToPlay', True)

        # Teacher

        self.world.defineState(greta.name, 'Power', float, lo=minMax['min'], hi=minMax['max'],
                               description='Teacher Power value')
        greta.setState('Power', 2.0)

        # World

        self.world.defineState(None, 'round', int, lo=minMax['min'], hi=minMax['max'], description='round number')
        self.world.setState(None, 'round', 0)

        # Actions

        # Greta negociating actions
        greta.addAction({'verb': 'Do nothing'})
        greta.addAction({'verb': 'ExplainWork'})
        greta.addAction({'verb': 'MakeWorkFun'})
        greta.addAction({'verb': 'CanBeBestInClass'})
        greta.addAction({'verb': 'ForbidToParty'})
        greta.addAction({'verb': 'ForceToWork'})

        # Greta enhancing relations
        greta.addAction({'verb': 'EnhanceLiking'})
        greta.addAction({'verb': 'EnhancePower'})

        # Greta maintaning engagement actions
        ##                greta.addAction({'verb': 'ImproveDifficulty'})
        ##		greta.addAction({'verb': 'Encourage'})

        # Child actions

        tmp = child.addAction({'verb': 'Do nothing'})
        child.setLegal(tmp, makeTree({'if': trueRow(stateKey(child.name, 'AllowedToPlay')),
                                      False: False,
                                      True: True}))
        child.addAction({'verb': 'Work'})
        tmp = child.addAction({'verb': 'Play'})
        child.setLegal(tmp, makeTree({'if': trueRow(stateKey(child.name, 'AllowedToPlay')),
                                      False: False,
                                      True: True}))

        # Parameters
        greta.setHorizon(3)
        child.setHorizon(3)

        # Levels of belief
        greta.setRecursiveLevel(3)
        child.setRecursiveLevel(3)
        turnOrder = ['Greta', 'Child']
        self.world.setOrder(turnOrder)

        self.world.addTermination(
            makeTree({'if': thresholdRow(stateKey(None, 'round'), self.maxRounds), True: True, False: False}))

        # Dynamics of actions

        # Child Actions

        # Playing will improve the child total level of fun. If the child plays two times in a row, the effect is lowered.
        atom = Action({'subject': child.name, 'verb': 'Play'})
        change = stateKey(child.name, 'TotalFun')
        tree = makeTree(approachMatrix(change, 0.5, 3))
        self.world.setDynamics(change, atom, tree)

        # Working will improve the child knowledge. It will also increase or decrease his fun according to his beliefs.
        atom = Action({'subject': child.name, 'verb': 'Work'})
        change = stateKey(child.name, 'TotalKnowledge')
        tree = makeTree({'if': trueRow(stateKey(child.name, 'AllowedToPlay')),
                         True: addFeatureMatrix(change, stateKey(child.name, 'KnowledgeIncrement'), 1.0),
                         False: addFeatureMatrix(change, stateKey(child.name, 'KnowledgeIncrement'), 0.5)})
        self.world.setDynamics(change, atom, tree)

        change = stateKey(child.name, 'TotalFun')
        tree = makeTree(addFeatureMatrix(stateKey(child.name, 'TotalFun'), stateKey(child.name, 'FunIncrement'), 1.0))
        self.world.setDynamics(change, atom, tree)

        change = stateKey(child.name, 'AllowedToPlay')
        tree = makeTree(setTrueMatrix(change))
        self.world.setDynamics(change, atom, tree)

        # The child will be the best in class if he reaches a particular treshold
        change = stateKey(child.name, 'BestInClass')
        tree = makeTree(
            {'if': greaterThanRow(stateKey(child.name, 'TotalKnowledge'), stateKey(child.name, 'BestInClassThreshold')),
             True: setTrueMatrix(stateKey(child.name, 'BestInClass')),
             False: noChangeMatrix(stateKey(child.name, 'BestInClass'))})
        self.world.setDynamics(change, atom, tree)

        # Teacher Actions

        # Explaining why to work will change the child's beliefs about the knowledge increment if he trust him
        atom = Action({'subject': greta.name, 'verb': 'ExplainWork'})
        change = stateKey(child.name, 'KnowledgeIncrement')
        tree = makeTree({'if': thresholdRow(stateKey(child.name, 'Liking'), 1.0),
                         True: setToConstantMatrix(change, 0.8),
                         False: noChangeMatrix(change)})
        self.world.setDynamics(change, atom, tree)

        # Making work fun will improve the child level of funniness and his motivation
        atom = Action({'subject': greta.name, 'verb': 'MakeWorkFun'})
        change = stateKey(child.name, 'FunIncrement')
        tree = makeTree({'if': thresholdRow(stateKey(child.name, 'Liking'), 1.0),
                         True: approachMatrix(change, 0.3, 1),
                         False: noChangeMatrix(change)})
        self.world.setDynamics(change, atom, tree)

        # Explaining the kid that he can be the best in class will lower his treshold
        atom = Action({'subject': greta.name, 'verb': 'CanBeBestInClass'})
        change = stateKey(child.name, 'BestInClassThreshold')
        tree = makeTree({'if': thresholdRow(stateKey(child.name, 'Liking'), 1.0),
                         True: setToConstantMatrix(change, 1.5),
                         False: noChangeMatrix(change)})
        self.world.setDynamics(change, atom, tree)

        # The teacher can forbid the child to party
        atom = Action({'subject': greta.name, 'verb': 'ForbidToParty'})
        change = stateKey(child.name, 'ForbidToParty')
        tree = makeTree(setTrueMatrix(change))
        self.world.setDynamics(change, atom, tree)

        change = stateKey(child.name, 'Liking')
        tree = makeTree(incrementMatrix(stateKey(child.name, 'Liking'), -1.0))
        self.world.setDynamics(change, atom, tree)

        # Forcing the child to work will lower the liking
        atom = Action({'subject': greta.name, 'verb': 'ForceToWork'})
        change = stateKey(child.name, 'AllowedToPlay')
        tree = makeTree(setFalseMatrix(change))
        self.world.setDynamics(change, atom, tree)

        change = stateKey(child.name, 'Liking')
        tree = makeTree(incrementMatrix(stateKey(child.name, 'Liking'), -1.0))
        self.world.setDynamics(change, atom, tree)

        # Enhance the child liking
        atom = Action({'subject': greta.name, 'verb': 'EnhanceLiking'})
        change = stateKey(child.name, 'Liking')
        tree = makeTree(approachMatrix(change, 0.5, 3.0))
        self.world.setDynamics(change, atom, tree)

        # Enhance the teacher power
        atom = Action({'subject': greta.name, 'verb': 'EnhancePower'})
        change = stateKey(greta.name, 'Power')
        tree = makeTree(approachMatrix(change, 0.5, 3.0))
        self.world.setDynamics(change, atom, tree)

        child.addModel('DumbChildWorkUseless0', R={}, rationality=10, horizon=1)
        child.addModel('DumbChildWorkUseless1', R={}, rationality=10, horizon=2)
        child.addModel('DumbChildWorkUseless2', R={}, rationality=10, horizon=3)

        greta.addModel('SmartGretaCaresLiking0', R={}, rationality=10, horizon=1)
        greta.addModel('SmartGretaCaresLiking1', R={}, rationality=10, horizon=2)
        greta.addModel('SmartGretaCaresLiking2', R={}, rationality=10, horizon=3)

    ##                child.setReward(maximizeFeature(stateKey(child.name,'BestInClass')),0.25, child.models.keys[True])
    ##                child.setReward(maximizeFeature(stateKey(child.name,'TotalFun')),0.75, child.models.keys[True])

    ##for agent in self.world.agents.values()

    def modeltest(self, trueModels, childBeliefAboutGreta, gretaBeliefAboutChild, strongerBelief):

        greta = self.world.agents['Greta']
        child = self.world.agents['Child']

        for agent in self.world.agents.values():
            self.world.setModel(agent.name, trueModels[agent.name])
            for model in agent.models.keys():
                if model is True:
                    name = trueModels[agent.name]
                else:
                    name = model
                if 'DumbChildWorkUseless' in name:
                    agent.setReward(maximizeFeature(stateKey(agent.name, 'BestInClass')), 0.25, model)
                    agent.setReward(maximizeFeature(stateKey(agent.name, 'TotalFun')), 0.75, model)
                elif 'DumbChildWorkImportant' in name:
                    agent.setReward(maximizeFeature(stateKey(agent.name, 'BestInClass')), 0.75, model)
                    agent.setReward(maximizeFeature(stateKey(agent.name, 'TotalFun')), 0.25, model)
                elif 'SmartChildWorkUseless' in name:
                    agent.setReward(maximizeFeature(stateKey(agent.name, 'BestInClass')), 0.25, model)
                    agent.setReward(maximizeFeature(stateKey(agent.name, 'TotalFun')), 0.75, model)
                elif 'SmartChildWorkImportant' in name:
                    agent.setReward(maximizeFeature(stateKey(agent.name, 'BestInClass')), 0.75, model)
                    agent.setReward(maximizeFeature(stateKey(agent.name, 'TotalFun')), 0.25, model)
                elif 'SmartGretaCaresLiking' in name:
                    agent.setReward(maximizeFeature(stateKey(child.name, 'TotalKnowledge')), 1, model)
                    agent.setReward(maximizeFeature(stateKey(child.name, 'Liking')), 0.3, model)
                elif 'SmartGretaCaresNothing' in name:
                    agent.setReward(maximizeFeature(stateKey(child.name, 'TotalKnowledge')), 1, model)

        belief = {'SmartGretaCaresLiking1': 1.0}
        belief[childBeliefAboutGreta + '1'] = 1.0
        self.world.setMentalModel('Child', 'Greta', belief, 'DumbChildWorkUseless2')

        belief = {'SmartGretaCaresLiking0': 1.0}
        belief[childBeliefAboutGreta + '0'] = 1.0
        self.world.setMentalModel('Child', 'Greta', belief, 'DumbChildWorkUseless1')

        belief = {'DumbChildWorkUseless1': 1.0}
        belief[gretaBeliefAboutChild + '1'] = 1.0
        self.world.setMentalModel('Greta', 'Child', belief, 'SmartGretaCaresLiking2')

        belief = {'DumbChildWorkUseless0': 1.0}
        belief[gretaBeliefAboutChild + '0'] = 1.0
        self.world.setMentalModel('Greta', 'Child', belief, 'SmartGretaCaresLiking1')

    def runit(self, Msg):

        print Msg

        for t in range(self.maxRounds + 1):
            # self.world.agents['Child'].printModel('SmartGretaCaresNothing2')
            self.world.explain(self.world.step(), level=1)
            # self.world.setModel('Child',True)
            # self.world.setModel('Greta',True)
            self.world.printState()

            self.world.state[None].select()

            if self.world.terminated():
                break


trueModels = {'Child': 'DumbChildWorkUseless2', 'Greta': 'SmartGretaCaresLiking2'}
turnOrder = ['Greta', 'Child']
MoCATest = MoCA(turnOrder)
MoCATest.modeltest(trueModels, 'SmartGretaCaresLiking', 'DumbChildWorkUseless', 0.70)
MoCATest.runit("Some model of the child")

# MoCATest = MoCA(turnOrder)
# MoCATest.modeltest(trueModels,'WorkImportant','WorkImportant', 0.75)
# MoCATest.runit("Wrong Model of the child")
