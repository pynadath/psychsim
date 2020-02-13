# coding=utf-8
from psychsim_agents.helper_functions import *
from psychsim.world import *
from psychsim.reward import *

# parameters
NUM_STEPS = 4
MODEL_NAME = 'my_model'

if __name__ == '__main__':

    # create world and add agents
    world = World()
    ag_producer = Agent('Producer')
    world.addAgent(ag_producer)
    ag_consumer = Agent('Consumer')
    world.addAgent(ag_consumer)
    agents = [ag_producer, ag_consumer]

    # define order (parallel execution)
    my_turn_order = [{ag_producer, ag_consumer}]
    world.setOrder(my_turn_order)

    # agent settings
    ag_producer.setAttribute('discount', 1)
    ag_producer.setHorizon(2)
    ag_consumer.setAttribute('discount', 1)
    ag_consumer.setHorizon(2)

    # add variables
    var_half_cap = world.defineState(ag_producer.name, 'half capacity', bool)
    world.setFeature(var_half_cap, False)
    var_ask_amnt = world.defineState(ag_producer.name, 'asked amount', int, lo=0, hi=10)
    world.setFeature(var_ask_amnt, 0)
    var_rcv_amnt = world.defineState(ag_consumer.name, 'received amount', int, lo=0, hi=10)
    world.setFeature(var_rcv_amnt, 0)

    # add producer actions
    # produce capacity: if half capacity then 0.5 asked amount else asked amount)
    act_prod = ag_producer.addAction({'verb': '', 'action': 'produce'})
    tree = makeTree({'if': equalRow(var_half_cap, True),
                     True: multiSetMatrix(var_rcv_amnt, {var_ask_amnt: 0.5}),
                     False: setToFeatureMatrix(var_rcv_amnt, var_ask_amnt)})
    ag_producer.world.setDynamics(var_rcv_amnt, act_prod, tree)

    # add consumer actions (ask more = 10 / less = 5)
    act_ask_more = ag_consumer.addAction({'verb': '', 'action': 'ask_more'})
    tree = makeTree(setToConstantMatrix(var_ask_amnt, 10))
    ag_consumer.world.setDynamics(var_ask_amnt, act_ask_more, tree)

    act_ask_less = ag_consumer.addAction({'verb': '', 'action': 'ask_less'})
    tree = makeTree(setToConstantMatrix(var_ask_amnt, 5))
    ag_consumer.world.setDynamics(var_ask_amnt, act_ask_less, tree)

    # add mental models
    ag_producer.addModel(MODEL_NAME)
    ag_consumer.addModel(MODEL_NAME)

    # add mental model of the other for each agent
    world.setMentalModel(ag_producer.name, ag_consumer.name, {MODEL_NAME: 1})
    world.setMentalModel(ag_consumer.name, ag_producer.name, {MODEL_NAME: 1})

    # defines payoff for consumer agent: if received amount > 5 then 10 - rcv_amnt else rcv_amount
    # this simulates over-stock cost, best is to receive max of 5, more than this has costs
    ag_consumer.setReward(makeTree({'if': thresholdRow(var_rcv_amnt, 5),
                                    True: KeyedVector({CONSTANT: 10, var_rcv_amnt: -1}),
                                    False: KeyedVector({var_rcv_amnt: 1})}), 1)

    # sets consumer belief that producer is at half-capacity, making it believe that asking more has more advantage
    # - in reality, producer is always at full capacity, so best strategy would be to always ask less
    ag_consumer.setBelief(var_half_cap, True)

    # NOTE: this is equivalent to:
    # --------------------------------
    # ag_consumer.setBelief(var_half_cap, Distribution({True: 1}))
    # ag_consumer.setBelief(var_half_cap, True, True)

    # NOTE: also, setting the belief in the producer's model is unnecessary
    # because the consumer already believes in half-capacity:
    # --------------------------------
    # ag_producer.setBelief(var_half_cap, True, MODEL_NAME)

    total_rwd = 0
    for i in range(NUM_STEPS):
        print '===================================='
        print 'Step ' + str(i)
        step = world.step()
        reward = get_current_reward(ag_consumer, world)
        print 'Half capacity:\t\t' + str(world.getValue(var_half_cap))
        print 'Asked amount:\t\t' + str(world.getValue(var_ask_amnt))
        print 'Received amount:\t' + str(world.getValue(var_rcv_amnt))
        print 'Consumer reward:\t' + str(reward)
        total_rwd += reward

        print '________________________________'
        world.explain(step, level=2)

    print '===================================='
    print 'Total reward: ' + str(total_rwd)
