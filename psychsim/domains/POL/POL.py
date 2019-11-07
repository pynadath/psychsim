
from psychsim.reward import *
from psychsim.pwl import *
from psychsim.action import *
from psychsim.world import *
from psychsim.agent import *

import logging
import random
from random import randint
from time import time

from export import exportCS

class Person(Agent):
    def __init__(self, name, init_location, world, feelings_toward, random_horizon=False, random_weights=False, random_costs=False):
        Agent.__init__(self,name)
        world.addAgent(self)

        # set the horizon to 2, so he can see that it should make money to eat
        
        horizon_value=randint(1,4) if random_horizon else 2
        print('\n'+name+':')
        print(' Horizon: '+str(horizon_value)+'\n')
        self.setAttribute('horizon',horizon_value)

        
        # define features of a civilian
        current_x=world.defineState(self.name,'current_x')
        current_y=world.defineState(self.name,'current_y')
        wealth=world.defineState(self.name,'wealth')
        hunger=world.defineState(self.name,'hunger')
        comfort=world.defineState(self.name,'comfort')
        health=world.defineState(self.name,'health')


        # initialize the features
        self.setState('current_x', init_location[0])
        self.setState('current_y', init_location[1])
        self.setState('wealth', 0.)
        self.setState('hunger', 0.)
        self.setState('comfort', 0.)
        self.setState('health', 1.)


        # define rewards
        wealth_weight  =randint(3,6)*1. if random_weights else 3.
        comfort_weight =randint(3,6)*1. if random_weights else 4.
        health_weight  =randint(5,8)*1. if random_weights else 6.
        hunger_weight  =randint(3,6)*1. if random_weights else 5.
        print(' Wealth Weight: ' +str(wealth_weight ))
        print(' Comfort Weight: '+str(comfort_weight))
        print(' Health Weight: ' +str(health_weight ))
        print(' Hunger Weight: ' +str(hunger_weight )+'\n')
        self.setReward(maximizeFeature(wealth,self.name),  wealth_weight)## maximize
        self.setReward(maximizeFeature(comfort,self.name),comfort_weight)
        self.setReward(maximizeFeature(health,self.name),  health_weight)
        self.setReward(minimizeFeature(hunger,self.name),  hunger_weight)## minimize


        # define actions
        time2work=8
        time2home=16
        time_pass = stateKey('current_environment','time_pass') # point to the same variable
        tree= makeTree({'if': thresholdRow(time_pass,time2work), # if time_pass is larger than time2work, larger than 8
                        True: {'if': thresholdRow(time_pass,time2home), # if the time_pass is less than time2home, less than 16
                                True: False,
                                False: True},
                        False: False})
        work = self.addAction({'verb':'GoWork'}, tree)

        
        eating_cost =randint(10,50)*.01 if random_costs else .5
        wealth_cost =randint(10,20)*.01 if random_costs else .1 
        hunger_cost =randint(10,20)*.01 if random_costs else .1
        comfort_cost=randint(10,20)*.01 if random_costs else .1
        print(' Eating Cost: ' +str(eating_cost ))
        print(' Wealth Cost: ' +str(wealth_cost ))
        print(' Hunger Cost: ' +str(hunger_cost ))
        print(' Comfort Cost: '+str(comfort_cost))
        print('------------------------------------')


        # see if wealth is larger than the eating cost before eating
        tree= makeTree({'if': thresholdRow(wealth,eating_cost),
                        True: True,
                        False: False})
        eat = self.addAction({'verb':'GoEat'}, tree)
        gohome = self.addAction({'verb':'GoHome'})

        # set dynamics
        commercial=world.agents['commercial']

        ## impacts of work
        tree = makeTree(setToConstantMatrix(current_x,randint(commercial.lower_x, commercial.higher_x)))
        world.setDynamics(current_x,work,tree)
        tree = makeTree(setToConstantMatrix(current_y,randint(commercial.lower_y, commercial.higher_y)))
        world.setDynamics(current_y,work,tree)
        ### instead of increments by a constant, we increase by a percentage, so that the changes in one need will be proportionally reflected in the multiplications. That is, instead of weights being multiplied by a certian value each time, they will be multiplied by the amount of change. This way, if one need is not satified, over time, it will get more attention.
        tree = makeTree(approachMatrix(wealth,wealth_cost,100))
        world.setDynamics(wealth,work,tree)

        tree = makeTree(approachMatrix(hunger,hunger_cost,100))
        world.setDynamics(hunger,work,tree)

        tree = makeTree(approachMatrix(comfort,comfort_cost,100))
        world.setDynamics(comfort,work,tree)

        risk = stateKey('commercial','risk')
        initialHealth = 1.
        decline_perc = .9

        ## impacts of eat
        tree = makeTree(approachMatrix(hunger,.9,0))
        world.setDynamics(hunger,eat,tree)

        tree = makeTree(approachMatrix(wealth,eating_cost,0))
        world.setDynamics(wealth,eat,tree)

        residential=world.agents['residential']

        ## impacts of gohome
        tree = makeTree(setToConstantMatrix(current_x,randint(residential.lower_x,residential.higher_x)))
        world.setDynamics(current_x,gohome,tree)
        tree = makeTree(setToConstantMatrix(current_y,randint(residential.lower_y, residential.higher_y)))
        world.setDynamics(current_y,gohome,tree)

        tree = makeTree(approachMatrix(comfort,comfort_cost,100))
        world.setDynamics(comfort,gohome,tree)

        tree = makeTree(approachMatrix(hunger,hunger_cost,100))
        world.setDynamics(hunger,gohome,tree)

        # make future this where we have the value for time T and time T+1, and we are defining the new health value
        # this is basically what it means:
        # future health= current health* (1-decline_perc)+ decline_perc*initialHealth -future risk*decline_perc
        tree = makeTree(KeyedMatrix({makeFuture(health): KeyedVector({health: 1.-decline_perc, CONSTANT: decline_perc*initialHealth, makeFuture(risk): -(decline_perc/2), makeFuture(hunger): - (decline_perc/2)})}))
        
        # this is the actual effect, has nothing to do with decision making. future risk means 
        world.setDynamics(health,work,tree)


    def init_attitudes(self, world): #attitude is a float in the range of [-1.,1.]
        armed_forces_objs= [self.world.agents[name] for name in self.world.agents if isinstance(self.world.agents[name],ArmedForces)]
        
        for armed_force in armed_forces_objs:

            attitude= self.world.defineRelation(self.name,armed_force,'attitude',float)
            if armed_force.friendly:
                self.world.setFeature(attitude,0.1)
            else:
                self.world.setFeature(attitude,-0.1)

    # ignore the other people unless they are not civilians
    def init_beliefs(self):
        relevant = {key for key in self.world.state.keys() if state2agent(key) == self.name or state2agent(key)[:8] != 'Civilian'}
        return self.resetBelief(include=relevant)


