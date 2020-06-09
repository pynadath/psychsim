from psychsim.pwl import *
from psychsim.agent import Agent
from psychsim.domains.groundtruth.simulation.data import likert,logNode,logEdge
from psychsim.domains.groundtruth.simulation.region import Region

class Nature(Agent):
    def __init__(self,world,config):
        Agent.__init__(self,'Nature')
        world.addAgent(self)
        if world.diagram:
            world.diagram.setColor(self.name,'red')

        self.evolution = self.addAction({'verb': 'evolve'},codePtr=True)

        logNode('Nature\'s phase','Current hurricane state','String: either "none" / "approaching" / "active"')
        #//GT: node 7; 1 of 1; next 2 lines
        phase = world.defineState(self.name,'phase',list,['none','approaching','active'],codePtr=True)
        world.setFeature(phase,'none')

        logNode('Nature\'s days','Number of days of current Hurricane\'s phase','Nonnegative integer')
        #//GT: node 8; 1 of 1; next 2 lines
        days = world.defineState(self.name,'days',int,codePtr=True)
        world.setFeature(days,0)

        logNode('Nature\'s location','Projected landfall location (when over sea) or current center (when over land)','Region[01-16]')
        #//GT: node 9; 1 of 1; next 4 lines
        regions = sorted([name for name in self.world.agents
                          if isinstance(self.world.agents[name],Region)])
        location = world.defineState(self.name,'location',list,regions+['none'],codePtr=True)
        world.setFeature(location,'none')

        logNode('Nature\'s category','Hurricane severity','Integer in [0-5]')
        #//GT: node 10; 1 of 1; next 2 lines
        category = world.defineState(self.name,'category',int,codePtr=True)
        world.setFeature(category,0)
        
        # Phase dynamics
        logEdge('Nature\'s days','Nature\'s phase','often','There is a minimum number of days that must pass before a hurricane can change phase')
        #//GT: edge 1; from 8; to 7; 1 of 1; next 22 lines
        logEdge('Nature\'s location','Nature\'s phase','sometimes','Active hurricanes that move out of the area are no longer considered active and their phase goes to "none"')
        #//GT: edge 2; from 9; to 7; 1 of 1; next 20 lines
        prob = likert[5][config.getint('Disaster','phase_change_prob')-1]
        minDays = config.getint('Disaster','phase_min_days')
        tree = {'if': equalRow(phase,['none','approaching','active']),
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
                2: {'if': equalRow(location,'none'),
                       True: setToConstantMatrix(phase,'none'),
                       False: setToConstantMatrix(phase,'active')}}
        world.setDynamics(phase,self.evolution,makeTree(tree),codePtr=True)

        logEdge('Nature\'s phase','Nature\'s days','often','The number of days spent in the current phase goes to 0 if there\'s a phase change; otherwise it increases by 1')
        #//GT: edge 3; from 7; to 8; 1 of 1; next 4 lines
        tree = makeTree({'if': equalFeatureRow(phase,makeFuture(phase)),
                         True: incrementMatrix(days,1),
                         False: setToConstantMatrix(days,0)})
        world.setDynamics(days,self.evolution,tree,codePtr=True)

        logEdge('Nature\'s phase','Nature\'s category','sometimes','The hurricane\'s category can change when its phase is "approaching"')
        #//GT: edge 4; from 7; to 10; 1 of 1; next 25 lines
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
        tree = makeTree({'if': equalRow(makeFuture(phase),['approaching','active','none']),
                         0: {'if': equalRow(category,0),
                                # Generate a random cateogry
                                True: {'distribution': [(setToConstantMatrix(category,1),0.2),
                                                        (setToConstantMatrix(category,2),0.2),
                                                        (setToConstantMatrix(category,3),0.2),
                                                        (setToConstantMatrix(category,4),0.2),
                                                        (setToConstantMatrix(category,5),0.2)]},
                                False: subtree},
                         1: noChangeMatrix(category),
                         2: setToConstantMatrix(category,0)})
        world.setDynamics(category,self.evolution,tree,codePtr=True)

        # For computing initial locations
        coastline = {r for r in regions if world.agents[r].x == 1}
        prob = 1./float(len(coastline))
        # For computing hurricane movement
        logEdge('Nature\'s phase','Nature\'s location','sometimes','The hurricane moves differently depending on whether it is over land or over water')
        #//GT: edge 5; from 7; to 9; 1 of 1; next 28 lines
        subtree = {'if': equalRow(location,regions[:]),
                   None: noChangeMatrix(location)}
        northProb = likert[5][config.getint('Disaster','move_north')-1]
        for index in range(len(regions)):
            region = world.agents[regions[index]]
            if config.getint('Disaster','stall_prob') > 0:
                stall = likert[5][config.getint('Disaster','stall_prob')-1]
                dist = [(setToConstantMatrix(location,region.name),stall),
                        (setToConstantMatrix(location,region.north),(1.-stall)*northProb),
                        (setToConstantMatrix(location,region.east),(1.-stall)*(1.-northProb))]
            else:
                dist = [(setToConstantMatrix(location,region.north),northProb),
                        (setToConstantMatrix(location,region.east),1.-northProb)]
            subtree[index] = {'distribution': dist}
        tree = makeTree({'if': equalRow(makeFuture(phase),['approaching','active','none']),
                         0: {'if': equalRow(location,'none'),
                             # Generate initial location estimate
                             True: {'distribution': [(setToConstantMatrix(location,r),prob) \
                                                     for r in coastline]},
                             # No change?
                             False: noChangeMatrix(location)},
                         1: # Hurricane moving through regions
                         {'if': equalRow(phase,'approaching'),
                          True: noChangeMatrix(location),
                          False: subtree},
                         2: # No hurricane
                         setToConstantMatrix(location,'none')})
        world.setDynamics(location,self.evolution,tree,codePtr=True)

        # Effect of disaster on risk
        logEdge('ActorBeliefOfNature\'s category','ActorBeliefOfRegion\'s risk','often','Higher categories of hurricane mean higher increase in perception of risk to region')
        #//GT: edge 6; from 11; to 12; 1 of 1; next 24 lines
        logEdge('Nature\'s category','Region\'s risk','often','Higher categories of current hurricane mean higher increase in risk to region')
        #//GT: edge 7; from 10; to 1; 1 of 1; next 22 lines
        logEdge('Nature\'s location','Region\'s risk','often','A region\'s risk level increases more the closer it is to the hurricane\'s center')
        #//GT: edge 8; from 9; to 1; 1 of 1; next 20 lines
        logEdge('Nature\'s phase','Region\'s risk','often','A region\'s risk is affected by Nature variables only when phase is active')
        #//GT: edge 9; from 7; to 1; 1 of 1; next 18 lines
        base_increase = likert[5][config.getint('Disaster','risk_impact')-1]
        base_decrease = likert[5][config.getint('Disaster','risk_decay')-1]
        for region in regions:
            risk = stateKey(region,'risk')
            distance = [world.agents[region].distance(world.agents[center]) for center in regions]
            subtrees = {i: {'if': equalRow(makeFuture(category),list(range(1,6)))} for i in range(len(regions))}
            for i in range(len(regions)):
                subtrees[i].update({cat: approachMatrix(risk,base_increase*float(cat+1)/\
                                                        float(max(distance[i],1)),1.) \
                                    for cat in range(5)})
                subtrees[i][None] = approachMatrix(risk,base_decrease,world.agents[region].risk)
            subtree = {'if': equalRow(makeFuture(location),regions[:]),
                       None: approachMatrix(risk,base_decrease,world.agents[region].risk)}
            subtree.update({i: subtrees[i] for i in range(len(regions))})
            tree = makeTree({'if': equalRow(makeFuture(phase),'active'),
                             True: subtree,
                             False: approachMatrix(risk,base_decrease,world.agents[region].risk)})
            world.setDynamics(risk,self.evolution,tree,codePtr=True)

        if config.getint('Regions','economy_mean',fallback=0) > 0:
            delta = config.getint('Regions','economy_risk_delta',fallback=0)
            if delta > 0:
                logEdge('Region\'s risk','Region\'s economy','often','Excessive risk in a region causes its economy to decline')
                #
                for region in regions:
                    economy = stateKey(region,'economy')
                    tree = {'if': thresholdRow(makeFuture(economy),toLikert(config.getint('Regions','economy_risk_threshold',fallback=5)-1)),
                        True: approachMatrix(economy,toLikert(delta-1),0.),
                        False: approachMatrix(economy,toLikert(delta-1),world.agents[region].economy)}
                    world.setDynamics(economy,self.evolution,makeTree(tree),codePtr=True)

        if config.getboolean('Shelter','exists'):
            logEdge('ActorBeliefOfNature\'s category','ActorBeliefOfRegion\'s shelterRisk','often','Higher categories of hurricane mean higher increases in perception of risk at the shelters')
            #//GT: edge 10; from 11; to 13; 1 of 1; next 23 lines
            logEdge('Nature\'s category','Region\'s shelterRisk','often','Higher categories of hurricane mean higher increases in a shelter\'s risk')
            #//GT: edge 11; from 10; to 3; 1 of 1; next 21 lines
            logEdge('Nature\'s location','Region\'s shelterRisk','often','A shelter\'s risk level increases more the closer it is to the hurricane\'s center')
            #//GT: edge 12; from 9; to 3; 1 of 1; next 19 lines
            logEdge('Nature\'s phase','Region\'s shelterRisk','often','A shelter\'s risk is affected by Nature variables only when phase is active')
            #//GT: edge 13; from 7; to 3; 1 of 1; next 17 lines
            for index in map(int,config.get('Shelter','region').split(',')):
                region = Region.nameString % (index)
                if region in world.agents:
                    risk = stateKey(region,'shelterRisk')
                    subtree = {'if': equalRow(category,list(range(1,6)))}
                    for cat in range(5):
                        if config.getint('Shelter','category_effect',fallback=0) > 0:
                            effect = base_increase*float(cat)*likert[5][config.getint('Shelter','category_effect',fallback=0)-1]
                        else:
                            effect = base_increase#*float(cat)
                        subtree[cat] = approachMatrix(risk,effect,1.)
                    tree = makeTree({'if': equalRow(makeFuture(phase),'active'),
                                     True: {'if': equalRow(makeFuture(location),region),
                                            True: subtree,
                                            False: noChangeMatrix(risk)},
                                     False: approachMatrix(risk,base_decrease,0.)})
                    world.setDynamics(risk,self.evolution,tree,codePtr=True)

        self.setAttribute('static',True)
                                        
        if not config.getboolean('Simulation','graph',fallback=False):
            # Advance calendar after Nature moves
            tree = makeTree(incrementMatrix(stateKey(WORLD,'day'),1))
            world.setDynamics(stateKey(WORLD,'day'),self.evolution,tree,codePtr=True)

    def step(self,select,s=None,updateBeliefs=True):
        """
        Specialized and optimized stepping for hurricane
        """
        if s is None:
            s = self.world.state
        original = s.keys()
        assert len(self.actions) == 1
        evolve = next(iter(self.actions))
        if isinstance(s,KeyedVector):
            return self.world.step({self.name: evolve},s,select=select,keySubset=s.keys(),updateBeliefs=updateBeliefs)
        else:
            # Determine effects of hurricane
            order = [{k for k in keySet if k in s and (k in self.world.dynamics[evolve] or True in self.world.dynamics.get(k,{}))} 
                for keySet in self.world.dependency.getEvaluation()]
            order = [keySet for keySet in order if keySet]
            futures = set()
            # Project individual effects
            for i in range(len(order)):
                keySet = order[i]
                futures |= keySet
                for key in keySet:
                    try:
                        tree = self.world.dynamics[evolve][key]
                    except KeyError:
                        tree = self.world.dynamics[key][True]
                    if select is True:
                        tree = tree.sample()
                    elif select == 'max':
                        tree = tree.sample(True)
                    elif key in select:
                        tree = makeTree(setToConstantMatrix(key,select[key]))
