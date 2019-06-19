import inspect
import logging
import random
import sys

from psychsim.probability import Distribution
from psychsim.pwl import *
from psychsim.action import *
from psychsim.reward import *
from psychsim.agent import Agent
from psychsim.domains.groundtruth.simulation.data import likert,toLikert,sampleNormal
from psychsim.domains.groundtruth.simulation.region import Region


if (sys.version_info > (3, 0)):
    import configparser
else:
    import ConfigParser as configparser

class Actor(Agent):
    def __init__(self,number,world,config):
        if config.getint('Actors','population') == 1:
            name = 'Actor'
        else:
            name = 'Actor%04d' % (number)
        Agent.__init__(self,name)
        world.addAgent(self)

        if world.diagram:
            if number == 1:
                world.diagram.setColor(self.name,'gold')
            elif number == 2:
                world.diagram.setColor(self.name,'yellow')

        if config.getint('Simulation','phase',fallback=1) > 1:
            self.demographics = {}

        # Decision-making parameters
        minH = config.getint('Actors','min_horizon')
        maxH = config.getint('Actors','max_horizon')
        if minH == maxH:
            self.horizon = minH
        else:
            self.horizon = random.randint(minH,maxH)
        self.setAttribute('horizon',self.horizon)
        #self.setAttribute('selection','distribution')
        #self.setAttribute('rationality',1.)

        self.friends = set()
        self.groups = set()

        # States

        # Demographic info
        if random.random() > likert[5][config.getint('Actors','ethnic_majority')-1]:
            self.demographics['ethnicGroup'] = 'minority'
        else:
            self.demographics['ethnicGroup'] = 'majority'
        if config.getint('Simulation','phase',fallback=1) == 1:
            ethnic = world.defineState(self.name,'ethnicGroup',list,['majority','minority'],
                                       description='Ethnicity of actor',codePtr=True)
            world.setFeature(ethnic,self.demographics['ethnicGroup'])

        if random.random() < likert[5][config.getint('Actors','religious_majority')-1]:
            self.demographics['religion'] = 'majority'
        else:
            atheistPct = config.getint('Actors','atheists')
            if atheistPct and random.random() < likert[5][atheistPct-1]:
                self.demographics['religion'] = 'none'
            else:
                self.demographics['religion'] = 'minority'
        if config.getint('Simulation','phase',fallback=1) == 1:
            religion = world.defineState(self.name,'religion',list,['majority','minority','none'],
                                         description='Religious affiliation of actor',codePtr=True)
            world.setFeature(religion,self.demographics['religion'])

        if random.random() < config.getfloat('Actors','male_prob'):
            self.demographics['gender'] = 'male'
        else:
            self.demographics['gender'] = 'female'
        if config.getint('Simulation','phase',fallback=1) == 1:
            gender = world.defineState(self.name,'gender',list,['male','female'],codePtr=True)
            world.setFeature(gender,self.demographics['gender'])

        # Section 2.1
        ageMin = config.getint('Actors','age_min')
        ageMax = config.getint('Actors','age_max')
        self.demographics['age'] = random.randint(ageMin,ageMax)
        ageInterval = toLikert(float(self.demographics['age']-ageMin)/float(ageMax-ageMin),5)
        if config.getint('Simulation','phase',fallback=1) == 1:
            age = world.defineState(self.name,'age',int,codePtr=True)
            world.setFeature(age,self.demographics['age'])

        maxKids = config.getint('Actors','children_max')
        if self.demographics['age'] > config.getint('Actors','parent_max_age'):
            self.demographics['kids'] = 0
        else:
            self.demographics['kids'] = random.randint(0,maxKids)
        if config.getint('Simulation','phase',fallback=1) == 1:
            kids = world.defineState(self.name,'children',float,lo=0,hi=float(maxKids),
                                     description='Number of children',codePtr=True)
            world.setFeature(kids,self.demographics['kids'])

        job = world.defineState(self.name,'employed',bool,description='Has a full-time job',
                                codePtr=True)
        threshold = likert[5][config.getint('Actors','job_%s' % (self.demographics['ethnicGroup']))-1]
        self.demographics['job'] = random.random() < threshold
        world.setFeature(job,self.demographics['job'])

        threshold = config.getint('Actors','pet_prob')
        if threshold > 0:
            pet = world.defineState(self.name,'pet',bool,description='Owns a pet',codePtr=True)
            self.demographics['pet'] = random.random() < likert[5][threshold-1]
            world.setFeature(pet,self.demographics['pet'])
        else:
            self.demographics['pet'] = False

        if config.getint('Actors','married',fallback=0) > 0:
            threshold = likert[5][config.getint('Actors','married')-1]
            if random.random() < threshold:
                key = binaryKey(self.name,self.name,'marriedTo')
                self.world.defineRelation(self.name,self.name,'marriedTo',bool,codePtr=True)
                self.world.setFeature(key,True)

        # Psychological
        if config.getboolean('Actors','attachment'):
            attachmentStyles = {'secure': likert[5][config.getint('Actors','attachment_secure')-1],
                                'anxious': likert[5][config.getint('Actors','attachment_anxious')-1]}
            attachmentStyles['avoidant'] = 1.-attachmentStyles['secure']-attachmentStyles['anxious']
            attachmentStyles = Distribution(attachmentStyles)
            attachment = world.defineState(self.name,'attachment',list,
                                           list(attachmentStyles.domain()),
                                           description='Attachment style',codePtr=True)
            self.attachment = attachmentStyles.sample()
            world.setFeature(attachment,self.attachment)
        if config.getboolean('Actors','appraisal'):
            # Coping Style
            copingStyles = {'none': 1.}
            if config.getint('Actors','coping_emotion') > 0:
                copingStyles['emotion'] = likert[5][config.getint('Actors','coping_emotion')-1]
            if config.getint('Actors','coping_problem') > 0:
                copingStyles['problem'] = likert[5][config.getint('Actors','coping_problem')-1]
            copingStyles = Distribution(copingStyles)
            coping = world.defineState(self.name,'coping',list,['none','emotion','problem'],
                                       description='Coping style, whether biased toward emotion- or problem-directed decision-making',
                                       codePtr=True)
            self.coping = copingStyles.sample()
            world.setFeature(coping,self.coping)
            # Control bias
            controlStyles = {'none': 1.}
            if config.getint('Actors','control_hi') > 0:
                controlStyles['hiEfficacy'] = likert[5][config.getint('Actors','control_hi')-1]
                controlStyles['none'] -= controlStyles['hiEfficacy']
            if config.getint('Actors','control_lo') > 0:
                controlStyles['loEfficacy'] = likert[5][config.getint('Actors','control_lo')-1]
                controlStyles['none'] -= controlStyles['loEfficacy']
            controlStyles = Distribution(controlStyles)
            control = world.defineState(self.name,'control',list,['none','hiEfficacy','loEfficacy'],
                                        description='Control style, whether low or high self-efficacy',
                                        codePtr=True)
            self.control = controlStyles.sample()
            world.setFeature(control,self.control)
            # Causal attribution
            attributionStyles = {'none': 1.}
            if config.getint('Actors','attribution_in') > 0:
                attributionStyles['internal'] = likert[5][config.getint('Actors','attribution_in')-1]
                attributionStyles['none'] -= attributionStyles['internal']
            if config.getint('Actors','attribution_ex') > 0:
                attributionStyles['external'] = likert[5][config.getint('Actors','attribution_ex')-1]
                attributionStyles['none'] -= attributionStyles['external']
            attributionStyles = Distribution(attributionStyles)
            attribution = world.defineState(self.name,'attribution',list,['none','internal',
                                                                          'external'],
                                            description='Causal attribution style, whether attributing events to internal or external causes',
                                            codePtr=True)
            self.attribution = attributionStyles.sample()
            world.setFeature(attribution,self.attribution)

        regions = sorted([name for name in self.world.agents
                          if isinstance(self.world.agents[name],Region)])
        if config.getboolean('Regions','random_population'):
            self.demographics['home'] = random.choice(regions)
        else:
            index = int((number-1)*config.getint('Regions','regions')/config.getint('Actors','population'))
            self.demographics['home'] = regions[index]
        if config.getint('Simulation','phase',fallback=1) == 1:
            region = world.defineState(self.name,'region',list,regions,description='Region of residence',
                                       codePtr=True)
            world.setFeature(region,self.demographics['home'])
        neighbors = [a for a  in world.agents.values() if isinstance(a,Actor) and \
                     not a.name == self.name and a.getState('location').first() == self.demographics['home']]

        if config.getboolean('Simulation','visualize'):
            # For display use only
            tooClose = True
            xKey = world.defineState(self.name,'x',float,
                                     description='Representation of residence\'s longitude',codePtr=True)
            yKey = world.defineState(self.name,'y',float,
                                     description='Representation of residence\'s latitude',codePtr=True)
            while tooClose:
                x = random.random()
                y = random.random()
                for neighbor in neighbors:
                    if abs(neighbor.getState('x').first()-x)+abs(neighbor.getState('y').first()-y) < 0.05:
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
                region = Region.nameString % (int(index))
                if region in self.world.agents:
                    locationSet.append('shelter%s' % (index))
        location = world.defineState(self.name,'location',list,locationSet,
                                     description='Current location',codePtr=True)
        world.setFeature(location,self.demographics['home'])
        # Section 2.2
        alive = world.defineState(self.name,'alive',bool,codePtr=True)
        world.setFeature(alive,True)

        health = world.defineState(self.name,'health',float,
                                   description='Current level of physical wellbeing',codePtr=True)
        try:
            self.health = float(config.get('Actors','health_value_age').split(',')[ageInterval-1])
        except configparser.NoOptionError:
            mean = int(config.get('Actors','health_mean_age').split(',')[ageInterval-1])
            if self.demographics['ethnicGroup'] == 'minority':
                mean += config.getint('Actors','health_mean_ethnic_minority')
            mean = max(1,mean)
            sigma = config.getint('Actors','health_sigma')
            if sigma > 0:
                self.health = sampleNormal(mean,sigma)
            else:
                self.health = likert[5][mean-1]
        world.setFeature(health,self.health)
