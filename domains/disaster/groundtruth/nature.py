from psychsim.pwl import *
from psychsim.agent import Agent
from data import likert
from region import Region

class Nature(Agent):
    def __init__(self,world,config):
        Agent.__init__(self,'Nature')
        world.addAgent(self)

        world.diagram.setColor(self.name,'red')

        evolution = self.addAction({'verb': 'evolve'})

        phase = world.defineState(self.name,'phase',list,['none','approaching','active'])
        world.setFeature(phase,'none')
        days = world.defineState(self.name,'days',int)
        world.setFeature(days,0)

        regions = sorted([name for name in self.world.agents
                                if isinstance(self.world.agents[name],Region)])
        location = world.defineState(self.name,'location',list,regions+['none'])
        world.setFeature(location,'none')
        
        # Phase dynamics
        prob = likert[5][config.getint('Disaster','phase_change_prob')-1]
        minDays = config.getint('Disaster','phase_min_days')
        tree = makeTree({'if': equalRow(phase,'none'),
                         # When does a hurricane emerge
                         True: {'if': thresholdRow(days,minDays),
                                True: {'distribution': [(setToConstantMatrix(phase,'approaching'),
                                                         prob),
                                                        (noChangeMatrix(phase),1.-prob)]},
                                False: noChangeMatrix(phase)},
                         False: {'if': equalRow(phase,'approaching'),
                                 # When does hurricane make landfall
                                 True: {'if': thresholdRow(days,minDays),
                                        True: {'distribution': [(setToConstantMatrix(phase,'active'),
                                                                 prob),
                                                                (noChangeMatrix(phase),1.-prob)]},
                                        False: noChangeMatrix(phase)},
                                 # Active hurricane
                                 False: {'if': equalRow(location,'none'),
                                         True: setToConstantMatrix(phase,'none'),
                                         False: noChangeMatrix(phase)}}})
        world.setDynamics(phase,evolution,tree)

        tree = makeTree({'if': equalFeatureRow(phase,makeFuture(phase)),
                         True: incrementMatrix(days,1),
                         False: setToConstantMatrix(days,0)})
        world.setDynamics(days,True,tree)

        category = world.defineState(self.name,'category',int)
        world.setFeature(category,0)

        tree = makeTree({'if': equalRow(makeFuture(phase),'approaching'),
                         True: {'if': equalRow(category,0),
                                # Generate a random cateogry
                                True: {'distribution': [(setToConstantMatrix(category,1),0.2),
                                                        (setToConstantMatrix(category,2),0.2),
                                                        (setToConstantMatrix(category,3),0.2),
                                                        (setToConstantMatrix(category,4),0.2),
                                                        (setToConstantMatrix(category,5),0.2)]},
                                False: noChangeMatrix(category)},
                         False: {'if': equalRow(makeFuture(phase),'active'),
                                 True: noChangeMatrix(category),
                                 False: setToConstantMatrix(category,0)}})
        world.setDynamics(category,evolution,tree)

        # For computing initial locations
        coastline = {r for r in regions if world.agents[r].x == 1}
        prob = 1./float(len(coastline))
        # For computing hurricane movement
        subtree = noChangeMatrix(location)
        for name in regions:
            region = world.agents[name]
            subtree = {'if': equalRow(location,name),
                       True: {'distribution': [(setToConstantMatrix(location,region.north),0.5),
                                               (setToConstantMatrix(location,region.east),0.5)]},
                       False: subtree}
        tree = makeTree({'if': equalRow(makeFuture(phase),'approaching'),
                         True: {'if': equalRow(location,'none'),
                                # Generate initial location estimate
                                True: {'distribution': [(setToConstantMatrix(location,r),prob) \
                                                        for r in coastline]},
                                # No change?
                                False: noChangeMatrix(location)},
                         False: {'if': equalRow(makeFuture(phase),'active'),
                                 # Hurricane moving through regions
                                 True: subtree,
                                 # No hurricane
                                 False: setToConstantMatrix(location,'none')}})
        world.setDynamics(location,evolution,tree)

        # Effect of disaster on risk
        base_increase = likert[5][config.getint('Disaster','risk_impact')-1]
        base_decrease = likert[5][config.getint('Disaster','risk_decay')-1]
        for region in regions:
            risk = stateKey(region,'risk')
            tree = noChangeMatrix(risk)
            for center in regions:
                distance = abs(world.agents[center].x-world.agents[region].x) + \
                           abs(world.agents[center].y-world.agents[region].y)
                subtree = approachMatrix(risk,base_increase*5,1.)
                for cat in range(4):
                    effect = base_increase*float(cat+1)/float(distance+2)
                    subtree = {'if': equalRow(category,cat+1),
                            True: approachMatrix(risk,effect,1.),
                            False: subtree}
                tree = {'if': equalRow(makeFuture(location),center),
                        True: subtree,
                        False: tree}
            tree = makeTree({'if': equalRow(makeFuture(phase),'active'),
                             True: tree, False: approachMatrix(risk,base_decrease,0.)})
            world.setDynamics(risk,evolution,tree)
        if config.getboolean('Shelter','exists'):
            for index in map(int,config.get('Shelter','region').split(',')):
                region = Region.nameString % (index)
                risk = stateKey(region,'shelterRisk')
                subtree = noChangeMatrix(risk)
                for cat in range(5):
                    effect = base_increase*float(cat)
                    subtree = {'if': equalRow(category,cat+1),
                               True: approachMatrix(risk,effect,1.),
                               False: subtree}
                tree = makeTree({'if': equalRow(makeFuture(phase),'active'),
                                 True: {'if': equalRow(makeFuture(location),region),
                                        True: subtree,
                                        False: noChangeMatrix(risk)},
                                 False: approachMatrix(risk,base_decrease,0.)})
                world.setDynamics(risk,evolution,tree)
        self.setAttribute('static',True)

        # Advance calendar after Nature moves
        tree = makeTree(incrementMatrix(stateKey(WORLD,'day'),1))
        world.setDynamics(stateKey(WORLD,'day'),evolution,tree)
