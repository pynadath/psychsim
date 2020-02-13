# coding=utf-8
from psychsim_agents.helper_functions import *
from psychsim.agent import Agent
from psychsim.world import World
from psychsim.reward import *

# parameters
HORIZON = 2
DISCOUNT = 0.9
NUM_AGENTS = 3
MODEL_NAME = 'my_model'

# create world and add agents
world = World()
agents = []
for i in range(NUM_AGENTS):
    # create agent
    agent = Agent('Agent {}'.format(i + 1))
    world.addAgent(agent)
    agents.append(agent)

    # set agent params
    agent.setAttribute('discount', DISCOUNT)
    agent.setHorizon(HORIZON)
    agent.setRecursiveLevel(1)

    # add position variable
    pos = world.defineState(agent.name, 'position', int, lo=-100, hi=100)
    world.setFeature(pos, 0)

    # define agents' actions: stay (for ag 0,1,2), left (for ag 1,2)  and right (for ag 2 only)
    action = agent.addAction({'verb': 'move', 'action': 'anywhere'})
    tree = makeTree(setToFeatureMatrix(pos, pos))
    world.setDynamics(pos, action, tree)

    if i > 0:
        action = agent.addAction({'verb': 'move', 'action': 'left'})
        tree = makeTree(multiSetMatrix(pos, {pos: 1, CONSTANT: -1}))
        world.setDynamics(pos, action, tree)

    if i > 1:
        action = agent.addAction({'verb': 'move', 'action': 'right'})
        tree = makeTree(multiSetMatrix(pos, {pos: 1, CONSTANT: 1}))
        world.setDynamics(pos, action, tree)

    # define rewards (left always adds 1, right depends on position)
    agent.setReward(achieveFeatureValue(pos, -1), 1)
    agent.setReward(achieveFeatureValue(pos, -2), 2)
    agent.setReward(achieveFeatureValue(pos, 1), 1)
    agent.setReward(achieveFeatureValue(pos, 2), 100)

    # add mental copy of true model and set it static (we do not have beliefs in the models)
    agent.addModel(MODEL_NAME)
    agent.setAttribute("static", True, MODEL_NAME)

# define order
world.setOrder([set(agents)])

# set mental model of each agent in all other agents
for i in range(NUM_AGENTS):
    for j in range(i + 1, NUM_AGENTS):
        world.setMentalModel(agents[i].name, agents[j].name, {MODEL_NAME: 1})
        world.setMentalModel(agents[j].name, agents[i].name, {MODEL_NAME: 1})

# single decision for each agent: left, right or stay put?
step = world.step()
world.explain(step, level=3)

print('\n')
for i in range(NUM_AGENTS):
    decision_infos = get_decision_info(step, agents[i].name)
    explain_decisions(agents[i].name, decision_infos)