#        healthMax = world.defineState(self.name,'healthMax',float,
#                                      description='Maximum level of physical wellbeing',codePtr=True)
#        world.setFeature(healthMax,self.health)

        if self.demographics['kids'] > 0:
            kidHealth = world.defineState(self.name,'childrenHealth',float,
                                          description='Current level of children\'s physical wellbeing',
                                          codePtr=True)
            world.setFeature(kidHealth,self.health)

        wealth = world.defineState(self.name,'resources',float,codePtr=True,
                                   description='Material resources (wealth) currently owned')
        try:
            self.demographics['wealth'] = float(config.get('Actors','wealth_value_age').split(',')[ageInterval-1])
        except configparser.NoOptionError:
            mean = int(config.get('Actors','wealth_mean_age').split(',')[ageInterval-1])
            if self.demographics['ethnicGroup'] == 'minority':
                mean += config.getint('Actors','wealth_mean_ethnic_minority')
            if self.demographics['gender'] == 'female':
                mean += config.getint('Actors','wealth_mean_female')
            if self.demographics['religion'] == 'minority':
                mean += config.getint('Actors','wealth_mean_religious_minority')
            mean = max(1,mean)
            sigma = config.getint('Actors','wealth_sigma')
            if sigma > 0:
                self.demographics['wealth'] = sampleNormal(mean,sigma)
            else:
                self.demographics['wealth'] = likert[5][mean-1]
        world.setFeature(wealth,self.demographics['wealth'])

        risk = world.defineState(self.name,'risk',float,codePtr=True,
                                 description='Current level of risk from hurricane')
        world.setFeature(risk,world.getState(self.demographics['home'],'risk').expectation())

        if config.getboolean('System','system'):
            mean = config.getint('Actors','grievance_ethnic_%s' % (self.demographics['ethnicGroup']))
            mean += config.getint('Actors','grievance_religious_%s' % (self.demographics['religion']))
            mean += config.getint('Actors','grievance_%s' % (self.demographics['gender']))
            if self.demographics['wealth'] > likert[5][config.getint('Actors','grievance_wealth_threshold')-1]:
                mean += config.getint('Actors','grievance_wealth_yes')
            else:
                mean += config.getint('Actors','grievance_wealth_no')
            sigma = config.getint('Actors','grievance_sigma')
            grievance = world.defineState(self.name,'grievance',float,codePtr=True,
                                          description='Current level of grievance felt toward system')
            if sigma > 0:
                self.grievance = sampleNormal(mean,sigma)
            else:
                self.grievance = likert[5][mean-1]
            world.setFeature(grievance,self.grievance)

        # Actions and Dynamics

        evolve = ActionSet([Action({'subject': 'Nature','verb': 'evolve'})])
        self.nop = self.addAction({'verb': 'stayInLocation'},codePtr=True,
                                  description='Actor does not move from current location, nor perform any pro/antisocial behaviors')
        goHomeFrom = set()
        if config.getboolean('Shelter','exists'):
            # Go to shelter
            shelters = config.get('Shelter','region').split(',')
            actShelter = {}
            distances = {}
            for index in shelters:
                region = Region.nameString % (int(index))
                if region in self.world.agents:
                    distances[index] = self.world.agents[region].distance(self.demographics['home'])
            shortest = min(distances.values())
            closest = [index for index in distances if distances[index] == shortest]
            for index in closest:
                shelter = 'shelter%s' % (index)
                region = Region.nameString % (int(index))
                goHomeFrom.add(shelter)
                tree = {'if': equalRow(stateKey('Nature','phase'),'none'),
                        True: False,
                        False: {'if': trueRow(alive),
                                True: {'if': equalRow(location,shelter),
                                       True: False,
                                       False: True},
                                False: False}}
