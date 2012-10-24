import sys
from ConfigParser import SafeConfigParser
from optparse import OptionParser

from psychsim.pwl import *
from psychsim.action import Action,ActionSet
from psychsim.world import World,stateKey,actionKey
from psychsim.agent import Agent



if __name__ == '__main__':

    # Create scenario
    world = World()
    totals = {'exiter':3,'follower':4, 'avoider':3} # 

    # there are a mix of agent types that have different reward preferences for heading towards door,
    # following someone who is closest or avoiding the fire
    rewardWeights = {'exiter':{'fire':.4,'door':.5,'follow':.1},'follower':{'fire':.2,'door':.2,'follow':.6},'avoider':{'fire':.6,'door':.3,'follow':.1}}


    # the fire and door are modeled as agents with no actions - they only have a fixed location

    me = Agent('door')
    world.addAgent(me)
    world.defineState(me.name,'x',float)
    world.setState(me.name,'x',5)
    world.defineState(me.name,'y',float)
    world.setState(me.name,'y',5)
    me.setHorizon(0)

    me = Agent('fire')
    world.addAgent(me)
    world.defineState(me.name,'x',float)
    world.setState(me.name,'x',1)
    world.defineState(me.name,'y',float)
    world.setState(me.name,'y',1)
    me.setHorizon(0)

    # Player state, actions and parameters common to both players
    embodiedAgts = []
    for base in ['exiter','follower','avoider']:
        num = 0
        print base
        for i in range(totals[base]):
            num = num + 1
            me = Agent(base + str(num))
            world.addAgent(me)
            # State
            # trying to avoid psychsim thinking in terms x,y coordinates
            # so smartbody will have to maintain these values
            world.defineState(me.name,'door_dist',float)
            world.setState(me.name,'door_dist',3)
            world.defineState(me.name,'fire_dist',float)
            world.setState(me.name,'fire_dist',5)
            world.defineState(me.name,'closest_dist',float)
            world.setState(me.name,'closest_dist',4)
            
            # Actions
            me.addAction({'verb': 'do nothing'})
            me.addAction({'verb': 'runAway','object': 'fire'})
            me.addAction({'verb': 'runTowards','object': 'door'})
            me.addAction({'verb': 'followClosest'})
            # goals
            goal = maximizeFeature(stateKey(me.name,'fire_dist'))
            me.setReward(goal,rewardWeights[base]['fire'])
            goal = minimizeFeature(stateKey(me.name,'door_dist'))
            me.setReward(goal,rewardWeights[base]['door'])
            goal = minimizeFeature(stateKey(me.name,'closest_dist'))
            me.setReward(goal,rewardWeights[base]['follow'])
            # Parameters
            me.setHorizon(1)
            # me.setParameter('discount',0.9)
            me.setParameter('discount',0.2)

    # Turn order: Uncomment the following if you want agents to act in parallel

    actors = world.agents.keys()
    # actors = set(actors)
    # print actors
    # actors.discard('door')
    # actors.discard('fire')
    # world.setOrder([actors])
    actors.remove('door')
    actors.remove('fire')
    world.setOrder([set(actors)])
    print actors
    
    for agt in actors:
        atom = Action({'subject': agt,'verb': 'runAway', 'object':'fire'})
        tree = makeTree(incrementMatrix(stateKey(atom['subject'],'fire_dist'),.1))
        world.setDynamics(agt,'fire_dist',atom,tree)

        atom = Action({'subject': agt,'verb': 'runTowards', 'object':'door'})
        tree = makeTree(incrementMatrix(stateKey(atom['subject'],'door_dist'),-.1))
        world.setDynamics(agt,'door_dist',atom,tree)

        atom = Action({'subject': agt,'verb': 'runClosest'})
        tree = makeTree(incrementMatrix(stateKey(atom['subject'],'closest_dist'),-.1))
        world.setDynamics(agt,'door_dist',atom,tree)

    
    # Save scenario to compressed XML file
    world.save('default.psy')

    # Create configuration file
    # config = SafeConfigParser()
    # f = open('default.cfg','w')
    # config.write(f)
    # f.close()

    # Test saved scenario
    world = World('default.psy')
    # world.printState()
    
    for t in range(7):
        print 'next:',world.next(world.state.expectation())
        world.explain(world.step(),0)
        # world.explain()
        # print world.step()
        world.state.select()

    world.printState()

