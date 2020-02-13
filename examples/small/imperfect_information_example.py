# coding=utf-8
from psychsim_agents.helper_functions import *
from psychsim.agent import Agent
from psychsim.world import World
from psychsim.reward import *

# parameters
HORIZON = 3
DISCOUNT = 1
MAX_STEPS = 3

# create world and add agent
world = World()
agent = Agent('Agent')
world.addAgent(agent)
world.setOrder([agent])

# set parameters
agent.setAttribute('discount', DISCOUNT)
agent.setHorizon(HORIZON)

# add position variable
pos = world.defineState(agent.name, 'position', int, lo=-100, hi=100)
world.setFeature(pos, 0)

# define agents' actions (stay 0, left -1 and right +1)
action = agent.addAction({'verb': 'move', 'action': 'anywhere'})
tree = makeTree(setToFeatureMatrix(pos, pos))
world.setDynamics(pos, action, tree)
action = agent.addAction({'verb': 'move', 'action': 'left'})
tree = makeTree(multiSetMatrix(pos, {pos: 1, CONSTANT: -1}))
world.setDynamics(pos, action, tree)
action = agent.addAction({'verb': 'move', 'action': 'right'})
tree = makeTree(multiSetMatrix(pos, {pos: 1, CONSTANT: 1}))
world.setDynamics(pos, action, tree)

# define rewards (maximize position, i.e., always go right)
agent.setReward(maximizeFeature(pos), 1)

# agent initially believes he is in pos 10, so action values will be inflated according to that
world.setModel(agent.name, Distribution({True: 1.0}))
agent.setBelief(pos, 10)
# agent.setBelief(pos, Distribution({10: 0.5, 12: 0.5}))

print '===================================='
print "Initial beliefs:"
for world_state in world.state[None]._domain.values():
    model = world.getModel(agent.name, world_state)
    agent.printBeliefs(model)

for i in range(MAX_STEPS):
    print '===================================='
    print 'Current pos: ' + str(world.getValue(pos))

    # single decision: left, right or no-move?
    step = world.step()

    # prints all models and beliefs
    print '____________________________________'
    print "Updated beliefs:"
    for world_state in world.state[None]._domain.values():
        model = world.getModel(agent.name, world_state)
        agent.printBeliefs(model)
    print '____________________________________'

    # print step
    world.explain(step, level=2)
