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

        category = world.defineState(self.name,'category',int)
        world.setFeature(category,0)
        
        # Phase dynamics
        prob = likert[5][config.getint('Disaster','phase_change_prob')-1]
        minDays = config.getint('Disaster','phase_min_days')
        tree = {'if': equalRow(phase,['none','approaching']),
                # When does a hurricane emerge
                0: {'if': thresholdRow(days,minDays),
                    True: {'distribution': [(setToConstantMatrix(phase,'approaching'),
                                             prob),
                                            (setToConstantMatrix(phase,'none'),1.-prob)]},
                    False: setToConstantMatrix(phase,'none')},
                # When does hurricane make landfall
                1:{'if': thresholdRow(days,minDays),
                   True: {'distribution': [(setToConstantMatrix(phase,'active'),prob),
                                           (setToConstantMatrix(phase,'approaching'),1.-prob)
                   ]},
                   False: setToConstantMatrix(phase,'approaching')},
                # Active hurricane
                None: {'if': equalRow(location,'none'),
                       True: setToConstantMatrix(phase,'none'),
                       False: setToConstantMatrix(phase,'active')}}
        world.setDynamics(phase,evolution,makeTree(tree))

        tree = makeTree({'if': equalFeatureRow(phase,makeFuture(phase)),
                         True: incrementMatrix(days,1),
                         False: setToConstantMatrix(days,0)})
        world.setDynamics(days,evolution,tree)

        if config.getint('Disaster','category_change') > 0:
            prob = likert[5][config.getint('Disaster','category_change')-1]
            subtree = {'if': equalRow(category,1),
                       True: {'distribution': [(noChangeMatrix(category),1.-prob),
                                               (setToConstantMatrix(category,2),prob)]},
                       False: {'if': equalRow(category,5),
                               True: {'distribution': [(setToConstantMatrix(category,4),prob),
                                                       (noChangeMatrix(category),1.-prob)]},
                               False: {'distribution': [(incrementMatrix(category,-1),prob/2.),
                                                        (noChangeMatrix(category),1.-prob),
                                                        (incrementMatrix(category,1),prob/2.)]}}}
        else:
            subtree = noChangeMatrix(category)
        tree = makeTree({'if': equalRow(makeFuture(phase),'approaching'),
                         True: {'if': equalRow(category,0),
                                # Generate a random cateogry
                                True: {'distribution': [(setToConstantMatrix(category,1),0.2),
                                                        (setToConstantMatrix(category,2),0.2),
                                                        (setToConstantMatrix(category,3),0.2),
                                                        (setToConstantMatrix(category,4),0.2),
                                                        (setToConstantMatrix(category,5),0.2)]},
                                False: subtree},
                         False: {'if': equalRow(makeFuture(phase),'active'),
                                 True: noChangeMatrix(category),
                                 False: setToConstantMatrix(category,0)}})
        world.setDynamics(category,evolution,tree)

        # For computing initial locations
        coastline = {r for r in regions if world.agents[r].x == 1}
        prob = 1./float(len(coastline))
        # For computing hurricane movement
        subtree = {'if': equalRow(location,regions[:]),
                   None: noChangeMatrix(location)}
        for index in range(len(regions)):
            region = world.agents[regions[index]]
            if config.getint('Disaster','stall_prob') > 0:
                stall = likert[5][config.getint('Disaster','stall_prob')-1]
                dist = [(setToConstantMatrix(location,region.name),stall),
                        (setToConstantMatrix(location,region.north),(1.-stall)/2.),
                        (setToConstantMatrix(location,region.east),(1.-stall)/2.)]
            else:
                dist = [(setToConstantMatrix(location,region.north),0.5),
                        (setToConstantMatrix(location,region.east),0.5)]
            subtree[index] = {'distribution': dist}
        tree = makeTree({'if': equalRow(makeFuture(phase),['approaching','active','none']),
                         0: {'if': equalRow(location,'none'),
                             # Generate initial location estimate
                             True: {'distribution': [(setToConstantMatrix(location,r),prob) \
                                                     for r in coastline]},
                             # No change?
                             False: noChangeMatrix(location)},
                         1: # Hurricane moving through regions
                         subtree,
                         2: # No hurricane
                         setToConstantMatrix(location,'none')})
        world.setDynamics(location,evolution,tree)

        # Effect of disaster on risk
        base_increase = likert[5][config.getint('Disaster','risk_impact')-1]
        base_decrease = likert[5][config.getint('Disaster','risk_decay')-1]
        for region in regions:
            risk = stateKey(region,'risk')
            distance = [abs(world.agents[center].x-world.agents[region].x) + \
                        abs(world.agents[center].y-world.agents[region].y) for center in regions]
            subtrees = {i: {'if': equalRow(category,list(range(1,6)))} for i in range(len(regions))}
            for i in range(len(regions)):
                subtrees[i].update({cat: approachMatrix(risk,base_increase*float(cat+1)/\
                                                        float(distance[i]+2),1.) \
                                    for cat in range(5)})         
            subtree = {'if': equalRow(makeFuture(location),regions[:]),
                       None: approachMatrix(risk,base_decrease,0.)}
            subtree.update({i: subtrees[i] for i in range(len(regions))})
            tree = makeTree({'if': equalRow(makeFuture(phase),'active'),
                             True: subtree, False: approachMatrix(risk,base_decrease,0.)})
            world.setDynamics(risk,evolution,tree)
        if config.getboolean('Shelter','exists'):
            for index in map(int,config.get('Shelter','region').split(',')):
                region = Region.nameString % (index)
                risk = stateKey(region,'shelterRisk')
                subtree = {'if': equalRow(category,list(range(1,6)))}
                for cat in range(5):
                    effect = base_increase*float(cat)
                    subtree[cat] = approachMatrix(risk,effect,1.)
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
