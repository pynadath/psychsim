# coding=utf-8
from psychsim_agents.helper_functions import *
from psychsim.world import *
import random

HIGH = 100
LOW = 50
NUM_GROUPS = 10
NUM_SAMPLES = 100

# create world and add agent
world = World()
agent = Agent('Agent')
world.addAgent(agent)
world.setOrder([agent])

# add variable
var = world.defineState(agent.name, 'x', float, lo=LOW, hi=HIGH)

# set reward function (minimize x)
agent.setReward(makeTree(create_discretized_reward_tree(world, var, NUM_GROUPS)), -1)

# add dummy actions
agent.addAction({'verb': '', 'action': 'dummy1'})
agent.addAction({'verb': '', 'action': 'dummy2'})

agent.setHorizon(0)

print '===================================='
print 'High:\t' + str(HIGH)
print 'Low:\t' + str(LOW)
print 'Groups:\t' + str(NUM_GROUPS)

for i in range(NUM_SAMPLES):
    num = random.uniform(LOW, HIGH)
    world.setFeature(var, num)
    before = str(world.getFeature(var))
    world.printState()
    world.explain(world.step(), level=2)
    print '____________________________________'
