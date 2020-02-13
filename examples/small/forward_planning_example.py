# coding=utf-8
from agent import Agent
from world import World
from helper_functions import multiSetMatrix, get_decision_info, explain_decisions
from pwl import makeTree, setToFeatureMatrix
from reward import achieveFeatureValue, CONSTANT

# parameters
MAX_HORIZON = 3
DISCOUNT = 0.9

# create world and add agent
world = World()
agent = Agent('Agent')
world.addAgent(agent)
world.setOrder([agent])

# set discount
agent.setAttribute('discount', DISCOUNT)

# add position variable
pos = world.defineState(agent.name, 'position', int, lo=-100, hi=100)

# define agents' actions (stay, left and right)
action = agent.addAction({'verb': 'move', 'action': 'anywhere'})
tree = makeTree(setToFeatureMatrix(pos, pos))
world.setDynamics(pos, action, tree)
action = agent.addAction({'verb': 'move', 'action': 'left'})
tree = makeTree(multiSetMatrix(pos, {pos: 1, CONSTANT: -1}))
world.setDynamics(pos, action, tree)
action = agent.addAction({'verb': 'move', 'action': 'right'})
tree = makeTree(multiSetMatrix(pos, {pos: 1, CONSTANT: 1}))
world.setDynamics(pos, action, tree)

# define rewards (left always adds 1, right depends on position)
agent.setReward(achieveFeatureValue(pos, -1), 1)
agent.setReward(achieveFeatureValue(pos, -2), 2)
agent.setReward(achieveFeatureValue(pos, -3), 3)
agent.setReward(achieveFeatureValue(pos, 2), 3)
agent.setReward(achieveFeatureValue(pos, 3), 100)

for i in range(MAX_HORIZON + 1):
    print '===================================='
    print 'Horizon: ' + str(i)

    # reset
    world.setFeature(pos, 0)
    agent.setHorizon(i)

    # single decision: left or right?
    step = world.step()
    # print step
    world.printState()
    world.explain(step, level=3)

    print('\n')
    decision_infos = get_decision_info(step, agent.name)
    explain_decisions(agent.name, decision_infos)