class Region(Agent):
    def __init__(self, name, lower_points, higher_points, max_occupancy, world):
        Agent.__init__(self,name)
        world.addAgent(self)
        self.lower_x, self.lower_y = lower_points
        self.higher_x, self.higher_y= higher_points
        self.max_occupancy=max_occupancy

        current_occupancy = world.defineState(self.name,'current_occupancy')
        self.setState('current_occupancy', 0)

        #risk/danger level of being in this region for a civilian health
        risk = world.defineState(self.name,'risk')
        self.setState('risk', 0)

class Environment(Agent):
    def __init__(self, name, world):
        Agent.__init__(self,name)
        world.addAgent(self)
        time_pass=world.defineState(self.name,'time_pass')

#       time_increase = self.addAction({'verb':'time_increase'})
        self.setState('time_pass', 0)

        # impact of time_increase
        tree = makeTree(incrementMatrix(time_pass,1))
        world.setDynamics(time_pass,True,tree)

class ArmedForces(Agent):
    def __init__(self, name, world, init_location, friendly):
        Agent.__init__(self,name)
        world.addAgent(self)

        self.friendly=friendly

        current_x=world.defineState(self.name,'current_x')
        current_y=world.defineState(self.name,'current_y')
        self.setState('current_x', init_location[0])
        self.setState('current_y', init_location[1])

        do_good_cost=.15
        do_bad_cost=.15
        # region_names = [name for name in self.world.agents if isinstance(self.world.agents[name],Region)]
        region_objs= [self.world.agents[name] for name in self.world.agents if isinstance(self.world.agents[name],Region)]
        civilian_objs= [self.world.agents[name] for name in self.world.agents if isinstance(self.world.agents[name],Region)]
        
        do_nothing = self.addAction({'verb':'do_nothing'})
        tree = makeTree(incrementMatrix(current_x,0.)) # it does nothing
        world.setDynamics(current_x,do_nothing,tree)
        # here we have to write it declaratively because it is not executed now. so we define the actions over all of the regions and their risks but here in the Armed_Forced class where the actions impact the risks
        for region in region_objs:

            # each armed_force can only take action in the region it is in. the tree below checks for that
            tree= makeTree({'if': thresholdRow(current_x, region.lower_x), # if armed_force's x is larger than lower end of x_range
                        True: {'if': thresholdRow(current_x, region.higher_x), # if the armed_force's x is less than upper end of x_range
                                True: False,
                                False: {'if': thresholdRow(current_y, region.lower_y), # if armed_force's y is larger than lower end of y_range
                                    True: {'if': thresholdRow(current_y, region.higher_y), # if the armed_force's y is less than upper end of y_range
                                        True: False,
                                        False: True},
                                    False: False}},
                        False: False})
            # print(tree[world.state])
            do_good = self.addAction({'verb':'do_good', 'object':region.name}, tree)
            do_bad = self.addAction({'verb':'do_bad', 'object':region.name}, tree)
            
            risk=stateKey(region.name,'risk')

            if friendly:
                self.setReward(minimizeFeature(risk,self.name), 5.)
            else:
                self.setReward(maximizeFeature(risk,self.name), 5.)
            
            tree = makeTree(approachMatrix(risk,do_good_cost,0.))
            world.setDynamics(risk,do_good,tree)

            tree = makeTree(incrementMatrix(risk,do_bad_cost))
            #tree = makeTree(approachMatrix(risk,do_bad_cost,1.))
            world.setDynamics(risk,do_bad,tree)
            
            # go through all of the civilians and change their attitudes based on the action that is being taken
            for civilian in civilian_objs:
                attitude=binaryKey(civilian.name, self.name, 'attitude')
                current_x=stateKey(civilian.name, 'current_x')
                current_y=stateKey(civilian.name, 'current_y')
                # below, we have the impact of armed forces' actions on the civilians' attitudes. it approcaches 1 for doing good and -1 for doing bad.
                # here if the civilian is in the same region, the impact on attitude is higher: 0.2, otherwise, for all other cases, it is lower: 0.1
                tree= makeTree({'if': thresholdRow(current_x, region.lower_x), 
                        True: {'if': thresholdRow(current_x, region.higher_x), 
                                True: approachMatrix(attitude,0.1,1.0), # when civilian is  NOT in the same region, the impact is lower: .1 
                                False: {'if': thresholdRow(current_y, region.lower_y), 
                                    True: {'if': thresholdRow(current_y, region.higher_y), 
                                        True: approachMatrix(attitude,0.1,1.0), # when civilian is  NOT in the same region, the impact is lower: .1 
                                        False: approachMatrix(attitude,0.2,1.0)}, # when civilian is in the same region, the impact is higher: .2 
                                    False: approachMatrix(attitude,0.1,1.0)}}, # when civilian is  NOT in the same region, the impact is lower: .1 
                        False: approachMatrix(attitude,0.1,1.0)}) # when civilian is  NOT in the same region, the impact is lower: .1 
                world.setDynamics(attitude,do_good,tree)
                tree= makeTree({'if': thresholdRow(current_x, region.lower_x), 
                        True: {'if': thresholdRow(current_x, region.higher_x), 
                                True: approachMatrix(attitude,0.1,-1.0), # when civilian is  NOT in the same region, the impact is lower: .1 
                                False: {'if': thresholdRow(current_y, region.lower_y), 
                                    True: {'if': thresholdRow(current_y, region.higher_y), 
                                        True: approachMatrix(attitude,0.1,-1.0), # when civilian is  NOT in the same region, the impact is lower: .1 
                                        False: approachMatrix(attitude,0.2,-1.0)}, # when civilian is in the same region, the impact is higher: .2 
                                    False: approachMatrix(attitude,0.1,-1.0)}}, # when civilian is  NOT in the same region, the impact is lower: .1 
                        False: approachMatrix(attitude,0.1,-1.0)}) # when civilian is  NOT in the same region, the impact is lower: .1
                world.setDynamics(attitude,do_bad,tree)
            
            # print(world.dynamics[risk][do_bad])

            # print(world.dynamics.keys())

            # print(world.dynamics[do_bad][risk])

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    start_time=time()   
    world = World()
    # below, the first tuple is (lower_x, lower_y) and the second one is (higher_x, higher_y)
    residential = Region('residential', (30,30), (50,50), 100, world)

    commercial = Region('commercial', (75,35), (85,45), 25, world)

    environment_agent =Environment('current_environment', world)

    civilians=[]
    civilian_count=50
    for j in range(civilian_count):
        starting_location=(randint(residential.lower_x,residential.higher_x), randint(residential.lower_y,residential.higher_y))
        civilian = Person('Civilian %d' %(j+1), starting_location, world, True, True, True)
        civilians.append(civilian.name)


    friendly_force_location=(randint(commercial.lower_x, commercial.higher_x), randint(commercial.lower_y, commercial.higher_y))
    
    hostile_force_location=friendly_force_location #both in the same region

