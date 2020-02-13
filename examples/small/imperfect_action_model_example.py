# coding=utf-8
from agent import Agent
from world import World
from helper_functions import multiCompareRow, set_illegal_action, set_legal_action
from pwl import KeyedVector, CONSTANT, makeTree, KeyedMatrix
from multiprocessing import Process, freeze_support

# parameters (positive reward if sides are different, otherwise punishment)
DIFF_SIDES_RWD = KeyedVector({CONSTANT: 1})
SAME_SIDE_RWD = KeyedVector({CONSTANT: -1})
NUM_STEPS = 4
MODEL_NAME = 'my_model'


# defines reward tree
def get_reward_tree(my_side, other_side):
    return makeTree({'if': multiCompareRow({my_side: 1}),
                     True: {'if': multiCompareRow({my_side: -1}),
                            True: KeyedVector({CONSTANT: 0}),
                            False: {'if': multiCompareRow({my_side: 1, other_side: -1}),
                                    True: {'if': multiCompareRow({other_side: 1, my_side: -1}),
                                           True: SAME_SIDE_RWD,
                                           False: DIFF_SIDES_RWD},
                                    False: DIFF_SIDES_RWD}},
                     False: KeyedVector({CONSTANT: 0})})


# gets a state description
def get_state_desc(my_world, my_side):
    result = str(my_world.getFeature(my_side)).replace("100%\t", "")
    if result == '0':
        return 'start'
    if result == '1':
        return 'left'
    if result == '2':
        return 'right'


if __name__ == '__main__':
    freeze_support()

    # create world and add agents
    world = World()
    agent1 = Agent('Agent 1')
    world.addAgent(agent1)
    agent2 = Agent('Agent 2')
    world.addAgent(agent2)

    # define order
    my_turn_order = [{agent1, agent2}]
    world.setOrder(my_turn_order)

    sides = []
    rights = []
    lefts = []

    agents = [agent1, agent2]
    for agent in agents:
        # set agent's params
        agent.setAttribute('discount', 1)
        agent.setHorizon(1)

        # add 'side chosen' variable (0 = didn't decide, 1 = went left, 2 = went right)
        side = world.defineState(agent.name, 'side', int, lo=0, hi=2)
        sides.append(side)

        # define agents' actions (left and right)
        action = agent.addAction({'verb': '', 'action': 'go left'})
        tree = makeTree(KeyedMatrix({side: KeyedVector({CONSTANT: 1})}))
        world.setDynamics(side, action, tree)
        lefts.append(action)

        action = agent.addAction({'verb': '', 'action': 'go right'})
        tree = makeTree(KeyedMatrix({side: KeyedVector({CONSTANT: 2})}))
        world.setDynamics(side, action, tree)
        rights.append(action)

        # set the untie to stochastic
        agent.models[True]['selection'] = 'random'

        # add real/true mental model
        model = agent.addModel(MODEL_NAME)
        model['selection'] = 'random'

    # add mental model of the other for each agent
    world.setMentalModel(agent1.name, agent2.name, {MODEL_NAME: 1})
    world.setMentalModel(agent2.name, agent1.name, {MODEL_NAME: 1})

    # defines payoff matrices
    agent1.setReward(get_reward_tree(sides[0], sides[1]), 1)
    agent2.setReward(get_reward_tree(sides[1], sides[0]), 1)

    # 'hides' right actions from models by setting them illegal
    # (therefore agents should always choose right because they think the other will choose left)
    set_illegal_action(agent1, rights[0], [MODEL_NAME])
    set_illegal_action(agent2, rights[1], [MODEL_NAME])

    # ** unnecessary / just for illustration **:
    # set left actions legal for both the agents and their models
    set_legal_action(agent1, lefts[0], [True, MODEL_NAME])
    set_legal_action(agent2, lefts[1], [True, MODEL_NAME])

    for i in range(NUM_STEPS):
        # reset
        for j in range(len(agents)):
            world.setFeature(sides[j], 0)

        print '===================================='
        print 'Step ' + str(i)
        step = world.step()
        for j in range(len(agents)):
            print agents[j].name + ': ' + get_state_desc(world, sides[j])

        print '________________________________'
        world.explain(step, level=2)
