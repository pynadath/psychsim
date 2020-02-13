# coding=utf-8
import time
import random
from psychsim_agents.helper_functions import *
from psychsim.world import *
from psychsim.reward import *
from vprof import runner

# parameters
NUM_TIME_STEPS = 4
NUM_AGENTS = 2  # seems to have an exponential effect
HORIZON = 3  # seems to have a polynomial effect
NUM_ACTIONS_PER_AGENT = 3  # seems to have a polynomial effect
NUM_FEATURES_PER_AGENT = 30  # seems to have a linear effect
NUM_FEATURES_ACTION = 10  # the lower the higher the number of trees per action and dependencies (does not have much effect)
MAX_FEATURE_VALUE = 10

MODEL_NAME = 'my_model'
PARALLEL = False
RUN_PROFILER = False


def run():
    global world
    setup()

    print '===================================='
    step = None
    start_time = time.time()
    total_time = 0
    for i in range(0, NUM_TIME_STEPS):
        print 'Step ' + str(i) + '...'
        start_clock = time.clock()
        step = world.step()
        step_time = time.clock() - start_clock
        total_time += step_time
        print 'Clock time: ' + str(step_time) + 's'
        world.printState()
        print '____________________________________'

    print 'Total time: ' + str(time.time() - start_time) + 's'
    print 'Av. time: ' + str(total_time / NUM_TIME_STEPS) + 's'
    print '____________________________________'
    world.explain(step, level=2)


def setup():
    global world
    random.seed(0)
    # create world and add agents
    world = World()
    world.memory = False
    world.parallel = PARALLEL
    agents = []
    for ag in range(NUM_AGENTS):
        agent = Agent('Agent' + str(ag))
        world.addAgent(agent)
        agents.append(agent)

        # set agent's params
        agent.setAttribute('discount', 1)
        agent.setHorizon(HORIZON)

        # add features
        features = []
        for f in range(NUM_FEATURES_PER_AGENT):
            feat = world.defineState(agent.name, 'Feature' + str(f), int, lo=0, hi=1000)
            world.setFeature(feat, random.randint(0, MAX_FEATURE_VALUE))
            features.append(feat)

        # set random reward function
        agent.setReward(maximizeFeature(features[0]), 1)

        # add mental copy of true model and set it static (we do not have beliefs in the models)
        agent.addModel(MODEL_NAME)
        agent.setAttribute("static", True, MODEL_NAME)

        # add actions
        for ac in range(NUM_ACTIONS_PER_AGENT):
            action = agent.addAction({'verb': '', 'action': 'Action' + str(ac)})
            i = ac
            while i + NUM_FEATURES_ACTION < NUM_FEATURES_PER_AGENT:

                weights = {}
                for j in range(NUM_FEATURES_ACTION):
                    weights[features[i + j + 1]] = 1
                tree = makeTree(multiSetMatrix(features[i], weights))
                world.setDynamics(features[i], action, tree)

                world.addDependency(features[i], features[i + NUM_FEATURES_ACTION])

                i += NUM_FEATURES_ACTION

        # test belief update:
        # - add the True model to the world
        # - set a belief in one feature to the actual initial value (should not change outcomes)
        world.setModel(agent.name, Distribution({True: 1.0}))
        agent.setBelief(features[0], world.getValue(features[0]))

    # define order
    world.setOrder([set(agents)])

    # set mental model of each agent in all other agents
    for i in range(NUM_AGENTS):
        for j in range(i + 1, NUM_AGENTS):
            world.setMentalModel(agents[i].name, agents[j].name, {MODEL_NAME: 1})
            world.setMentalModel(agents[j].name, agents[i].name, {MODEL_NAME: 1})


if __name__ == '__main__':

    if RUN_PROFILER:
        # NOTE: run 'vprof -r' in command line first to create a listener
        # runner.run(run, 'cmhp', host='localhost', port=8000)
        runner.run(run, 'c', host='localhost', port=8000)
    else:
        run()