#                if world.getState(region,'shelterCapacity').first() > 0:
#                    tree = {'if': greaterThanRow(stateKey(region,'shelterCapacity'),
#                                                 stateKey(region,'shelterOccupancy')),
#                            True: tree, False: False}
                if config.getboolean('Actors','movement'):
                    # Actors move from region to region
                    tree = {'if': equalFeatureRow(location,Region.nameString % (int(index))),
                            True: tree, False: False}
                    # TODO: Add actions for movement here
#                elif config.getboolean('Actors','evacuation'):
#                    tree = {'if': equalRow(location,'evacuated'),
#                            True: False, False: tree}
                tree = makeTree(tree)
                actShelter[index] = self.addAction({'verb':'moveTo','object': shelter},
                                                   tree.desymbolize(world.symbols),
                                                   'Move myself and family to the shelter in %s' \
                                                   % (region),True)
        if config.getboolean('Actors','evacuation'):
            # Evacuate city altogether
            tree = makeTree({'if': equalRow(stateKey('Nature','phase'),'none'),
                             True: False,
                             False: {'if': equalRow(location,'evacuated'),
                                     True: False,
                                     False: {'if': trueRow(alive),
                                             True: True, False: False}}})
            actEvacuate = self.addAction({'verb': 'evacuate'},tree.desymbolize(world.symbols),
                                         'Evacuate the city at least temporarily',True)
            goHomeFrom.add('evacuated')
        if goHomeFrom:
            tree = makeTree({'if': equalRow(location,goHomeFrom),
                             True: True, False: False})
            goHome = self.addAction({'verb': 'moveTo','object': self.demographics['home']},
                                    tree.desymbolize(world.symbols),
                                    'Return home',True)
        if config.getboolean('Actors','prorisk'):
            # Prosocial behavior
            actGoodRisk = {}
            for region in regions:
                if config.getboolean('Actors','movement') or region == self.demographics['home']:
                    tree = makeTree({'if': equalRow(location,region),
                                     True: {'if': trueRow(alive),True: True, False: False},
                                     False: False})
                    actGoodRisk[region] = self.addAction({'verb': 'decreaseRisk','object': region},
                                                         tree.desymbolize(world.symbols),
                                                         'Perform prosocial behaviors to reduce the danger posed by the hurricane in a given region',True)
        if config.getboolean('Actors','proresources'):
            # Prosocial behavior
            actGoodResources = {}
            for region in regions:
                if config.getboolean('Actors','movement') or region == self.demographics['home']:
                    tree = makeTree({'if': equalRow(location,region),
                                     True: {'if': trueRow(alive),True: True, False: False},
                                     False: False})
                    actGoodResources[region] = self.addAction({'verb': 'giveResources',
                                                               'object': region},
                                                              tree.desymbolize(world.symbols),
                                                              'Perform prosocial behaviors to gather and donate resources to the people of a given region',True)
        if config.getboolean('Actors','antirisk'):
            # Antisocial behavior
            actBadRisk = {}
            for region in regions:
                if config.getboolean('Actors','movement') or region == self.demographics['home']:
                    tree = makeTree({'if': equalRow(location,region),
                                     True: {'if': trueRow(alive),True: True, False: False},
                                     False: False})
                    actBadRisk[region] = self.addAction({'verb': 'increaseRisk','object': region},
                                                        tree.desymbolize(world.symbols),
                                                        'Perform antisocial behaviors that increase the danger faced by people in a given region',True)
        if config.getboolean('Actors','antiresources'):
            # Antisocial behavior
            actBadResources = {}
            for region in regions:
                if config.getboolean('Actors','movement') or region == self.demographics['home']:
                    tree = makeTree({'if': equalRow(location,region),
                                     True: {'if': trueRow(alive),True: True, False: False},
                                     False: False})
                    actBadResources[region] = self.addAction({'verb': 'takeResources',
                                                              'object': region},
                                                             tree.desymbolize(world.symbols),
                                                             'Perform antisocial behaviors that gain resources personally at the expense of people in a given region',True)
        regions = [n for n in self.world.agents.values()
                         if isinstance(n,Region)]
        if config.getboolean('Actors','movement'):
            actMove = {}
            for region in regions:
                cell = int(region.name[-2:])
                row = (cell-1) / 5
                col = (cell-1) % 5
                bordering = set()
                if row > 0:
                    bordering.add('Region%02d' % ((row-1)*5+col+1))
                if row < len(regions)/5-1:
                    bordering.add('Region%02d' % ((row+1)*5+col+1))
                if col > 0:
                    bordering.add('Region%02d' % (cell-1))
                if col < 4:
                    bordering.add('Region%02d' % (cell+1))
                tree = makeTree({'if': equalRow(location,bordering),
                                 True: {'if': trueRow(alive),
                                        True: True, False: False}, False: False})
                actMove[region.name] = self.addAction({'verb': 'moveTo',
                                                       'object': region.name},
                                                      tree.desymbolize(world.symbols),
                                                      codePtr=True)

        # Information-seeking actions
        if config.getboolean('Actors','infoseek'):
            tree = makeTree({'if': trueRow(alive), True: True, False: False})
            infoseek = self.addAction({'verb': 'seekInfoReHurricane'},
                                      tree.desymbolize(world.symbols),
                                      'Seek out additional information about the hurricane risk',True)
                
        # Effect on location
        if config.getboolean('Shelter','exists'):
            for index,action in actShelter.items():
                tree = makeTree(setToConstantMatrix(location,'shelter%s' % (index)))
            world.setDynamics(location,action,tree,codePtr=True)
        if config.getboolean('Actors','evacuation'):
            tree = makeTree(setToConstantMatrix(location,'evacuated'))
            world.setDynamics(location,actEvacuate,tree,codePtr=True)
        if config.getboolean('Actors','movement'):
            for region in regions:
                tree = makeTree(setToConstantMatrix(location,region.name))
                world.setDynamics(location,actMove[region.name],tree,codePtr=True)
        if goHomeFrom:
            tree = makeTree(setToConstantMatrix(location,self.demographics['home']))
            world.setDynamics(location,goHome,tree,codePtr=True)

        # Effect on my risk
        if config.getboolean('Actors','movement'):
            tree = noChangeMatrix(risk)
        else:
            tree = setToFeatureMatrix(risk,makeFuture(stateKey(self.demographics['home'],'risk')))
        if config.getboolean('Actors','evacuation'):
            tree = {'if': equalRow(makeFuture(location),'evacuated'),
                    True: approachMatrix(risk,0.9,0.),
                    False:  tree}
        if config.getboolean('Shelter','exists'):
            for index in actShelter:
                region = Region.nameString % (int(index))
                tree = {'if': equalRow(makeFuture(location),'shelter%s' % (index)),
                        True: setToFeatureMatrix(risk,stateKey(region,'shelterRisk')),
                        False: tree}
        if config.getboolean('Actors','movement'):
            for region in regions:
                tree = {'if': equalRow(makeFuture(location),region.name),
                        True: setToFeatureMatrix(risk,stateKey(region.name,'risk')),
                        False: tree}
        tree = {'if': trueRow(alive),True: tree, False: setToConstantMatrix(risk,0.)}
        world.setDynamics(risk,True,makeTree(tree),codePtr=True)
        
        # Effect on my health
        impact = likert[5][config.getint('Actors','health_impact')-1]
        tree = {'if': thresholdRow(makeFuture(risk),likert[5][:]),
                0: approachMatrix(health,impact,self.health)}
        for level in range(1,6):
            value = likert[5][level-1]
            dist = [(approachMatrix(health,impact,0.),value),
                    (approachMatrix(health,impact,self.health),1.-value)]
            tree[level] = {'distribution': dist}
        tree = makeTree({'if': trueRow(alive),
                         True: tree, False: setToConstantMatrix(health,0.)})
        if self.horizon <= 2:
            world.setDynamics(health,Action({'subject': self.name}),tree,codePtr=True)
        else:
            world.setDynamics(health,evolve,tree,codePtr=True)

        if self.demographics['kids'] > 0:
            # Effect on kids' health
            tree = {'if': thresholdRow(makeFuture(risk),likert[5][:]),
                    0: approachMatrix(kidHealth,impact,self.health)}
            for level in range(1,6):
                value = likert[5][level-1]
                dist = [(approachMatrix(kidHealth,impact,0.),value),
                        (approachMatrix(kidHealth,impact,self.health),1.-value)]
                tree[level] = {'distribution': dist}
            tree = makeTree({'if': trueRow(alive),
                             True: tree, False: setToConstantMatrix(kidHealth,0.)})
            if self.horizon <= 2:
                world.setDynamics(kidHealth,Action({'subject': self.name}),tree,codePtr=True)
            else:
                world.setDynamics(kidHealth,evolve,tree,codePtr=True)

        # Effect on life
        tree = makeTree({'if': trueRow(alive),
                         True: {'if': thresholdRow(makeFuture(health),
                                                   config.getfloat('Actors','life_threshold')),
                                True: setTrueMatrix(alive),
                                False: setFalseMatrix(alive)},
                         False: noChangeMatrix(alive)})
        world.setDynamics(alive,True,tree,codePtr=True)
        
        # Effect on wealth
        impactJob = config.getint('Actors','job_impact')
        impactNoJob = config.getint('Actors','wealth_spend')
        ceiling = config.getboolean('Actors','wealth_ceiling',fallback=False)
        if impactJob > 0:
            # Being at home or out of town, allows your job to make money
            tree = {'if': trueRow(alive),
                    True: {'if': trueRow(job),
                           True: {'if': equalRow(location,{self.demographics['home'],'evacuated'}),
                                  True: approachMatrix(wealth,likert[5][impactJob-1],self.demographics['wealth'] if ceiling else 1.),
                                  False: noChangeMatrix(wealth)},
                           False: None},
                    False: noChangeMatrix(wealth)}
            if impactNoJob > 0: 
                tree[True][False] = approachMatrix(wealth,likert[5][impactNoJob-1],0.)
            else:
                tree[True][False] = noChangeMatrix(wealth)
            world.setDynamics(wealth,self.nop,makeTree(tree),codePtr=True)
            # Going home allows you to work again
            tree = {'if': trueRow(alive),
                    True: {'if': trueRow(job),
                           True: approachMatrix(wealth,likert[5][impactJob-1],1.),
                           False: None},
                    False: noChangeMatrix(wealth)}
            if impactNoJob > 0: 
                tree[True][False] = approachMatrix(wealth,likert[5][impactNoJob-1],0.)
            else:
                tree[True][False] = noChangeMatrix(wealth)
            world.setDynamics(wealth,goHome,makeTree(tree),codePtr=True)
        # TODO: The following should be moved into the above if statement
        if config.getboolean('Shelter','exists') and not config.getboolean('Shelter','job'):
            for index,action in actShelter.items():
                tree = makeTree(approachMatrix(wealth,likert[5][impactNoJob-1],0.))
                world.setDynamics(wealth,action,tree,codePtr=True)
        if config.getboolean('Actors','evacuation'):
            cost = config.getint('Actors','evacuation_cost')
            if cost > 0:
                cost = likert[5][cost-1]
                tree = makeTree({'if': thresholdRow(wealth,cost),
                                 True: incrementMatrix(wealth,-cost),
                                 False: setToConstantMatrix(wealth,0.)})
                world.setDynamics(wealth,actEvacuate,tree,codePtr=True)
            if config.getint('Actors','evacuation_unemployment') > 0:
                # Might lose job
                prob = likert[5][config.getint('Actors','evacuation_unemployment')-1]
                tree = makeTree({'if': trueRow(alive),
                                 True: {'if': trueRow(job),
                                        True: {'distribution': [(noChangeMatrix(job),1.-prob),
                                                                (setFalseMatrix(job),prob)]},
                                        False: noChangeMatrix(job)},
                                 False: noChangeMatrix(job)})
            else:
                tree = makeTree(noChangeMatrix(job))
                world.setDynamics(job,actEvacuate,tree,codePtr=True)

        if config.getboolean('Actors','prorisk'):
            # Effect of doing good
            benefit = likert[5][config.getint('Actors','prorisk_benefit')-1]
            for region,action in actGoodRisk.items():
                key = stateKey(region,'risk')
                tree = makeTree(approachMatrix(key,benefit,self.world.agents[region].risk))
                world.setDynamics(key,action,tree,codePtr=True)
            cost = config.getint('Actors','prorisk_cost_risk')
            if cost > 0:
                for region,action in actGoodRisk.items():
                    tree = makeTree(approachMatrix(risk,likert[5][cost-1],1.))
                    world.setDynamics(risk,action,tree,codePtr=True)
        if config.getboolean('Actors','proresources'):
            # Effect of doing good
            benefit = likert[5][config.getint('Actors','proresources_benefit')-1]
            for region,action in actGoodResources.items():
                key = stateKey(region,'resources')
                tree = makeTree(approachMatrix(key,benefit,0.))
                world.setDynamics(key,action,tree,codePtr=True)
            cost = config.getint('Actors','proresources_cost_risk')
            if cost > 0:
                for region,action in actGoodResources.items():
                    tree = makeTree(approachMatrix(risk,likert[5][cost-1],1.))
                    world.setDynamics(risk,action,tree,codePtr=True)
        if config.getboolean('Actors','antiresources'):
            # Effect of doing bad
            benefit = likert[5][config.getint('Actors','antiresources_benefit')-1]
            for region,action in actBadResources.items():
                tree = makeTree(approachMatrix(wealth,benefit,self.demographics['wealth'] if ceiling else 1.))
                world.setDynamics(wealth,action,tree,codePtr=True)
            cost = config.getint('Actors','antiresources_cost_risk')
            if cost > 0:
                for region,action in actBadResources.items():
                    tree = makeTree({'if': equalRow(stateKey('Nature','phase'),'none'),
                                     True: approachMatrix(risk,likert[5][3],1.),
                                     False: approachMatrix(risk,likert[5][cost-1],1.)})
                    world.setDynamics(risk,action,tree,codePtr=True)
        if config.getboolean('Actors','antirisk'):
            # Effect of doing bad
            benefit = likert[5][config.getint('Actors','antirisk_benefit')-1]
            for region,action in actBadRisk.items():
                key = stateKey(region,'risk')
                tree = makeTree(approachMatrix(key,benefit,1.))
                world.setDynamics(key,action,tree,codePtr=True)
            cost = config.getint('Actors','antirisk_cost_risk')
            if cost > 0:
                for region,action in actBadRisk.items():
                    tree = makeTree({'if': equalRow(stateKey('Nature','phase'),'none'),
                                     True: approachMatrix(risk,likert[5][3],1.),
                                     False: approachMatrix(risk,likert[5][cost-1],1.)})
                    world.setDynamics(risk,action,tree,codePtr=True)


        if self.demographics.get('pet',False) and config.getboolean('Shelter','exists'):
            # Process shelters' pet policy
            for index,action in actShelter.items():
                    region = Region.nameString % (int(index))
                    tree = makeTree({'if': equalRow(makeFuture(location),'shelter%s' % (index)),
                                     True: {'if': trueRow(stateKey(region,'shelterPets')),
                                            True: noChangeMatrix(pet),
                                            False: setFalseMatrix(pet)},
                                     False: noChangeMatrix(pet)})
                    world.setDynamics(pet,action,tree,codePtr=True)

        # Reward
        sigma = config.getint('Actors','reward_sigma')
        mean = config.getint('Actors','reward_health_%s' % (self.demographics['gender']))
        self.Rweights = {'childrenHealth': 0.,'pet':0.}
        if mean > 0:
            if sigma > 0:
                self.Rweights['health'] = sampleNormal(mean,sigma)
            else:
                self.Rweights['health'] = likert[5][mean-1]
            self.setReward(maximizeFeature(health,self.name),self.Rweights['health'])
        else:
            self.Rweights['health'] = 0.
        mean = config.getint('Actors','reward_wealth_%s' % (self.demographics['gender']))
        if mean > 0:
            if sigma > 0:
                self.Rweights['resources'] = sampleNormal(mean,sigma)
            else:
                self.Rweights['resources'] = likert[5][mean-1]
            self.setReward(maximizeFeature(wealth,self.name),self.Rweights['resources'])
        else:
            self.Rweights['resources'] = 0.
        if self.demographics['kids'] > 0:
            mean = config.getint('Actors','reward_kids_%s' % (self.demographics['gender']))
            if mean > 0:
                if sigma > 0:
                    self.Rweights['childrenHealth'] = sampleNormal(mean,sigma)
                else:
                    self.Rweights['childrenHealth'] = likert[5][mean-1]
                self.setReward(maximizeFeature(kidHealth,self.name),self.Rweights['childrenHealth'])
        if self.demographics.get('pet',False):
            mean = config.getint('Actors','reward_pets')
            if mean > 0:
                if sigma > 0:
                    self.Rweights['pet'] = sampleNormal(mean,sigma)
                else:
                    self.Rweights['pet'] = likert[5][mean-1]
                self.setReward(maximizeFeature(pet,self.name),self.Rweights['pet'])
        mean = config.getint('Actors','altruism_neighbors_%s' % (self.demographics['religion']))
        if mean > 0:
            if sigma > 0:
                self.Rweights['neighbors'] = sampleNormal(mean,sigma)
            else:
                self.Rweights['neighbors'] = likert[5][mean-1]
            try:
                self.Rweights['neighbors'] /= float(len(neighbors))
            except ZeroDivisionError:
                pass
            self.setReward(minimizeFeature(stateKey(self.demographics['home'],'risk'),self.name),
                           self.Rweights['neighbors'])
        else:
            self.Rweights['neighbors'] = 0.
        if config.getboolean('Actors','beliefs'):
            # Observations
            evolve = ActionSet([Action({'subject': 'Nature','verb': 'evolve'})])
            if not config.getboolean('Simulation','graph',fallback=False):
                omega = self.defineObservation('perceivedPhase',domain=list,codePtr=True,
                                               lo=self.world.variables['Nature\'s phase']['elements'],
                                               description='Perception of Nature\'s phase')
                self.setO('perceivedPhase',None,
                          makeTree(setToFeatureMatrix(omega,stateKey('Nature','phase'))))
                self.world.setFeature(omega,'none')
            omega = self.defineObservation('perceivedDays',domain=int,codePtr=True,
                                           description='Perception of Nature\'s days')
            self.setO('perceivedDays',None,
                      makeTree(setToFeatureMatrix(omega,stateKey('Nature','days'))))
            self.world.setFeature(omega,0)
            if not config.getboolean('Simulation','graph',fallback=False):
                omega = self.defineObservation('perceivedCenter',domain=list,codePtr=True,
                                               lo=self.world.variables['Nature\'s location']['elements'],
                                               description='Perception of Nature\'s location')
                self.setO('perceivedCenter',None,
                          makeTree(setToFeatureMatrix(omega,stateKey('Nature','location'))))
                self.world.setFeature(omega,'none')

            omega = self.defineObservation('perceivedCategory',domain=int,codePtr=True,
                                           description='Perception of Nature\'s category')
            distortion = Distribution({'over': likert[5][config.getint('Actors','category_over')-1],
                                       'under': likert[5][config.getint('Actors','category_under')-1]})
            distortion['none'] = 1.-distortion['over']-distortion['under']
            self.distortion = distortion.sample()
            distortionProb = likert[5][config.getint('Actors','category_distortion')-1]
            real = stateKey('Nature','category')
            if self.distortion == 'none':
                tree = setToFeatureMatrix(omega,real)
            elif self.distortion == 'over':
                tree = {'if': equalRow(real,{0,5}),
                        True: setToFeatureMatrix(omega,real),
                        False: {'distribution': [(setToFeatureMatrix(omega,real),distortionProb),
                                                 (setToFeatureMatrix(omega,real,shift=1),
                                                  1.-distortionProb)]}}
            else:
                assert self.distortion == 'under'
                tree = {'if': equalRow(real,{0,1}),
                        True: setToFeatureMatrix(omega,real),
                        False: {'distribution': [(setToFeatureMatrix(omega,real),distortionProb),
                                                 (setToFeatureMatrix(omega,real,shift=-1),
                                                  1.-distortionProb)]}}
            self.setO('perceivedCategory',evolve,makeTree(tree))
            self.setO('perceivedCategory',None,makeTree(setToConstantMatrix(omega,0)))
            self.setState('perceivedCategory',0)
            
            if not config.getboolean('Simulation','graph',fallback=False):
                omega = self.defineObservation('perceivedHealth',codePtr=True,
                                               description='Perception of Actor\'s health')
                self.setO('perceivedHealth',None,
                          makeTree(setToFeatureMatrix(omega,stateKey(self.name,'health'))))
                self.setState('perceivedHealth',self.health)
                if self.demographics['kids'] > 0:
                    omega = self.defineObservation('perceivedChildrenHealth',domain=float,codePtr=True,
                                               description='Perception of Actor\'s childrenHealth')
                    self.setO('perceivedChildrenHealth',None,
                              makeTree(setToFeatureMatrix(omega,stateKey(self.name,'childrenHealth'))))
                    self.setState('perceivedChildrenHealth',self.health)
            if config.getboolean('Actors','infoseek'):
                omega = self.defineObservation('categoryData',domain=int,codePtr=True,
                                           description='Information received from explicit seeking')
                self.setState('categoryData',0)
                if config.getint('Actors','info_reliability') == 5:
                    # 100% reliable information
                    self.setO('categoryData',infoseek,
                              makeTree(setToFeatureMatrix(omega,real)))
                else:
                    assert config.getint('Actors','info_reliability') > 0
                    # Not much point in having 0% reliable information
                    trueProb = likert[5][config.getint('Actors','info_reliability')-1]
                    self.setO('categoryData',infoseek,
                              makeTree({'if': equalRow(real,1),
                                        True: {'distribution': [(setToConstantMatrix(omega,1),trueProb),
                                                                (setToConstantMatrix(omega,2),1.-trueProb)]},
                                        False: {'if': equalRow(real,5),
                                                True: {'distribution': [(setToConstantMatrix(omega,5),trueProb),
                                                                        (setToConstantMatrix(omega,4),1.-trueProb)]},
                                                False: {'distribution': [(setToFeatureMatrix(omega,real),trueProb),
                                                                         (setToFeatureMatrix(omega,real,shift=-1),(1.-trueProb)/2.),
                                                                         (setToFeatureMatrix(omega,real,shift=1),(1.-trueProb)/2.)]}}}))
        

    def makeFriend(self,friend,config):
        self.friends.add(friend.name)
        key = binaryKey(self.name,friend.name,'friendOf')
        if 'friendOf' not in self.world.relations or \
           key not in self.world.relations['friendOf']:
            self.world.defineRelation(self.name,friend.name,'friendOf',bool,codePtr=True)
        self.world.setFeature(key,True)
        # if config.getboolean('Actors','messages'):
        #     tree = makeTree({'if': trueRow(stateKey(self.name,'alive')),
        #                      True: {'if': trueRow(key),
        #                             True: True, False: False},
        #                      False: False})
        #     msg = self.addAction({'verb': 'msgReHurricane','object': friend.name},
        #                          tree.desymbolize(self.world.symbols),
        #                          'Send message communicating my current perceptions about the hurricane and its impact',True)
        #     omega = friend.defineObservation('rcvdCategoryMsg',domain=int,codePtr=True)
            

    def _initializeRelations(self,config):
        population = {a for a in self.world.agents.values() if isinstance(a,self.__class__)}
        friendMax = config.getint('Actors','friends')
        friendMin = config.getint('Actors','friendMin',fallback=0)
        neighbors = {a.name for a in population if a.name != self.name and a.demographics['home'] == self.demographics['home']}
        if friendMax > 0:
            # Social network
            friendCount = {}
            if 'friendOf' in self.world.relations:
                for key in self.world.relations['friendOf']:
                    relation = key2relation(key)
                    if relation['subject'] == self.name:
                        self.friends.add(relation['object'])
                    else:
                        friendCount[relation['subject']] = friendCount.get(relation['subject'],0)+1
            numFriends = random.randint(max(friendMin,len(self.friends)),friendMax)
            possibles = [agent.name for agent in population
                         if friendCount.get(agent.name,0) < friendMax
                         and agent.name not in self.friends]
            if len(population) > 1:
                # For illustrative graph purposes, we allow links to self
                possibles.remove(self.name)
            while len(self.friends) < numFriends and possibles:
                friend = random.choice(possibles)
                possibles.remove(friend)
                self.makeFriend(self.world.agents[friend],config)
                self.world.agents[friend].makeFriend(self,config)

        sigma = config.getint('Actors','reward_sigma')
        mean = config.getint('Actors','altruism_friends_%s' % (self.demographics['religion']))
        if mean > 0 and self.friends:
            if sigma > 0:
                self.Rweights['friends'] = sampleNormal(mean,sigma)
            else:
                self.Rweights['friends'] = likert[5][mean-1]
            try:
                self.Rweights['friends'] /= float(len(self.friends))
            except ZeroDivisionError:
                pass
        else:
            self.Rweights['friends'] = 0.
        for other in population:
            if self.name != other.name:
                R = 0.
