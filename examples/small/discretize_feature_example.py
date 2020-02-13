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

# add variable
var = world.defineState(agent.name, 'x', float, lo=LOW, hi=HIGH)

# reward function
print '===================================='
print 'High:\t' + str(HIGH)
print 'Low:\t' + str(LOW)
print 'Groups:\t' + str(NUM_GROUPS)

for i in range(NUM_SAMPLES):
    num = random.uniform(LOW, HIGH)
    world.setFeature(var, num)
    before = str(world.getValue(var))
    discretize_feature(world, var, NUM_GROUPS)
    print before + '\t-> ' + str(world.getValue(var))