#   friendly_force=ArmedForces('Friendly_Force', world, friendly_force_location, True)
#   hostile_force=ArmedForces('Hostile_Force', world, hostile_force_location, False) 
    # print(hostile_force.getActions())
    #exit()
    
    world.setAllParallel()


    for name in civilians:
        world.agents[name].init_beliefs()
#       world.agents[name].init_attitudes(world)
        print(name)
        exportCS(world,name)
        
    
    with open(os.path.join(os.path.dirname(__file__), 'PSCivilianInit.cs'), 'w') as initFile:
		
        
        initFile.write('using UnityEngine;\n')
        initFile.write('namespace PsychSim \n')
        initFile.write('{\n')
        initFile.write('\tpublic partial class TssPsController : MonoBehaviour\n')
        initFile.write('\t{\n')

        for j in range(civilian_count):
            initFile.write('\t\tPSCivilian%d mPSCivilian%d;\n'% (j+1, j+1))
        initFile.write('\t\tint numAgents = %d;\n\n'%(civilian_count))
        
        initFile.write('\t\tvoid InitializeCivilians()\n')
        initFile.write('\t\t{\n')
        initFile.write('\t\t\tGameObject psCivilians = new GameObject("PS Civilians");\n')

        for j in range(civilian_count):
            
            initFile.write('\t\t\tmPSCivilian%d = mIAgents[%d].AddComponent<PSCivilian%d>();\n'%(j+1, j, j+1))
            initFile.write('\t\t\tmPSCivilian%d.transform.SetParent(psCivilians.transform);\n'%(j+1))
            initFile.write('\t\t\tmPSCivilian%d.agentId = mIAgents[%d].id;\n'%(j+1, j))
            initFile.write('\t\t\tmPSCivilian%d.SetController(this);\n'%(j+1))
            initFile.write('\t\t\tmPSCivilian%d.ActionChanged += OnActionChanged;\n\n'%(j+1))
    
        initFile.write('\t\t}\n')
        initFile.write('\t}\n')
        initFile.write('}')


    exit()
    for i in range(24):
        start_round=time()
        print('\n \tStep %d: ' %(i+1))
        newState = world.step()
        #world.explainAction(newState)
        world.printState(newState)
        end_round = time()
        time_elapsed = round(end_round - start_round)
        print('Step time: %02d:%02d:%02d' %(int(time_elapsed/3600), int((time_elapsed%3600)/60), time_elapsed%60))
        print('----------------------------------------------------------------------')
        # for action,tree in world.dynamics['residential\'s risk'].items():
        #   print(action)
        #   print(tree)

    end_time=time()
    time_overall = end_time - start_time
    print('Overall time for %d civilians: %02d:%02d:%02d' %(civilian_count, int(time_overall/3600), int(time_overall%3600/60), time_overall%60))

# print('x: ' + str(world.getState(civilian1.name,'x')) + ' , y: ' + str(world.getState(civilian1.name,'y')))
# print('goal x: ' + str(world.getState(civilian1.name,'goal_x')) + ' , goal y: ' + str(world.getState(civilian1.name,'goal_y')))
