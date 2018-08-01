import random

from psychsim.probability import Distribution
from psychsim.pwl import *
from psychsim.reward import *
from psychsim.agent import Agent
from data import likert,toLikert,sampleNormal
from region import Region

class Actor(Agent):
    def __init__(self,number,world,config):
        Agent.__init__(self,'Actor%04d' % (number))
        world.addAgent(self)

        if number == 1:
            world.diagram.setColor(self.name,'gold')
        elif number == 2:
            world.diagram.setColor(self.name,'yellow')

        # States

        # Demographic info
        ethnic = world.defineState(self.name,'ethnicGroup',list,['majority','minority'])
        if random.random() > likert[5][config.getint('Actors','ethnic_majority')-1]:
            self.ethnicGroup = 'minority'
        else:
            self.ethnicGroup = 'majority'
        world.setFeature(ethnic,self.ethnicGroup)

        religion = world.defineState(self.name,'religion',list,['majority','minority','none'])
        if random.random() < likert[5][config.getint('Actors','religious_majority')-1]:
            self.religion = 'majority'
        else:
            atheistPct = config.getint('Actors','atheists') - 1
            if atheistPct and random.random() < likert[5][atheistPct]:
                self.religion = 'none'
            else:
                self.religion = 'minority'
        world.setFeature(religion,self.religion)

        gender = world.defineState(self.name,'gender',list,['male','female'])
        if random.random() > 0.5:
            self.gender = 'male'
        else:
            self.gender = 'female'
        world.setFeature(gender,self.gender)
        
        age = world.defineState(self.name,'age',int)
        ageMin = config.getint('Actors','age_min')
        ageMax = config.getint('Actors','age_max')
        self.age = random.randint(ageMin,ageMax)
        ageInterval = toLikert(float(self.age-ageMin)/float(ageMax-ageMin),5)
        world.setFeature(age,self.age)
        
        kids = world.defineState(self.name,'children',int,lo=0,hi=2)
        self.kids = random.randint(0,config.getint('Actors','children_max'))
        world.setFeature(kids,self.kids)

        job = world.defineState(self.name,'employed',bool)
        threshold = likert[5][config.getint('Actors','job_%s' % (self.ethnicGroup))-1]
        self.job = random.random() > threshold
        world.setFeature(job,self.job)
        
        # Psychological
        attachmentStyles = {'secure': likert[5][config.getint('Actors','attachment_secure')-1],
                            'anxious': likert[5][config.getint('Actors','attachment_anxious')-1]}
        attachmentStyles['avoidant'] = 1.-attachmentStyles['secure']-attachmentStyles['anxious']
        attachmentStyles = Distribution(attachmentStyles)
        attachment = world.defineState(self.name,'attachment',list,attachmentStyles.domain())
        self.attachment = attachmentStyles.sample()
        world.setFeature(attachment,self.attachment)

        regions = sorted([name for name in self.world.agents
                          if isinstance(self.world.agents[name],Region)])
        region = world.defineState(self.name,'region',list,regions)
        home = regions[(number-1)*config.getint('Regions','regions')/
                       config.getint('Actors','population')]
        world.setFeature(region,home)

        # For display use only
        tooClose = True
        xKey = world.defineState(self.name,'x',float)
        yKey = world.defineState(self.name,'y',float)
        while tooClose:
            x = random.random()
            y = random.random()
            for neighbor in [a for a  in world.agents.values() if isinstance(a,Actor) and \
                             not a.name == self.name and a.getState('location').first() == home]:
                if abs(neighbor.getState('x').first()-x)+abs(neighbor.getState('y').first()-y) < 0.1:
                    break
            else:
                tooClose = False
        world.setFeature(xKey,x)
        world.setFeature(yKey,y)
                             

        # Dynamic states
        locationSet = regions[:]
        locationSet.append('evacuated')
        if config.getboolean('Shelter','exists'):
            for index in config.get('Shelter','region').split(','):
                locationSet.append('shelter%s' % (index))
        location = world.defineState(self.name,'location',list,locationSet)
        world.setFeature(location,home)
        alive = world.defineState(self.name,'alive',bool)
        world.setFeature(alive,True)

        health = world.defineState(self.name,'health',float)
        mean = int(config.get('Actors','health_mean_age').split(',')[ageInterval-1])
        if self.ethnicGroup == 'minority':
            mean += config.getint('Actors','health_mean_ethnic_minority')
        sigma = config.getint('Actors','health_sigma')
        if sigma > 0:
            self.health = sampleNormal(mean,sigma)
        else:
            self.health = likert[5][mean-1]
        world.setFeature(health,self.health)

        wealth = world.defineState(self.name,'resources',float)
        mean = int(config.get('Actors','wealth_mean_age').split(',')[ageInterval-1])
        if self.ethnicGroup == 'minority':
            mean += config.getint('Actors','wealth_mean_ethnic_minority')
        if self.gender == 'female':
            mean += config.getint('Actors','wealth_mean_female')
        if self.religion == 'minority':
            mean += config.getint('Actors','wealth_mean_religious_minority')
        sigma = config.getint('Actors','wealth_sigma')
        if sigma > 0:
            self.wealth = sampleNormal(mean,sigma)
        else:
            self.wealth = likert[5][meanWealth-1]
        world.setFeature(wealth,self.wealth)

        risk = world.defineState(self.name,'risk',float)
        world.setFeature(risk,world.getState(home,'risk').expectation())

        mean = config.getint('Actors','grievance_ethnic_%s' % (self.ethnicGroup))
        mean += config.getint('Actors','grievance_religious_%s' % (self.religion))
        mean += config.getint('Actors','grievance_%s' % (self.gender))
        if self.wealth > 0.75:
            mean += config.getint('Actors','grievance_wealth_yes')
        else:
            mean += config.getint('Actors','grievance_wealth_no')
        sigma = config.getint('Actors','grievance_sigma')
        grievance = world.defineState(self.name,'grievance',float)
        if sigma > 0:
            self.grievance = sampleNormal(mean,sigma)
        else:
            self.grievance = likert[5][mean-1]
        world.setFeature(grievance,self.grievance)

        # Actions and Dynamics

        nop = self.addAction({'verb': 'doNothing'})
        goHomeFrom = []
        if config.getboolean('Shelter','exists'):
            # Go to shelter
            actShelter = {}
            for index in config.get('Shelter','region').split(','):
                shelter = 'shelter%s' % (index)
                goHomeFrom.append(shelter)
                tree = {'if': equalRow(stateKey('Nature','phase'),'none'),
                        True: False,
                        False: {'if': trueRow(alive),
                                True: {'if': equalRow(location,shelter),
                                       True: False, False: True}, False: False}}
                if config.getboolean('Actors','evacuation'):
                    tree = {'if': equalRow(location,'evacuated'),
                            True: False, False: tree}
                if config.getboolean('Actors','movement'):
                    # Actors move from region to region
                    tree = {'if': equalFeatureRow(location,Region.nameString % (int(index))),
                            True: tree, False: False}
                tree = makeTree(tree)
                actShelter[index] = self.addAction({'verb':'moveTo','object': shelter},
                                                   tree.desymbolize(world.symbols))
        if config.getboolean('Actors','evacuation'):
            # Evacuate city altogether
            tree = makeTree({'if': equalRow(stateKey('Nature','phase'),'none'),
                             True: False,
                             False: {'if': equalRow(location,'evacuated'),
                                     True: False,
                                     False: {'if': trueRow(alive),
                                             True: True, False: False}}})
            actEvacuate = self.addAction({'verb': 'evacuate'},tree.desymbolize(world.symbols))
            goHomeFrom.append('evacuated')
        if goHomeFrom:
            tree = makeTree({'if': equalRow(location,goHomeFrom),
                             True: True, False: False})
            goHome = self.addAction({'verb': 'moveTo','object': home},
                                    tree.desymbolize(world.symbols))
        if config.getboolean('Actors','prorisk'):
            # Prosocial behavior
            actGoodRisk = {}
            for region in regions:
                if config.getboolean('Actors','movement') or region == home:
                    tree = makeTree({'if': equalRow(location,region),
                                     True: {'if': trueRow(alive),True: True, False: False},
                                     False: False})
                    actGoodRisk[region] = self.addAction({'verb': 'decreaseRisk','object': region},
                                                         tree.desymbolize(world.symbols))
        if config.getboolean('Actors','proresources'):
            # Prosocial behavior
            actGoodResources = {}
            for region in regions:
                if config.getboolean('Actors','movement') or region == home:
                    tree = makeTree({'if': equalRow(location,region),
                                     True: {'if': trueRow(alive),True: True, False: False},
                                     False: False})
                    actGoodResources[region] = self.addAction({'verb': 'giveResources',
                                                               'object': region},
                                                              tree.desymbolize(world.symbols))
        if config.getboolean('Actors','antirisk'):
            # Antisocial behavior
            actBadRisk = {}
            for region in regions:
                if config.getboolean('Actors','movement') or region == home:
                    tree = makeTree({'if': equalRow(location,region),
                                     True: {'if': trueRow(alive),True: True, False: False},
                                     False: False})
                    actBadRisk[region] = self.addAction({'verb': 'increaseRisk','object': region},
                                                        tree.desymbolize(world.symbols))
        if config.getboolean('Actors','antiresources'):
            # Antisocial behavior
            actBadResources = {}
            for region in regions:
                if config.getboolean('Actors','movement') or region == home:
                    tree = makeTree({'if': equalRow(location,region),
                                     True: {'if': trueRow(alive),True: True, False: False},
                                     False: False})
                    actBadResources[region] = self.addAction({'verb': 'takeResources',
                                                              'object': region},
                                                        tree.desymbolize(world.symbols))
        regions = [n for n in self.world.agents.values()
                         if isinstance(n,Region)]
        if config.getboolean('Actors','movement'):
            actMove = {}
            for region in regions:
                cell = int(region.name[-2:])
                row = (cell-1) / 5
                col = (cell-1) % 5
                neighbors = []
                if row > 0:
                    neighbors.append('Region%02d' % ((row-1)*5+col+1))
                if row < len(regions)/5-1:
                    neighbors.append('Region%02d' % ((row+1)*5+col+1))
                if col > 0:
                    neighbors.append('Region%02d' % (cell-1))
                if col < 4:
                    neighbors.append('Region%02d' % (cell+1))
                tree = makeTree({'if': equalRow(location,neighbors),
                                 True: {'if': trueRow(alive),
                                        True: True, False: False}, False: False})
                actMove[region.name] = self.addAction({'verb': 'moveTo',
                                                            'object': region.name},
                                                            tree.desymbolize(world.symbols))

        # Information-seeking actions
        if config.getboolean('Actors','infoseek'):
            tree = makeTree({'if': trueRow(alive), True: True, False: False})
            self.addAction({'verb': 'infoSeek','object': home},tree.desymbolize(world.symbols))
                
        # Effect on location
        if config.getboolean('Shelter','exists'):
            for index,action in actShelter.items():
                tree = makeTree(setToConstantMatrix(location,'shelter%s' % (index)))
            world.setDynamics(location,action,tree)
        if config.getboolean('Actors','evacuation'):
            tree = makeTree(setToConstantMatrix(location,'evacuated'))
            world.setDynamics(location,actEvacuate,tree)
        if config.getboolean('Actors','movement'):
            for region in regions:
                tree = makeTree(setToConstantMatrix(location,region.name))
                world.setDynamics(location,actMove[region.name],tree)
        if goHomeFrom:
            tree = makeTree(setToConstantMatrix(location,home))
            world.setDynamics(location,goHome,tree)

        # Effect on my risk
        if config.getboolean('Actors','movement'):
            tree = noChangeMatrix(risk)
        else:
            tree = setToFeatureMatrix(risk,stateKey(home,'risk'))
        if config.getboolean('Actors','evacuation'):
            tree = {'if': equalRow(makeFuture(location),'evacuated'),
                    True: approachMatrix(risk,0.9,0.),
                    False:  tree}
        if config.getboolean('Shelter','exists'):
            for index in config.get('Shelter','region').split(','):
                tree = {'if': equalRow(makeFuture(location),'shelter%s' % (index)),
                    True: setToFeatureMatrix(risk,stateKey(Region.nameString % (int(index)),'risk')),
                    False: tree}
        if config.getboolean('Actors','movement'):
            for region in regions:
                tree = {'if': equalRow(makeFuture(location),region.name),
                        True: setToFeatureMatrix(risk,stateKey(region.name,'risk')),
                        False: tree}
        tree = {'if': trueRow(alive),True: tree, False: setToConstantMatrix(risk,0.)}
        world.setDynamics(risk,True,makeTree(tree))
        
        # Effect on my health
        impact = likert[5][config.getint('Actors','health_impact')-1]
        tree = {'if': thresholdRow(makeFuture(risk),likert[5][0]),
                True: None,
                False: approachMatrix(health,impact,self.health)}
        subtree = tree
        for level in range(1,4):
            value = likert[5][level-1]
            dist = [(approachMatrix(health,impact,0.),value),
                    (approachMatrix(health,impact,self.health),1.-value)]
            subtree[True] = {'if': thresholdRow(makeFuture(risk),likert[5][level]),
                             True: None,
                             False: {'distribution': dist}}
            subtree = subtree[True]
        subtree[True] = {'distribution': [(approachMatrix(health,impact,0.),likert[5][3]),
                                          (approachMatrix(health,impact,self.health),1.-likert[5][3])]}
        tree = makeTree({'if': trueRow(alive),
                         True: tree, False: setToConstantMatrix(health,0.)})
        world.setDynamics(health,True,tree)

        if config.getint('Actors','children_max') > 0:
            # Effect on kids' health
            tree = {'if': thresholdRow(makeFuture(risk),likert[5][0]),
                    True: None,
                    False: approachMatrix(kids,impact,self.health)}
            subtree = tree
            for level in range(1,4):
                value = likert[5][level-1]
                dist = [(approachMatrix(kids,impact,0.),value),
                        (approachMatrix(kids,impact,self.health),1.-value)]
                subtree[True] = {'if': thresholdRow(makeFuture(risk),likert[5][level]),
                                 True: None,
                                 False: {'distribution': dist}}
                subtree = subtree[True]
            subtree[True] = {'distribution': [(approachMatrix(kids,impact,0.),likert[5][3]),
                                              (approachMatrix(kids,impact,self.health),1.-likert[5][3])]}
            tree = makeTree({'if': trueRow(alive),
                             True: tree, False: setToConstantMatrix(kids,0.)})
            world.setDynamics(kids,True,tree)

        # Effect on life
        tree = makeTree({'if': trueRow(alive),
                         True: {'if': thresholdRow(makeFuture(health),
                                                   config.getfloat('Actors','life_threshold')),
                                True: setTrueMatrix(alive),
                                False: setFalseMatrix(alive)},
                         False: noChangeMatrix(alive)})
        world.setDynamics(alive,True,tree)
        
        # Effect on wealth
        if config.getboolean('Actors','evacuation'):
            cost = config.getint('Actors','evacuation_cost')
            if cost > 0:
                cost = likert[5][cost]
                tree = makeTree({'if': thresholdRow(wealth,cost),
                                 True: incrementMatrix(wealth,-cost),
                                 False: setToConstantMatrix(wealth,0.)})
                world.setDynamics(wealth,actEvacuate,tree)
            if config.getint('Actors','evacuation_unemployment') > 0:
                # Might lose job
                prob = likert[5][config.getint('Actors','evacuation_unemployment')-1]
                tree = makeTree({'if': trueRow(alive),
                                 True: {'if': trueRow(job),
                                        True: {'distribution': [(noChangeMatrix(job),1.-prob),
                                                                (setFalseMatrix(job),prob)]},
                                        False: noChangeMatrix(job)},
                                 False: noChangeMatrix(job)})

        if config.getboolean('Actors','prorisk'):
            # Effect of doing good
            benefit = likert[5][config.getint('Actors','prorisk_benefit')-1]
            for region,action in actGoodRisk.items():
                key = stateKey(region,'risk')
                tree = makeTree(approachMatrix(key,benefit,0.))
                world.setDynamics(key,action,tree)
            cost = config.getint('Actors','prorisk_cost_risk')
            if cost > 0:
                for region,action in actGoodRisk.items():
                    tree = makeTree(approachMatrix(risk,likert[5][cost-1],1.))
                    world.setDynamics(risk,action,tree)
        if config.getboolean('Actors','proresources'):
            # Effect of doing good
            benefit = likert[5][config.getint('Actors','proresources_benefit')-1]
            for region,action in actGoodResources.items():
                key = stateKey(region,'resources')
                tree = makeTree(approachMatrix(key,benefit,0.))
                world.setDynamics(key,action,tree)
            cost = config.getint('Actors','proresources_cost_risk')
            if cost > 0:
                for region,action in actGoodResources.items():
                    tree = makeTree(approachMatrix(risk,likert[5][cost-1],1.))
                    world.setDynamics(risk,action,tree)
        if config.getboolean('Actors','antiresources'):
            # Effect of doing bad
            benefit = likert[5][config.getint('Actors','antiresources_benefit')-1]
            for region,action in actBadResources.items():
                tree = makeTree(incrementMatrix(wealth,benefit))
                world.setDynamics(wealth,action,tree)
            cost = config.getint('Actors','antiresources_cost_risk')
            if cost > 0:
                for region,action in actBadResources.items():
                    tree = makeTree({'if': equalRow(stateKey('Nature','phase'),'none'),
                                     True: approachMatrix(risk,likert[5][3],1.),
                                     False: approachMatrix(risk,likert[5][cost-1],1.)})
                    world.setDynamics(risk,action,tree)
        if config.getboolean('Actors','antirisk'):
            # Effect of doing bad
            benefit = likert[5][config.getint('Actors','antirisk_benefit')-1]
            for region,action in actBadRisk.items():
                key = stateKey(region,'risk')
                tree = makeTree(approachMatrix(key,benefit,1.))
                world.setDynamics(key,action,tree)
            cost = config.getint('Actors','antirisk_cost_risk')
            if cost > 0:
                for region,action in actBadRisk.items():
                    tree = makeTree({'if': equalRow(stateKey('Nature','phase'),'none'),
                                     True: approachMatrix(risk,likert[5][3],1.),
                                     False: approachMatrix(risk,likert[5][cost-1],1.)})
                    world.setDynamics(risk,action,tree)
                
        # Reward
        mean = config.getint('Actors','reward_health')
        if mean > 0:
            self.setReward(maximizeFeature(health,self.name),likert[5][mean-1])
        mean = config.getint('Actors','reward_wealth')
        if mean > 0:
            self.setReward(maximizeFeature(wealth,self.name),likert[5][mean-1])
        if self.kids > 0:
            mean = config.getint('Actors','reward_kids')
            if mean > 0:
                self.setReward(maximizeFeature(kids,self.name),likert[5][mean-1])
        if config.getboolean('Actors','beliefs'):
            # Observations
            omega = self.defineObservation('phase',domain=list,
                                           lo=self.world.variables['Nature\'s phase']['elements'])
            self.setO('phase',None,
                      makeTree(setToFeatureMatrix(omega,makeFuture(stateKey('Nature','phase')))))
            self.setState('phase','none')
            omega = self.defineObservation('center',domain=list,
                                           lo=self.world.variables['Nature\'s location']['elements'])
            self.setO('center',None,
                      makeTree(setToFeatureMatrix(omega,makeFuture(stateKey('Nature','location')))))
            self.setState('center','none')
            omega = self.defineObservation('category',domain=int)
            self.setO('category',None,
                      makeTree(setToFeatureMatrix(omega,makeFuture(stateKey('Nature','category')))))
            self.setState('category',0)
            omega = self.defineObservation('perceivedHealth')
            self.setO('perceivedHealth',None,
                      makeTree(setToFeatureMatrix(omega,makeFuture(stateKey(self.name,'health')))))
            self.setState('perceivedHealth',self.health)
            omega = self.defineObservation('perceivedKids',domain=int,lo=0,hi=2)
            self.setO('perceivedKids',None,
                      makeTree(setToFeatureMatrix(omega,makeFuture(stateKey(self.name,'children')))))
            self.setState('perceivedKids',self.kids)
        # Decision-making parameters
        self.setAttribute('horizon',config.getint('Actors','horizon'))
        #self.setAttribute('selection','distribution')
        #self.setAttribute('rationality',1.)

    def makeFriend(self,friend,config):
        key = binaryKey(self.name,friend.name,'friendOf')
        if not key in self.world.variables:
            self.world.defineRelation(self.name,friend.name,'friendOf',bool)
        self.world.setFeature(key,True)
        if config.getboolean('Actors','messages'):
            tree = makeTree({'if': trueRow(stateKey(self.name,'alive')),
                             True: True, False: False})
            msg = self.addAction({'verb': 'message','object': friend.name},
                                 tree.desymbolize(self.world.symbols))

    def _initializeRelations(self,config):
        friends = set()
        population = {a for a in self.world.agents.values() if isinstance(a,self.__class__)}
        friendMax = config.getint('Actors','friends')
        myHome = self.world.getState(self.name,'region').first()
        neighbors = {a.name for a in population if a.name != self.name and \
                     self.world.getState(a.name,'region').first() == myHome}
        if friendMax > 0:
            # Social network
            friendCount = {}
            for other in population:
                if other.name != self.name:
                    friendship = binaryKey(self.name,other.name,'friendOf')
                    if not friendship in self.world.variables:
                        self.world.defineRelation(self.name,other.name,'friendOf',bool)
                    self.world.setFeature(friendship,False)
                    friendCount[other.name] = 0
                    if other.name in self.world.relations:
                        for key in self.world.relations[other.name]:
                            relation = key2relation(key)
                            if relation['relation'] == 'friendOf':
                                if self.world.getFeature(key).first():
                                    # This person has a friend
                                    friendCount[other.name] += 1
                                    if friendCount[other.name] == friendMax:
                                        del friendCount[other.name]
                                        break
            for count in range(friendMax):
                friend = random.choice(list(set(friendCount.keys())))
                self.makeFriend(self.world.agents[friend],config)
                self.world.agents[friend].makeFriend(self,config)
                if friendCount[friend] == friendMax - 1:
                    del friendCount[friend]
                else:
                    friendCount[friend] += 1

        for other in population:
            if self.name == other.name:
                continue
            Rneighbors = config.getint('Actors','altruism_neighbors')
            Rfriends = config.getint('Actors','altruism_friends')
            if Rneighbors > 0 and other in neighbors:
                self.setReward(maximizeFeature(stateKey(other.name,'health'),self.name),
                               likert[5][Rneighbors-1]/float(len(neighbors)))
            elif config.getint('Actors','friends') > 0 and Rfriends > 0 and \
                 self.world.getFeature(binaryKey(self.name,other.name,'friendOf')).first():
                self.setReward(maximizeFeature(stateKey(other.name,'health'),self.name),
                               likert[5][Rfriends-1]/float(friendMax))
        
    def _initializeBeliefs(self,config):
        # Beliefs
        friends = set()
        population = {a for a in self.world.agents.values() if isinstance(a,self.__class__)}
        myHome = self.world.getState(self.name,'region').first()
        neighbors = {a.name for a in population if a.name != self.name and \
                     self.world.getState(a.name,'region').first() == myHome}

        beliefs = self.resetBelief()
        for other in population:
            if other.name != self.name:
                if config.getint('Actors','altruism_neighbors') > 0 and \
                   other.name in neighbors:
                    # I care about my neighbors, so I can't ignore them
                    continue
#                 if world.getFeature(binaryKey(self.name,other.name,'friendOf')).first():
#                     continue
                self.ignore(other.name,'%s0' % (self.name))
