# coding=utf-8
import random
from agent import Agent
from reward import minimizeFeature
from world import World

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
agent.setReward(minimizeFeature(var), 1)

# add dummy actions
agent.addAction({'verb': '', 'action': 'dummy1'})
agent.addAction({'verb': '', 'action': 'dummy2'})
agent.setHorizon(0)
agent.setAttribute('discretization', NUM_GROUPS)

# reward function
print '===================================='
print 'High:\t' + str(HIGH)
print 'Low:\t' + str(LOW)
print 'Groups:\t' + str(NUM_GROUPS)

for i in range(NUM_SAMPLES):
    num = random.uniform(LOW, HIGH)
    world.setFeature(var, num)
    print 'x=' + str(world.getValue(var))
    world.explain(world.step(), level=2)
    print '____________________________________'
