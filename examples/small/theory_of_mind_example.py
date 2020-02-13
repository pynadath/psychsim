# coding=utf-8
from agent import Agent
from helper_functions import multiCompareRow, get_decision_info, explain_decisions, multiSetMatrix
from pwl import KeyedVector, CONSTANT, makeTree, equalRow
from world import World

# parameters (payoffs according to the Chicken Game)
MODEL_NAME = 'my model'
SUCKER = KeyedVector({CONSTANT: 0})  # CD
TEMPTATION = KeyedVector({CONSTANT: 2})  # DC
MUTUAL_COOP = KeyedVector({CONSTANT: 1})  # CC
PUNISHMENT = KeyedVector({CONSTANT: -10})  # DD


# defines a payoff matrix tree
def get_reward_tree(my_coop, other_coop):
    return makeTree({'if': multiCompareRow({my_coop: 1}),
                     True: {'if': multiCompareRow({my_coop: -1}),
                            True: KeyedVector({CONSTANT: 0}),
                            False: {'if': equalRow(my_coop, 2),
                                    True: {'if': equalRow(other_coop, 2),
                                           True: MUTUAL_COOP,
                                           False: SUCKER},
                                    False: {'if': equalRow(other_coop, 2),
                                            True: TEMPTATION,
                                            False: PUNISHMENT}}},
                     False: KeyedVector({CONSTANT: 0})})


# gets a state description
def get_state_desc(my_world, my_coop):
    result = str(my_world.getFeature(my_coop)).replace("100%\t", "")
    if result == '0':
        return 'start'
    if result == '1':
        return 'defected'
    if result == '2':
        return 'cooperated'


# create world and add agent
world = World()
agent1 = Agent('Agent 1')
world.addAgent(agent1)
agent2 = Agent('Agent 2')
world.addAgent(agent2)

# define order
my_turn_order = [{agent1, agent2}]
world.setOrder(my_turn_order)

agents_coop = []
agents = [agent1, agent2]
for agent in agents:
    # set agent's params
    agent.setAttribute('discount', 1)
    agent.setHorizon(1)
    agent.setRecursiveLevel(1)

    # add 'cooperated' variable (0 = didn't decide, 1 = Defected, 2 = Cooperated)
    coop = world.defineState(agent.name, 'cooperated', int, lo=0, hi=100)
    world.setFeature(coop, 0)
    agents_coop.append(coop)

    # define agents' actions (defect and cooperate)
    action = agent.addAction({'verb': '', 'action': 'defect'})
    tree = makeTree(multiSetMatrix(coop, {coop: 1, CONSTANT: 1}))
    world.setDynamics(coop, action, tree)
    action = agent.addAction({'verb': '', 'action': 'cooperate'})
    tree = makeTree(multiSetMatrix(coop, {coop: 1, CONSTANT: 2}))
    world.setDynamics(coop, action, tree)

    # add mental model
    agent.addModel(MODEL_NAME)

# add mental model of the other for each agent
world.setMentalModel(agent1.name, agent2.name, {MODEL_NAME: 1})
world.setMentalModel(agent2.name, agent1.name, {MODEL_NAME: 1})

# defines payoff matrices
agent1.setReward(get_reward_tree(agents_coop[0], agents_coop[1]), 1)
agent2.setReward(get_reward_tree(agents_coop[1], agents_coop[0]), 1)

# 'single' decision (1 per agent): cooperate or defect?
for i in range(len(my_turn_order)):
    print '===================================='
    print 'Step ' + str(i)
    step = world.step()
    for j in range(len(agents)):
        print agents[j].name + ': ' + get_state_desc(world, agents_coop[j])
    print '________________________________'
    world.explain(step, level=2)

    print('\n')
    for i in range(len(agents)):
        decision_infos = get_decision_info(step, agents[i].name)
        explain_decisions(agents[i].name, decision_infos)