#                if other in neighbors:
#                    R += self.Rweights['neighbors']
                if other in self.friends:
                    R += self.Rweights['friends']
                if R > 1e-8:
                    self.setReward(maximizeFeature(stateKey(other.name,'health'),self.name),R)
        
    def _initializeBeliefs(self,config):
        # Beliefs
        friends = set()
        population = {a for a in self.world.agents.values() if isinstance(a,self.__class__)}
        neighbors = {a.name for a in population if a.name != self.name and a.demographics['home'] == self.demographics['home']}
        if config.getboolean('Simulation','graph',fallback=False):
            for name in self.friends:
                print(name)
            if len(population) == 1:
                neighbors.add(self.name)
            for name in neighbors:
                key = self.world.defineRelation(self.name,name,'neighbor',bool,codePtr=True)
                self.world.setFeature(key,True)
                if self.Rweights['neighbors'] > 0.:
                    self.setReward(maximizeFeature(key,self.name),1.)

        regions = [n for n in self.world.agents if isinstance(self.world.agents[n],Region)]
        shelters = {int(region) for region in config.get('Shelter','region').split(',')}

        include = set()
        altNeighbor = config.getint('Actors','altruism_neighbors_%s' % (self.demographics['religion']))
        altFriend = config.getint('Actors','altruism_friends_%s' % (self.demographics['religion']))
        for key in self.world.state.keys():
            if isBinaryKey(key):
                agent = key2relation(key)['subject']
            else:
                agent = state2agent(key)
            if agent == self.name:
                if not isModelKey(key):
                    if not config.getboolean('Simulation','graph',fallback=False):
                        include.add(key)
                    elif state2feature(key) == 'risk':
                        include.add(key)
            elif agent == 'Nature':
                if not isModelKey(key):
                    if not config.getboolean('Simulation','graph',fallback=False):
                        include.add(key)
                    elif state2feature(key) in {'category','days'}:
                        include.add(key)
            elif agent[:5] == 'Group' and self.name in self.world.agents[agent].potentials:
                include.add(key)
                self.groups.add(agent)
            elif agent[:6] == 'System':
                if not config.getboolean('Simulation','graph',fallback=False):
                    include.add(key)
            elif agent == WORLD:
                if not config.getboolean('Simulation','graph',fallback=False):
                    include.add(key)
            # elif isinstance(self.world.agents[agent],Actor):
            #     if altNeighbor > 0 and agent in neighbors:
            #         # I care about my neighbors' health
            #         if state2feature(key) in {'health','alive','risk'}:
            #             include.add(key)
            #     elif altFriend > 0 and \
            #          self.world.getFeature(binaryKey(self.name,agent,'friendOf')).first():
            #         # I care about my friends' health
            #         if state2feature(key) in {'health','alive','risk'}:
            #             include.add(key)
            elif isinstance(self.world.agents[agent],Region):
                if agent == self.demographics['home']:
                    if not isModelKey(key):
                        if not config.getboolean('Simulation','graph',fallback=False):
                            include.add(key)
                        elif state2feature(key) == 'risk':
                            include.add(key)
                elif self.world.agents[agent].number in shelters:
                    if state2feature(key)[:7] == 'shelter':
                        if not config.getboolean('Simulation','graph',fallback=False):
                            include.add(key)
        beliefs = self.resetBelief(include=include)

    def memberOf(self,state):
        inGroup = []
        for group in self.groups:
            key = binaryKey(self.name,group,'memberOf')
            membership = self.world.getFeature(key,state)
            assert len(membership) == 1,'Unable to process uncertain group membership'
            if membership.first():
                inGroup.append(group)
        return inGroup
    
    def getActions(self,state,actions=None):
        for group in self.memberOf(state):
            key = stateKey(group,ACTION)
            if key in state:
                dist = self.world.getFeature(key,state)
                assert len(dist) == 1,'Unable to handle uncertain group decisions'
                action = dist.first()
                if action['verb'] != 'noDecision':
                    for myAction in self.actions:
                        if myAction['verb'] == action['verb']:
                            if 'object' not in action or myAction['object'] == action['object']:
                                return {myAction}
        try:
            return super().getActions(state,actions)
        except TypeError:
            return super(Actor,self).getActions(state,actions)

    def getO(self,state,actions):
        try:
            omega = super().getO(state,actions)
        except TypeError:
            omega = super(Actor,self).getO(state,actions)
        for action in actions:
            if action['verb'] == 'msgReHurricane' and action['object'] == self.name:
                trust = self.config.getint('Actors','friend_trust')
                prob = likert[5][trust-1]
                sender = self.world.agents[action['subject']]
                # Is this cheating? Maybe.
                belief = sender.getBelief(self.world.state)
                category = self.world.getState('Nature','category',belief).max()
                key = stateKey(self.name,'rcvdCategoryMsg')
                if trust == 5:
                    tree = setToConstantMatrix(key,category)
                elif category == 1:
                    tree = {'distribution': [(setToConstantMatrix(key,category),prob),
                                             (setToConstantMatrix(key,category+1),1.-prob)]}
                elif category == 5:
                    tree = {'distribution': [(setToConstantMatrix(key,category),prob),
                                             (setToConstantMatrix(key,category-1),1.-prob)]}
                else:
                    tree = {'distribution': [(setToConstantMatrix(key,category),prob),
                                             (setToConstantMatrix(key,category+1),(1.-prob)/2.),
                                             (setToConstantMatrix(key,category-1),(1.-prob)/2.)]}
                omega[key] = makeTree(tree).desymbolize(self.world.symbols)
                            
        return omega
    
    def recvMessage(self,key,msg,myScale=1.,yrScaleOpt=1.,yrScalePess=1.,model=None):
        beliefs = self.getBelief()
        if model is None:
            assert len(beliefs) == 1,'Unable to incorporate messages when identity is uncertain'
            model,myBelief = next(iter(beliefs.items()))
        else:
            myBelief = beliefs[model]
        dist = myBelief[key]
        old = dist.expectation()
        if old is None:
            logging.error('%s [%s] has null belief on %s' % (self.name,model,key))
        else:
            total = Distribution({el: myScale*dist[el] for el in dist.domain()})
            for value in msg.domain():
                if msg.expectation() > old:
                    total.addProb(value,yrScaleOpt*msg[value])
                else:
                    total.addProb(value,yrScalePess*msg[value])
            total.normalize()
            self.setBelief(key,total,model)

    def decide(self,state=None,horizon=None,others=None,model=None,selection='uniform',
                    actions=None,debug={}):
        if state is None:
            state = self.world.state
        if model is None:
            try:
                model = self.world.getModel(self.name,state)
            except KeyError:
                # Use real model as fallback?
                model = self.world.getModel(self.name)
            assert len(model) == 1
            model = model.first()
        if actions is None:
            actions = self.getActions(state)
        belief = self.getBelief(state,model)
        for group in self.groups:
            membership = self.world.getFeature(binaryKey(self.name,group,'memberOf'))
            assert len(membership) == 1,'Unable to handle uncertain group membership'
            if membership.first():
                # I'm in this group; has there been a group decision?
                action = self.world.getFeature(stateKey(group,ACTION))
                assert len(action) == 1
                action = action.first()
                if action['verb'] != 'noDecision':
                    candidates = []
                    for lonely in actions:
                        if lonely['verb'] == action['verb']:
                            if 'object' in action:
                                if lonely['object'] == action['object']:
                                    return {'action': lonely}
                            elif 'object' in lonely:
                                candidates.append(lonely)
                            else:
                                return {'action': lonely}
                    assert len(candidates) == 1,'Multiple options for agent %s to satisfy group %s decision %s:\n%s' % (self.name,group,action,candidates)
                    return {'action': candidates[0]}
        else:
            decision = Agent.decide(self,state,horizon,others,model,'uniform',actions,
                                    belief.keys(),debug)
            if len(decision['action']) > 1:
                try:
                    home = self.demographics['home']
                except AttributeError:
                    home = self.world.getState(self.name,'region').first()
                if self.world.getState(self.name,'location',belief).first() == home:
                    action = ActionSet(Action({'subject': self.name,'verb': 'stayInLocation'}))
                else:
                    action = ActionSet(Action({'subject': self.name, 'verb': 'moveTo','object': home}))
                for choice in decision['action'].domain():
                    if action == choice:
                        decision['action'] = choice
                        break
                else:
                    decision['action'] = decision['action'].first()
            return decision