#                        print(key,select[key])
#                        raise NotImplementedError
                    else:
                        # This feature not selected
                        tree = tree.sample()
    #                elif i < 2:
    #                    # Pre-determined hurricane
    #                    raise NotImplementedError
                    try:
                        s *= tree
                    except:
                        print(key)
                        print(s[key])
                        print(tree)
                        raise
            if isinstance(s,VectorDistributionSet):
                s.simpleRollback(futures)
            else:
                s.rollback(futures)
            # Update turn
            dynamics = self.world.deltaTurn(s,evolve)
            for key,tree in dynamics.items():
                assert len(tree) == 1
                s *= tree[0]
            if isinstance(s,VectorDistributionSet):
                s.simpleRollback(set(dynamics.keys()))
            else:
                s.rollback(set(dynamics.keys()))
            if updateBeliefs:
                # Update actor beliefs
                futures = set()
                actors = [name for name in self.world.agents.keys()
                                     if name[:5] == 'Actor' and modelKey(name) in s and self.world.agents[name].O is not True]
                for name in actors:
                    futures |= self.world.agents[name].projectObservations(s,evolve,True)
                    assert makeFuture(stateKey(name,'perceivedCategory')) in s
                    self.world.agents[name].updateBeliefs(s,evolve,debug=True)
                if isinstance(s,VectorDistributionSet):
                    s.simpleRollback(futures)
                else:
                    s.rollback(futures)
            assert original == s.keys()
            return s
