# coding=utf-8
from agent import Agent
from helper_functions import multiSetMatrix
from pwl import makeTree, CONSTANT, setToFeatureMatrix
from world import World

agent1 = Agent('Agent 1')
agent2 = Agent('Agent 2')

# turn orders
turn_orders = {'First increment, then copy': [agent1, agent2],
               'First copy, then increment': [agent2, agent1],
               'Simult. increment and copy': [{agent1, agent2}]}

for label, my_turn_order in turn_orders.iteritems():

    # create world and add agents
    world = World()
    world.addAgent(agent1)
    world.addAgent(agent2)

    # add variables
    var_counter = world.defineState(agent1.name, 'counter', int, lo=0, hi=3)
    var_copy = world.defineState(agent2.name, 'counter_copy', int, lo=0, hi=3)

    # define first agent's action (counter increment)
    action = agent1.addAction({'verb': '', 'action': 'increment'})
    tree = makeTree(multiSetMatrix(var_counter, {var_counter: 1, CONSTANT: 1}))
    world.setDynamics(var_counter, action, tree)

    # define second agent's action (var is copy from counter)
    action = agent2.addAction({'verb': '', 'action': 'copy'})
    tree = makeTree(setToFeatureMatrix(var_copy, var_counter))
    world.setDynamics(var_copy, action, tree)

    world.setOrder(my_turn_order)

    # resets vars
    world.setFeature(var_copy, 0)
    world.setFeature(var_counter, 0)

    print '_______________________________'
    print label

    # steps
    for i in range(3):
        print 'Step ' + str(i)
        step = world.step()
        # print step
        world.explain(step, level=4)
        world.printState()
