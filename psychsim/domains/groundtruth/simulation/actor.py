import logging
import random
import sys

from psychsim.probability import Distribution
from psychsim.pwl import *
from psychsim.action import *
from psychsim.reward import *
from psychsim.agent import Agent
from psychsim.domains.groundtruth.simulation.data import likert,toLikert,sampleNormal,logNode,logEdge
from psychsim.domains.groundtruth.simulation.region import Region


if (sys.version_info > (3, 0)):
    import configparser
else:
    import ConfigParser as configparser

class Actor(Agent):
    def __init__(self,number,world,config):
        self.config = config
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

        self.demographics = {}
        self.prescription = None
        self.correctInfo = None
        self.riskAttitude = None
        self.shelters = []

        # Decision-making parameters
        logNode('Actor\'s horizon','Number of steps into future that actor uses to evaluate candidate action choices','Positive integer','Static')
        #//GT: node 14; 1 of 1; next 7 lines
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
        logNode('Actor\'s ethnicGroup','Actor\'s ethnicity','String: either "majority" or "minority"','Static')
        #//GT: node 15; 1 of 1; next 4 lines
        if random.random() > likert[5][config.getint('Actors','ethnic_majority')-1]:
            self.demographics['ethnicGroup'] = 'minority'
        else:
            self.demographics['ethnicGroup'] = 'majority'

        if config.getint('Simulation','phase',fallback=1) == 1:
            ethnic = world.defineState(self.name,'ethnicGroup',list,['majority','minority'],
                                       description='Ethnicity of actor',codePtr=True)
            world.setFeature(ethnic,self.demographics['ethnicGroup'])

        logNode('Actor\'s religion','Actor\'s religion','String: either "majority" or "minority" or "none"','Static')
        #//GT: node 16; 1 of 1; next 8 lines
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

        logNode('Actor\'s employed','True iff actor has a job','Boolean')
        #//GT: node 17; 1 of 1; next 5 lines
        job = world.defineState(self.name,'employed',bool,description='Has a full-time job',
                                codePtr=True)
        threshold = likert[5][config.getint('Actors','job_%s' % (self.demographics['ethnicGroup']))-1]
        self.demographics['job'] = random.random() < threshold
        world.setFeature(job,self.demographics['job'])

        logNode('Actor\'s pet','Whether actor owns a pet','Boolean')
        #//GT: node 18; 1 of 1; next 8 lines
        threshold = config.getint('Actors','pet_prob')
        if threshold > 0:
            self.demographics['pet'] = random.random() < likert[5][threshold-1]
            if self.demographics['pet']:
                pet = world.defineState(self.name,'pet',bool,description='Owns a pet',codePtr=True)
                world.setFeature(pet,self.demographics['pet'])
        else:
            self.demographics['pet'] = False

        # Psychological
        if config.getboolean('Actors','attachment'):
            logNode('Actor\'s attachment','Attachment style of the actor','String: "secure" / "anxious" / "avoidant"')
            # // GT: node 40; 1 of 1; next 10 lines
            attachmentStyles = {'secure': likert[5][config.getint('Actors','attachment_secure')-1],
                                'anxious': likert[5][config.getint('Actors','attachment_anxious')-1]}
            attachmentStyles['avoidant'] = 1.-attachmentStyles['secure']-attachmentStyles['anxious']
            attachmentStyles = Distribution(attachmentStyles)
            self.attachment = attachmentStyles.sample()

#            attachment = world.defineState(self.name,'attachment',list,
#                                           list(attachmentStyles.domain()),
#                                           description='Attachment style',codePtr=True)
#            world.setFeature(attachment,self.attachment)

        if config.getboolean('Actors','appraisal'):
            # Coping Style
            logNode('Actor\'s copingStyle','Coping style of the actor','String: "none" / "problem" / "emotion"')
            # // GT: node 41; 1 of 1; next 11 lines
            copingStyles = {'none': 1.}
            if config.getint('Actors','coping_emotion') > 0:
                copingStyles['emotion'] = likert[5][config.getint('Actors','coping_emotion')-1]
            if config.getint('Actors','coping_problem') > 0:
                copingStyles['problem'] = likert[5][config.getint('Actors','coping_problem')-1]
            copingStyles = Distribution(copingStyles)
            self.coping = copingStyles.sample()

#            coping = world.defineState(self.name,'coping',list,['none','emotion','problem'],
#                                       description='Coping style, whether biased toward emotion- or problem-directed decision-making',
#                                       codePtr=True)
#            world.setFeature(coping,self.coping)

            # Control bias
            logNode('Actor\'s controlStyle','Control bias of the actor','String: "none" / "hiEfficacy" / "loEfficacy"')
            # // GT: node 42; 1 of 1; next 13 lines
            controlStyles = {'none': 1.}
            if config.getint('Actors','control_hi') > 0:
                controlStyles['hiEfficacy'] = likert[5][config.getint('Actors','control_hi')-1]
                controlStyles['none'] -= controlStyles['hiEfficacy']
            if config.getint('Actors','control_lo') > 0:
                controlStyles['loEfficacy'] = likert[5][config.getint('Actors','control_lo')-1]
                controlStyles['none'] -= controlStyles['loEfficacy']
            controlStyles = Distribution(controlStyles)
            self.control = controlStyles.sample()

#            control = world.defineState(self.name,'control',list,['none','hiEfficacy','loEfficacy'],
#                                        description='Control style, whether low or high self-efficacy',
#                                        codePtr=True)
#            world.setFeature(control,self.control)

            # Causal attribution
            logNode('Actor\'s attributionStyle','Causal attribution of the actor','String: "none" / "internal" / "external"')
            # // GT: node 42; 1 of 1; next 14 lines
            attributionStyles = {'none': 1.}
            if config.getint('Actors','attribution_in') > 0:
                attributionStyles['internal'] = likert[5][config.getint('Actors','attribution_in')-1]
                attributionStyles['none'] -= attributionStyles['internal']
            if config.getint('Actors','attribution_ex') > 0:
                attributionStyles['external'] = likert[5][config.getint('Actors','attribution_ex')-1]
                attributionStyles['none'] -= attributionStyles['external']
            attributionStyles = Distribution(attributionStyles)
            self.attribution = attributionStyles.sample()

#            attribution = world.defineState(self.name,'attribution',list,['none','internal',
#                                                                          'external'],
#                                            description='Causal attribution style, whether attributing events to internal or external causes',
#                                            codePtr=True)
#            world.setFeature(attribution,self.attribution)

        logNode('Actor\'s home','Region of residence','Region[01-16]')
        #//GT: node 19; 1 of 1; next 11 lines
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

        neighbors = self.getNeighbors()

        self.spouse = None
        if config.getint('Actors','married',fallback=0) > 0:
            logNode('Actor marriedTo Actor','Marriage relationship between two actors','Boolean','Static')
            #//GT: node 22; 1 of 1; next 11 lines
            threshold = likert[5][config.getint('Actors','married')-1]/2
            if random.random() < threshold:
                others = [other for other,otherAgent in self.world.agents.items() if other[:5] == 'Actor' and other != self.name and \
                    other in neighbors and otherAgent.spouse is None]
                if others:
                    self.spouse = random.choice(others)
                    key = self.world.defineRelation(self.name,self.spouse,'marriedTo',bool,codePtr=True)
                    self.world.setFeature(key,True)
                    key = self.world.defineRelation(self.spouse,self.name,'marriedTo',bool,codePtr=True)
                    self.world.setFeature(key,True)
                    self.world.agents[self.spouse].spouse = self.name

        if config.getboolean('Simulation','visualize',fallback=False):
            # For display use only
            tooClose = True
            while tooClose:
                x = random.random()
                y = random.random()
                for neighbor in neighbors:
                    if config.getint('Simulation','phase',fallback=1) == 1:
                        if abs(neighbor.getState('x').first()-x)+abs(neighbor.getState('y').first()-y) < 0.05:
                            break
                    elif abs(neighbor.x-x)+abs(neighbor.y-y) < 0.05:
                        break
                else:
                    tooClose = False
            if config.getint('Simulation','phase',fallback=1) == 1:
                xKey = world.defineState(self.name,'x',float,
                                         description='Representation of residence\'s longitude',codePtr=True)
                yKey = world.defineState(self.name,'y',float,
                                         description='Representation of residence\'s latitude',codePtr=True)
                world.setFeature(xKey,x)
                world.setFeature(yKey,y)
            else:            
                self.x = x
                self.y = y

        # Dynamic states
        logNode('Actor\'s location','Where actor currently is','String: either region name / shelter name / "evacuated"')
        #//GT: node 23; 1 of 1; next 13 lines
        if config.getboolean('Actors','movement'):
            locationSet = regions[:]
        else:
            locationSet = [self.demographics['home']]
        locationSet.append('evacuated')
        if config.getboolean('Shelter','exists'):
            for index in config.get('Shelter','region').split(','):
                region = Region.nameString % (int(index))
                if region in self.world.agents:
                    locationSet.append('shelter%s' % (index))
        location = world.defineState(self.name,'location',list,locationSet,
                                     description='Current location',codePtr=True)
        world.setFeature(location,self.demographics['home'])

        if config.getint('Simulation','phase',fallback=1) < 3:
            alive = world.defineState(self.name,'alive',bool,codePtr=True)
            world.setFeature(alive,True)

        logNode('Actor\'s health','Level of actor\'s wellbeing','Real in [0-1]')
        #//GT: node 21; 1 of 1; next 15 lines
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

        if self.demographics['kids'] > 0:
            logNode('Actor\'s childrenHealth','Level of children\'s wellbeing','Real in [0-1]')
            #//GT: node 40; 1 of 1; next 4 lines
            kidHealth = world.defineState(self.name,'childrenHealth',float,
                                          description='Current level of children\'s physical wellbeing',
                                          codePtr=True)
            world.setFeature(kidHealth,self.health)

        logNode('Actor\'s resources','Level of wealth','Real in [0-1]')
        #//GT: node 24; 1 of 1; next 19 lines
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
            mean = min(max(1,mean),5)
            sigma = config.getint('Actors','wealth_sigma')
            if sigma > 0:
                self.demographics['wealth'] = sampleNormal(mean,sigma)
            else:
                self.demographics['wealth'] = likert[5][mean-1]
        world.setFeature(wealth,self.demographics['wealth'])

        logNode('Actor\'s risk','Level of personal risk','Real in [0-1]')
        #//GT: node 25; 1 of 1; next 3 lines
        risk = world.defineState(self.name,'risk',float,codePtr=True,lo=0.,hi=1.,
                                 description='Current level of risk from hurricane')
        world.setFeature(risk,float(world.getState(self.demographics['home'],'risk')))

        if config.getboolean('Actors','grievance'):
            logNode('Actor\'s grievance','Level of dissatisfaction with government','Real in [0-1]')
            #//GT: node 26; 1 of 1; next 16 lines
            mean = config.getint('Actors','grievance_ethnic_%s' % (self.demographics['ethnicGroup']))
            mean += config.getint('Actors','grievance_religious_%s' % (self.demographics['religion']))
            mean += config.getint('Actors','grievance_%s' % (self.demographics['gender']))
            if self.demographics['wealth'] > likert[5][config.getint('Actors','grievance_wealth_threshold')-1]:
                mean += config.getint('Actors','grievance_wealth_yes')
            else:
                mean += config.getint('Actors','grievance_wealth_no')
            mean = min(max(1,mean),5)
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
        logNode('Actor-stayInLocation','Action choice of staying in current location','Boolean')
        #//GT: node 27; 1 of 1; next 2 lines
        self.nop = self.addAction({'verb': 'stayInLocation'},codePtr=True,
                                  description='Actor does not move from current location, nor perform any pro/antisocial behaviors')

        goHomeFrom = set()
        if config.getboolean('Shelter','exists'):
            # Go to shelter
            logNode('Actor-moveTo-shelter','Action choice of moving to public shelter','Boolean')
            #//GT: node 28; 1 of 1; next 45 lines
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
                self.shelters.append(region)
                goHomeFrom.add(shelter)
                tree = {'if': equalRow(stateKey('Nature','phase'),'none'),
                        True: False}
                if config.getint('Simulation','phase',fallback=1) < 3:
                    tree[False] = {'if': trueRow(alive),
                                True: {'if': equalRow(location,shelter),
                                       True: False,
                                       False: True},
                                False: False}
                else:
                    tree[False] = {'if': equalRow(location,shelter),True: False,False: True}
                if world.agents[region].capacity > 0:
                    logEdge('Region\'s shelterCapacity','Actor-moveTo-shelter','sometimes','Cannot move to a full shelter')
                    #//GT: edge 15; from 5; to 28; 1 of 1; next 18 lines
                    logEdge('Region\'s shelterOccupancy','Actor-moveTo-shelter','sometimes','Cannot move to a full shelter')
                    #//GT: edge 16; from 6; to 28; 1 of 1; next 16 lines
                    tree = {'if': greaterThanRow(stateKey(region,'shelterCapacity'),
                                                 stateKey(region,'shelterOccupancy')),
                            True: tree, False: False}
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
            logNode('Actor-evacuate','Action choice of leaving the area for at least a short time','Boolean')
            #//GT: node 29; 1 of 1; next 11 lines
            tree = {'if': equalRow(stateKey('Nature','phase'),'none'),
                             True: False,
                             False: {'if': equalRow(location,'evacuated'),
                                     True: False}}
            if config.getint('Simulation','phase',fallback=1) < 3:
                tree[False][False] = {'if': trueRow(alive),True: True, False: False}
            else:
                tree[False][False] = True
            actEvacuate = self.addAction({'verb': 'evacuate'},makeTree(tree).desymbolize(world.symbols),
                                         'Evacuate the city at least temporarily',True)
            goHomeFrom.add('evacuated')

        if goHomeFrom:
            logNode('Actor-moveTo-home','Action choice of moving back home','Boolean')
            #//GT: node 30; 1 of 1; next 5 lines
            tree = makeTree({'if': equalRow(location,goHomeFrom),
                             True: True, False: False})
            goHome = self.addAction({'verb': 'moveTo','object': self.demographics['home']},
                                    tree.desymbolize(world.symbols),
                                    'Return home',True)
            
        if config.getboolean('Actors','prorisk'):
            # Prosocial behavior
            logNode('Actor-decreaseRisk','Prosocial action choice','Boolean')
            #//GT: node 31; 1 of 1; next 17 lines
            actGoodRisk = {}
            for region in regions:
                if config.getboolean('Actors','movement') or region == self.demographics['home']:
                    tree = {'if': equalRow(location,region),False: False}
                    if config.getint('Simulation','phase',fallback=1) < 3:
                        tree[True] = {'if': trueRow(alive),True: True, False: False}
                    else:
                        tree[True] = True
                    if config.getboolean('Actors','prorisk_hurricane_only',fallback=False):
                        # Only legal when there is a hurricane
                        if config.getint('Simulation','phase',fallback=1) < 3:
                            tree[True][True] = {'if': equalRow(stateKey('Nature','phase'),'none'),True: False,False: True}
                        else:
                            tree[True] = {'if': equalRow(stateKey('Nature','phase'),'none'),True: False,False: True}
                    actGoodRisk[region] = self.addAction({'verb': 'decreaseRisk','object': region},
                                                         makeTree(tree).desymbolize(world.symbols),
                                                         'Perform prosocial behaviors to reduce the danger posed by the hurricane in a given region',True)

        if config.getboolean('Actors','proresources'):
            # Prosocial behavior
            actGoodResources = {}
            for region in regions:
                if config.getboolean('Actors','movement') or region == self.demographics['home']:
                    tree = {'if': equalRow(location,region),False: False}
                    if config.getint('Simulation','phase',fallback=1) < 3:
                        tree[True] = {'if': trueRow(alive),True: True, False: False}
                    else:
                        tree[True] = True
                    if config.getboolean('Actors','proresources_hurricane_only',fallback=False):
                        # Only legal when there is a hurricane
                        tree[True][True] = {'if': equalRow(stateKey('Nature','phase'),'none'),True: False,False: True}
                    actGoodResources[region] = self.addAction({'verb': 'giveResources',
                                                               'object': region},
                                                              makeTree(tree).desymbolize(world.symbols),
                                                              'Perform prosocial behaviors to gather and donate resources to the people of a given region',True)
        if config.getboolean('Actors','antirisk'):
            # Antisocial behavior
            actBadRisk = {}
            for region in regions:
                if config.getboolean('Actors','movement') or region == self.demographics['home']:
                    tree = {'if': equalRow(location,region),False: False}
                    if config.getint('Simulation','phase',fallback=1) < 3:
                        tree[True] = {'if': trueRow(alive),True: True, False: False}
                    else:
                        tree[True] = True
                    if config.getboolean('Actors','antirisk_hurricane_only',fallback=False):
                        # Only legal when there is a hurricane
                        tree[True][True] = {'if': equalRow(stateKey('Nature','phase'),'none'),True: False,False: True}
                    actBadRisk[region] = self.addAction({'verb': 'increaseRisk','object': region},
                                                        makeTree(tree).desymbolize(world.symbols),
                                                        'Perform antisocial behaviors that increase the danger faced by people in a given region',True)
        if config.getboolean('Actors','antiresources'):
            # Antisocial behavior
            logNode('Actor-takeResources','Antisocial action choice','Boolean')
            #//GT: node 32; 1 of 1; next 18 lines
            actBadResources = {}
            for region in regions:
                if config.getboolean('Actors','movement') or region == self.demographics['home']:
                    tree = {'if': equalRow(location,region),False: False}
                    if config.getint('Simulation','phase',fallback=1) < 3:
                        tree[True] = {'if': trueRow(alive),True: True, False: False}
                    else:
                        tree[True] = True
                    if config.getboolean('Actors','antiresources_hurricane_only',fallback=False):
                        # Only legal when there is a hurricane
                        if config.getint('Simulation','phase',fallback=1) < 3:
                            tree[True][True] = {'if': equalRow(stateKey('Nature','phase'),'none'),True: False,False: True}
                        else:
                            tree[True] = {'if': equalRow(stateKey('Nature','phase'),'none'),True: False,False: True}
                    actBadResources[region] = self.addAction({'verb': 'takeResources',
                                                              'object': region},
                                                             makeTree(tree).desymbolize(world.symbols),
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
                tree = {'if': equalRow(location,bordering), False: False}
                if config.getint('Simulation','phase',fallback=1) < 3:
                    tree[True] = {'if': trueRow(alive),True: True, False: False}
                else:
                    tree[True] = True
                actMove[region.name] = self.addAction({'verb': 'moveTo',
                                                       'object': region.name},
                                                      makeTree(tree).desymbolize(world.symbols),
                                                      codePtr=True)

        # Information-seeking actions
        if config.getboolean('Actors','infoseek'):
            logNode('Actor-infoSeek','Seek out additional information about the hurricane risk','Boolean')
            #
            if config.getint('Simulation','phase',fallback=1) < 3:
                tree = makeTree({'if': trueRow(alive), True: True, False: False})
            else:
                tree = None
            infoseek = self.addAction({'verb': 'seekInfoReHurricane'},
                                      tree.desymbolize(world.symbols),
                                      'Seek out additional information about the hurricane risk',True)
                
        # Effect on location
        if config.getboolean('Shelter','exists'):
            logEdge('Actor-moveTo-shelter','Actor\'s location','often','Moving to a shelter changes the actors\' location to that shelter')
            #//GT: edge 17; from 28; to 23; 1 of 1; next 3 lines
            for index,action in actShelter.items():
                tree = makeTree(setToConstantMatrix(location,'shelter%s' % (index)))
            world.setDynamics(location,action,tree,codePtr=True)

        if config.getboolean('Actors','evacuation'):
            logEdge('Actor-evacuate','Actor\'s location','often','Evacuating changes the actors\' location to "evacuated"')
            #//GT: edge 18; from 29; to 23; 1 of 1; next 2 lines
            tree = makeTree(setToConstantMatrix(location,'evacuated'))
            world.setDynamics(location,actEvacuate,tree,codePtr=True)

        if config.getboolean('Actors','movement'):
            for region in regions:
                tree = makeTree(setToConstantMatrix(location,region.name))
                logEdge(str(actMove[region.name],'Actor\'s location','often','Moving to a different region changes location'))
                #
                world.setDynamics(location,actMove[region.name],tree,codePtr=True)

        if goHomeFrom:
            logEdge('Actor-moveTo-home','Actor\'s location','often','When actors move to their home region their location becomes that region')
            #//GT: edge 19; from 30; to 23; 1 of 1; next 2 lines
            tree = makeTree(setToConstantMatrix(location,self.demographics['home']))
            world.setDynamics(location,goHome,tree,codePtr=True)

        # Effect on my risk
        logEdge('Actor\'s location','Actor\'s risk','often','Actor\'s personal risk decreases if evacuated; otherwise it moves closer to the risk in his/her current location')
        #//GT: edge 20; from 23; to 25; 1 of 1; next 10 lines
        logEdge('Actor\'s location','ActorBeliefOfActor\'s risk','often','Actor\'s belief about risk is influenced in the same way as actual risk')
        #//GT: edge 21; from 23; to 33; 1 of 1; next 8 lines
        if config.getboolean('Actors','movement'):
            tree = noChangeMatrix(risk)
        else:
            tree = setToFeatureMatrix(risk,makeFuture(stateKey(self.demographics['home'],'risk')))
        if config.getboolean('Actors','evacuation'):
            tree = {'if': equalRow(makeFuture(location),'evacuated'),
                    True: approachMatrix(risk,0.9,0.),
                    False:  tree}

        if config.getboolean('Shelter','exists'):
            logEdge('ActorBeliefOfRegion\'s shelterRisk','ActorBeliefOfActor\'s risk','often','Actors staying at the shelter have a perception of personal risk based on their perception of risk at the shelter')
            #//GT: edge 22; from 13; to 33; 1 of 1; next 7 lines
            logEdge('Region\'s shelterRisk','Actor\'s risk','sometimes','Actors staying at the shelter face a level of personal risk based on the risk at the shelter')
            #//GT: edge 23; from 3; to 25; 1 of 1; next 5 lines
            for index in actShelter:
                region = Region.nameString % (int(index))
                tree = {'if': equalRow(makeFuture(location),'shelter%s' % (index)),
                        True: setToFeatureMatrix(risk,stateKey(region,'shelterRisk')),
                        False: tree}

        logEdge('ActorBeliefOfRegion\'s risk','ActorBeliefOfActor\'s risk','often','Actors staying at home face a higher risk level in their region of residence leads to a higher level of personal risk')
        #//GT: edge 24; from 12; to 33; 1 of 1; next 20 lines
        logEdge('Region\'s risk','Actor\'s risk','often','Actors staying at home face a higher risk level in their region of residence leads to a higher level of personal risk')
        #//GT: edge 25; from 1; to 25; 1 of 1; next 18 lines
        if config.getboolean('Actors','movement'):
            for region in regions:
                tree = {'if': equalRow(makeFuture(location),region.name),
                        True: setToFeatureMatrix(risk,stateKey(region.name,'risk')),
                        False: tree}
        if config.getint('Simulation','phase',fallback=1) < 3:
            tree = {'if': trueRow(alive if config.getint('Simulation','phase',fallback=1) else makeFuture(alive)),
                True: tree, 
                False: setToConstantMatrix(risk,0.)}
        if config.getint('Simulation','phase',fallback=1) == 1:
            world.setDynamics(risk,True,makeTree(tree),codePtr=True)
        elif config.getint('Simulation','phase',fallback=1) < 3:
            for action in self.actions:
                world.setDynamics(risk,action,makeTree(tree),codePtr=True)
        else:
            logEdge('Actor-stayInLocation','Actor\'s risk','often','Actors staying in a location face the risk associated with that location')
            #//GT: edge 26; from 27; to 25; 1 of 1; next 1 lines
            world.setDynamics(risk,self.nop,makeTree(tree),codePtr=True)

        if config.getboolean('Actors','evacuation') and config.getboolean('Disaster','evacuation_path_risk',fallback=False):
            logEdge('Actor-evacuate','Actor\'s risk','often','Evacuating can incur risk on the way')
            #//GT: edge 27; from 29; to 25; 1 of 1; next 3 lines
            path = self.world.agents[self.demographics['home']].evacuationPath()
            tree = setToFeatureMatrix(risk,makeFuture(stateKey(path[-1],'risk')))
            world.setDynamics(risk,actEvacuate,makeTree(tree),codePtr=True)

        if config.getboolean('Shelter','exists'):

            if config.getboolean('Disaster','shelter_path_risk',fallback=False):
                logEdge('Actor-moveTo-shelter','Actor\'s risk','often','Actors moving to shelter incur some risk before entering')
                #//GT: edge 28; from 28; to 25; 1 of 1; next 4 lines
                for index,action in actShelter.items():
                    region = Region.nameString % (int(index))
                    tree = setToFeatureMatrix(risk,makeFuture(stateKey(region,'risk')))
                    world.setDynamics(risk,action,makeTree(tree),codePtr=True)

            for index,action in actShelter.items():
                region = Region.nameString % (int(index))
                if world.agents[region].capacity > 0:
                    logEdge('Actor-moveTo-shelter','Region\'s shelterOccupancy','sometimes','Moving to a shelter increases the number of people in it')
                    #//GT: edge 29; from 28; to 6; 1 of 1; next 2 lines
                    tree = incrementMatrix(stateKey(region,'shelterOccupancy'),1)
                    world.setDynamics(stateKey(region,'shelterOccupancy'),action,makeTree(tree),codePtr=True)

            for index,action in actShelter.items():
                region = Region.nameString % (int(index))
                if world.agents[region].capacity > 0:
                    logEdge('Actor-moveTo-home','Region\'s shelterOccupancy','sometimes','Moving out of shelter decreases the number of people in it')
                    #//GT: edge 30; from 30; to 6; 1 of 1; next 4 lines
                    tree = {'if': equalRow(location,'shelter%s' % (index)),
                        True: incrementMatrix(stateKey(region,'shelterOccupancy'),-1),
                        False: noChangeMatrix(stateKey(region,'shelterOccupancy'))}
                    world.setDynamics(stateKey(region,'shelterOccupancy'),goHome,makeTree(tree),codePtr=True)

            for index,action in actShelter.items():
                region = Region.nameString % (int(index))
                if world.agents[region].capacity > 0:
                    logEdge('Actor-evacuate','Region\'s shelterOccupancy','sometimes','Moving out of shelter decreases the number of people in it')
                    #//GT: edge 31; from 29; to 6; 1 of 1; next 4 lines
                    tree = {'if': equalRow(location,'shelter%s' % (index)),
                        True: incrementMatrix(stateKey(region,'shelterOccupancy'),-1),
                        False: noChangeMatrix(stateKey(region,'shelterOccupancy'))}
                    world.setDynamics(stateKey(region,'shelterOccupancy'),actEvacuate,makeTree(tree),codePtr=True)

        # Effect on my health
        impact = likert[5][config.getint('Actors','health_impact')-1]
        self.setHealthDynamics(impact,impact)

        if self.demographics['kids'] > 0:
            # Effect on kids' health
            logEdge('Actor\'s risk','Actor\'s childrenHealth','often','Higher levels of personal risk lead to higher likelihoods and higher severity of health loss for their children')
            #//GT: edge 53; from 25; to 40; 1 of 1; next 18 lines
            tree = {'if': thresholdRow(makeFuture(risk),likert[5][:]),
                    0: approachMatrix(kidHealth,impact,self.health)}
            for level in range(1,6):
                value = likert[5][level-1]
                dist = [(approachMatrix(kidHealth,impact,0.),value),
                        (approachMatrix(kidHealth,impact,self.health),1.-value)]
                tree[level] = {'distribution': dist}
            if config.getint('Simulation','phase',fallback=1) < 3:
                tree = {'if': trueRow(alive),
                                 True: tree, False: setToConstantMatrix(kidHealth,0.)}
            if config.getint('Simulation','phase',fallback=1) == 1:
                if self.horizon <= 2:
                    world.setDynamics(kidHealth,Action({'subject': self.name}),makeTree(tree),codePtr=True)
                else:
                    world.setDynamics(kidHealth,evolve,makeTree(tree),codePtr=True)
            else:
                for action in self.actions:
                    world.setDynamics(kidHealth,action,makeTree(tree),codePtr=True)

        if config.getint('Simulation','phase',fallback=1) < 3:
            # Effect on life
            logEdge('Actor\'s health','Actor\'s alive','often','Actor is dead or alive based on current health level')
            #
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
            logEdge('Actor-stayInLocation','Actor\'s resources','often','If an actor stays at home s/he can still go to work and earn money')
            #//GT: edge 33; from 27; to 24; 1 of 1; next 30 lines
            logEdge('Actor\'s employed','Actor\'s resources','sometimes','Actors who are employed experience an increase in resources on every day where they go to work (e.g. as opposed to staying in a shelter)')
            #//GT: edge 34; from 17; to 24; 1 of 1; next 28 lines
            logEdge('Actor\'s location','Actor\'s resources','often','An actor\'s resource gain/loss depends on the location in terms of whether s/he can go to work')
            #//GT: edge 35; from 23; to 24; 1 of 1; next 26 lines
            logEdge('Region\'s economy','Actor\'s resources','sometimes','Actors gain income from working only if economy is high')
            #//GT: edge 36; from 2; to 24; 1 of 1; next 24 lines
            tree = {'if': trueRow(job),
               True: {'if': equalRow(location,{self.demographics['home'],'evacuated'}),
                      True: approachMatrix(wealth,likert[5][impactJob-1],self.demographics['wealth'] if ceiling else 1.),
                      False: noChangeMatrix(wealth)},
               False: None}
            if config.getint('Actors','economy_threshold',fallback=0) > 0:
                tree[True][True] = {'if': greaterThanRow(makeFuture(self.demographics['home'],'economy'),
                    toLikert(config.getint('Actors','economy_threshold',fallback=0))),
                    True: tree[True][True], 
                    False: noChangeMatrix(wealth)}
            if config.getint('Simulation','phase',fallback=1) < 3:
                tree = {'if': trueRow(alive),
                        True: tree,
                        False: noChangeMatrix(wealth)}
                if impactNoJob > 0: 
                    tree[True][False] = approachMatrix(wealth,likert[5][impactNoJob-1],0.)
                else:
                    tree[True][False] = noChangeMatrix(wealth)
            else:
                if impactNoJob > 0: 
                    tree[False] = approachMatrix(wealth,likert[5][impactNoJob-1],0.)
                else:
                    tree[False] = noChangeMatrix(wealth)
            world.setDynamics(wealth,self.nop,makeTree(tree),codePtr=True)

            # TODO: What if you can work if you're at the shelter?
            # Going home allows you to work again
            logEdge('Actor-moveTo-home','Actor\'s resources','often','If an actor moves back home s/he can still go to work and earn money')
            #//GT: edge 37; from 30; to 24; 1 of 1; next 17 lines
            tree = {'if': trueRow(job),
               True: approachMatrix(wealth,likert[5][impactJob-1],1.),
               False: None} 
            if config.getint('Simulation','phase',fallback=1) < 3:
                tree = {'if': trueRow(alive),
                        True: tree,
                        False: noChangeMatrix(wealth)}
                if impactNoJob > 0: 
                    tree[True][False] = approachMatrix(wealth,likert[5][impactNoJob-1],0.)
                else:
                    tree[True][False] = noChangeMatrix(wealth)
            else:
                if impactNoJob > 0: 
                    tree[False] = approachMatrix(wealth,likert[5][impactNoJob-1],0.)
                else:
                    tree[False] = noChangeMatrix(wealth)
            world.setDynamics(wealth,goHome,makeTree(tree),codePtr=True)
            
        if impactNoJob > 0: 
            if config.getboolean('Shelter','exists') and not config.getboolean('Shelter','job'):
                logEdge('Actor-moveTo-shelter','Actor\'s resources','often','Going to a shelter can prevent an actor from going to work and earning resources')
                # 
                for index,action in actShelter.items():
                    tree = makeTree(approachMatrix(wealth,likert[5][impactNoJob-1],0.))
                    world.setDynamics(wealth,action,tree,codePtr=True)

        elif config.getboolean('Shelter','exists') and not config.getboolean('Shelter','job') and config.getint('Simulation','phase',fallback=1) == 1:
            # Phase 1 did not care about "impactNoJob" config
            for index,action in actShelter.items():
                tree = makeTree(approachMatrix(wealth,likert[5][impactNoJob-1],0.))
                world.setDynamics(wealth,action,tree,codePtr=True)

        if config.getboolean('Actors','evacuation'):
            cost = config.getint('Actors','evacuation_cost')
            if cost > 0:
                logEdge('Actor-evacuate','Actor\'s resources','often','Evacuating costs resources')
                #//GT: edge 38; from 29; to 24; 1 of 1; next 5 lines
                cost = likert[5][cost-1]
                tree = makeTree({'if': thresholdRow(wealth,cost),
                                 True: incrementMatrix(wealth,-cost),
                                 False: setToConstantMatrix(wealth,0.)})
                world.setDynamics(wealth,actEvacuate,tree,codePtr=True)

            if config.getint('Actors','evacuation_unemployment') > 0:
                # Might lose job
                logEdge('Actor-evacuate','Actor\'s employed','sometimes','If an actor evacuates it might lose its job')
                #//GT: edge 39; from 29; to 17; 1 of 1; next 9 lines
                prob = likert[5][config.getint('Actors','evacuation_unemployment')-1]
                tree = {'if': trueRow(job),
                    True: {'distribution': [(noChangeMatrix(job),1.-prob),
                                            (setFalseMatrix(job),prob)]},
                    False: noChangeMatrix(job)}
                if config.getint('Simulation','phase',fallback=1) < 3:
                    tree = {'if': trueRow(alive),
                                     True: tree,
                                     False: noChangeMatrix(job)}

            else:
                tree = noChangeMatrix(job)
            world.setDynamics(job,actEvacuate,makeTree(tree),codePtr=True)

        if config.getboolean('Actors','prorisk'):
            # Effect of doing good
            logEdge('Actor-decreaseRisk','Region\'s risk','often','Performing prosocial behavior reduces the risk in the target region')
            #//GT: edge 40; from 31; to 1; 1 of 1; next 5 lines
            benefit = likert[5][config.getint('Actors','prorisk_benefit')-1]
            for region,action in actGoodRisk.items():
                key = stateKey(region,'risk')
                tree = makeTree(approachMatrix(key,benefit,self.world.agents[region].risk))
                world.setDynamics(key,action,tree,codePtr=True)

            cost = config.getint('Actors','prorisk_cost_risk')
            if cost > 0:
                logEdge('Actor-decreaseRisk','Actor\'s risk','often','Performing prosocial behavior exposes the actor to additional risk')
                #//GT: edge 41; from 31; to 25; 1 of 1; next 3 lines
                for region,action in actGoodRisk.items():
                    tree = makeTree(approachMatrix(risk,likert[5][cost-1],1.))
                    world.setDynamics(risk,action,tree,codePtr=True)

            logEdge('Actor-decreaseRisk','Actor\'s resources','often','Performing prosocial behavior means no income')
            #//GT: edge 42; from 31; to 24; 1 of 1; next 3 lines
            if config.getint('Simulation','phase',fallback=1) >= 3 and impactNoJob > 0: 
                tree = makeTree(approachMatrix(wealth,likert[5][impactNoJob-1],0.))
                world.setDynamics(wealth,action,tree,codePtr=True)
                    
        if config.getboolean('Actors','proresources'):
            # Effect of doing good
            logEdge('Actor-giveResources','Region\'s economy','often','Performing prosocial behavior benefits the economy in the target region')
            #
            benefit = likert[5][config.getint('Actors','proresources_benefit')-1]
            for region,action in actGoodResources.items():
                key = stateKey(region,'economy')
                tree = makeTree(approachMatrix(key,benefit,self.world.agents[region].economy))
                world.setDynamics(key,action,tree,codePtr=True)

            cost = config.getint('Actors','proresources_cost_risk')
            if cost > 0:
                logEdge('Actor-giveResources','Actor\'s risk','often','Performing prosocial behavior exposes the actor to additional risk')
                #
                for region,action in actGoodResources.items():
                    tree = makeTree(approachMatrix(risk,likert[5][cost-1],1.))
                    world.setDynamics(risk,action,tree,codePtr=True)

        if config.getboolean('Actors','antiresources'):
            # Effect of doing bad
            logEdge('Actor-takeResources','Actor\'s resources','often','Performing antisocial behavior increases the actor\'s resources')
            #//GT: edge 43; from 32; to 24; 1 of 1; next 4 lines
            benefit = likert[5][config.getint('Actors','antiresources_benefit')-1]
            for region,action in actBadResources.items():
                tree = makeTree(approachMatrix(wealth,benefit,self.demographics['wealth'] if ceiling else 1.))
                world.setDynamics(wealth,action,tree,codePtr=True)

            logEdge('Actor-takeResources','Actor\'s risk','often','Performing antisocial behavior exposes the actor to additional risk')
            #//GT: edge 44; from 32; to 25; 1 of 1; next 7 lines
            cost = config.getint('Actors','antiresources_cost_risk')
            if cost > 0:
                for region,action in actBadResources.items():
                    tree = makeTree({'if': equalRow(stateKey('Nature','phase'),'none'),
                                     True: approachMatrix(risk,likert[5][3],1.),
                                     False: approachMatrix(risk,likert[5][cost-1],1.)})
                    world.setDynamics(risk,action,tree,codePtr=True)

        if config.getboolean('Actors','antirisk'):
            # Effect of doing bad
            logEdge('Actor-increaseRisk','Region\'s risk','often','Performing antisocial behavior increases the region\'s risk')
            #
            benefit = likert[5][config.getint('Actors','antirisk_benefit')-1]
            for region,action in actBadRisk.items():
                key = stateKey(region,'risk')
                tree = makeTree(approachMatrix(key,benefit,1.))
                world.setDynamics(key,action,tree,codePtr=True)

            cost = config.getint('Actors','antirisk_cost_risk')
            if cost > 0:
                logEdge('Actor-takeResources','Actor\'s risk','often','Performing antisocial behavior exposes the actor to additional risk')
                #
                for region,action in actBadRisk.items():
                    tree = makeTree({'if': equalRow(stateKey('Nature','phase'),'none'),
                                     True: approachMatrix(risk,likert[5][3],1.),
                                     False: approachMatrix(risk,likert[5][cost-1],1.)})
                    world.setDynamics(risk,action,tree,codePtr=True)

        if self.demographics.get('pet',False) and config.getboolean('Shelter','exists'):
            # Process shelters' pet policy
            logEdge('Actor-moveTo-shelter','Actor\'s pet','sometimes','Pets die if an actor goes to a shelter that does not allow pets')
            #//GT: edge 56; from 28; to 18; 1 of 1; next 8 lines
            logEdge('Region\'s shelterPets','Actor\'s pet','sometimes','Pets die if an actor goes to a shelter that does not allow pets')
            #//GT: edge 57; from 4; to 18; 1 of 1; next 6 lines
            for index,action in actShelter.items():
                region = Region.nameString % (int(index))
                tree = makeTree({'if': trueRow(stateKey(region,'shelterPets')),
                                    True: noChangeMatrix(pet),
                                    False: setFalseMatrix(pet)})
                world.setDynamics(pet,action,tree,codePtr=True)

        # Reward
        sigma = config.getint('Actors','reward_sigma')
        self.Rweights = {'childrenHealth': 0.,'pet':0.}
        logNode('Actor\'s priority of health','Importance of health','Real in [0-1]','Static')
        #//GT: node 34; 1 of 1; next 8 lines
        mean = config.getint('Actors','reward_health_%s' % (self.demographics['gender']))
        if mean == 0:
            self.Rweights['health'] = 0.
        else:
            if sigma > 0:
                self.Rweights['health'] = sampleNormal(mean,sigma)
            else:
                self.Rweights['health'] = likert[5][mean-1]

            logEdge('Actor\'s priority of health','Actor\'s Expected Reward','often','This priority moderates the dependency between Actor\'s health and its Expected Reward')
            #//GT: edge 45; from 34; to 35; 1 of 1; next 3 lines
            logEdge('Actor\'s health','Actor\'s Expected Reward','often','Actors are incentivized to avoid decreases to their own health levels')
            #//GT: edge 46; from 21; to 35; 1 of 1; next 1 lines
            self.setReward(maximizeFeature(health,self.name),self.Rweights['health'])


        logNode('Actor\'s priority of resources','Importance of resources','Real in [0-1]','Static')
        #//GT: node 36; 1 of 1; next 8 lines
        mean = config.getint('Actors','reward_wealth_%s' % (self.demographics['gender']))
        if mean == 0:
            self.Rweights['resources'] = 0.
        else:
            if sigma > 0:
                self.Rweights['resources'] = sampleNormal(mean,sigma)
            else:
                self.Rweights['resources'] = likert[5][mean-1]

            logEdge('Actor\'s priority of resources','Actor\'s Expected Reward','often','This priority moderates the dependency between Actor\'s resources and its Expected Reward')
            #//GT: edge 47; from 36; to 35; 1 of 1; next 3 lines
            logEdge('Actor\'s resources','Actor\'s Expected Reward','often','Actors are incentivized to increase their resources')
            #//GT: edge 48; from 24; to 35; 1 of 1; next 1 lines
            self.setReward(maximizeFeature(wealth,self.name),self.Rweights['resources'])

        if self.demographics['kids'] > 0:
            mean = config.getint('Actors','reward_kids_%s' % (self.demographics['gender']))
            if mean > 0:
                logNode('Actor\'s priority of childrenHealth','Importance of children\'s health','Real in [0-1]','Static')
                #//GT: node 41; 1 of 1; next 4 lines
                if sigma > 0:
                    self.Rweights['childrenHealth'] = sampleNormal(mean,sigma)
                else:
                    self.Rweights['childrenHealth'] = likert[5][mean-1]

                logEdge('Actor\'s priority of childrenHealth','Actor\'s Expected Reward','often','This priority moderates the dependency between Actor\'s childrenHealth and its Expected Reward')
                #//GT: edge 54; from 41; to 35; 1 of 1; next 3 lines
                logEdge('Actor\'s childrenHealth','Actor\'s Expected Reward','often','Actors with children are incentivized to avoid decreases to their children\'s health levels')
                #//GT: edge 55; from 40; to 35; 1 of 1; next 1 lines
                self.setReward(maximizeFeature(kidHealth,self.name),self.Rweights['childrenHealth'])

        if self.demographics.get('pet',False):
            mean = config.getint('Actors','reward_pets')
            if mean > 0:
                logNode('Actor\'s priority of pets','Importance of pet\'s wellbeing','Real in [0-1]','Static')
                #//GT: node 42; 1 of 1; next 4 lines
                if sigma > 0:
                    self.Rweights['pet'] = sampleNormal(mean,sigma)
                else:
                    self.Rweights['pet'] = likert[5][mean-1]

                logEdge('Actor\'s priority of pets','Actor\'s Expected Reward','often','This priority moderates the dependency between Actor\'s pets and its Expected Reward')
                #//GT: edge 58; from 42; to 35; 1 of 1; next 3 lines
                logEdge('Actor\'s pet','Actor\'s Expected Reward','often','Actors are incentivized to avoid having a pet die')
                #//GT: edge 59; from 18; to 35; 1 of 1; next 1 lines
                self.setReward(maximizeFeature(pet,self.name),self.Rweights['pet'])

        logNode('Actor\'s priority of neighbors','Importance of neighbors\' wellbeing','Real in [0-1]','Static')
        #//GT: node 37; 1 of 1; next 12 lines
        mean = config.getint('Actors','altruism_neighbors_%s' % (self.demographics['religion']))
        if mean == 0:
            self.Rweights['neighbors'] = 0.
        else:
            if sigma > 0:
                self.Rweights['neighbors'] = sampleNormal(mean,sigma)
            else:
                self.Rweights['neighbors'] = likert[5][mean-1]
            try:
                self.Rweights['neighbors'] /= float(len(neighbors))
            except ZeroDivisionError:
                pass

            logEdge('Actor\'s priority of neighbors','Actor\'s Expected Reward','often','This priority moderates the dependency between Region\'s risk and the actor\'s Expected Reward')
            #//GT: edge 49; from 37; to 35; 1 of 1; next 4 lines
            logEdge('ActorBeliefOfRegion\'s risk','Actor\'s Expected Reward','often','Altruistic actors derive reward from the risk level of their home region')
            #//GT: edge 50; from 12; to 35; 1 of 3; next 2 lines
            self.setReward(minimizeFeature(stateKey(self.demographics['home'],'risk'),self.name),
                           self.Rweights['neighbors'])

        if config.getboolean('Actors','beliefs'):
            # Observations
            self.uncertainKeys = {stateKey('Nature','category'),stateKey(self.name,'risk'),stateKey(self.demographics['home'],'risk')}
            for shelter in shelters:
                self.uncertainKeys.add(stateKey('Region%s' % (shelter),'shelterRisk'))
            evolve = ActionSet([Action({'subject': 'Nature','verb': 'evolve'})])
            if config.getint('Simulation','phase',fallback=1) == 1:
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

            logNode('Actor\'s information distortion','Over/underestimation in information received about hurricane severity','"none" / "over" / "under"','Static')
            #//GT: node 38; 1 of 1; next 7 lines
            distortion = Distribution({'over': likert[5][config.getint('Actors','category_over')-1],
                                       'under': likert[5][config.getint('Actors','category_under')-1]})
            distortion['none'] = 1.-distortion['over']-distortion['under']
            self.distortion = distortion.sample()
#            self.world.defineState(self.name,'distortion',list,['none','over','under'],
#                description='Over/underestimation in information received about hurricane severity',codePtr=True)
#            self.setState('distortion',self.distortion)

            if config.getint('Actor','memory',fallback=0) > 0:
                logNode('Actor\'s memory','How much an actor remembers about personal experience in previous hurricanes','Real in [0-1]')
                #
                self.memory = likert[5][config.getint('Actor','memory')-1]

            else:
                self.memory = 0.
                
            logNode('Actor\'s perceivedCategory','Information that actor receives about the hurricane\'s current severity','Integer in [0-5]')
            #//GT: node 39; 1 of 1; next 14 lines
            if config.getint('Simulation','phase',fallback=1) < 3 or isinstance(self.world.state,VectorDistributionSet):
                omega = self.defineObservation('perceivedCategory',domain=int,codePtr=True,
                                               description='Perception of Nature\'s category')
            else:
                omega = self.world.defineState(self.name,'perceivedCategory',domain=int,codePtr=True,
                                               description='Perception of Nature\'s category')
                self.omega |= {omega,stateKey(self.name,'health'),stateKey(self.name,'employed'),
                    stateKey('Nature','phase'),stateKey('Nature','location'),stateKey('Nature','days')}
                if self.demographics['kids'] > 0:
                    self.omega.add(stateKey(self.name,'childrenHealth'))
                for shelter in shelters:
                    self.omega.add(stateKey(Region.nameString % (int(shelter)),'shelterOccupancy'))
                self.O = {}
            self.setState('perceivedCategory',0)

            logEdge('Nature\'s category','Actor\'s perceivedCategory','often','Actors received accurate or off-by-1 reports of the hurricane category with some probability')
            #//GT: edge 51; from 10; to 39; 1 of 2; next 29 lines
            logEdge('Actor\'s information distortion','Actor\'s perceivedCategory','often','Category information is possibly an over/underestimate of real value')
            #//GT: edge 52; from 38; to 39; 1 of 2; next 27 lines
            distortionProb = likert[5][config.getint('Actors','category_distortion')-1]
            if config.getint('Simulation','phase',fallback=1) < 3 or isinstance(self.world.state,VectorDistributionSet):
                real = stateKey('Nature','category')
            else:
                # "Observation" of updated hurricane
                real = stateKey('Nature','category',True)
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
            if config.getint('Simulation','phase',fallback=1) < 3 or isinstance(self.world.state,VectorDistributionSet):
                self.setO('perceivedCategory',evolve,makeTree(tree))
                self.setO('perceivedCategory',None,makeTree(setToConstantMatrix(omega,-1)))
            else:
                self.world.setDynamics(omega,evolve,makeTree(tree))
                self.world.setDynamics(omega,True,makeTree(setToConstantMatrix(omega,-1)))

            if config.getint('Simulation','phase',fallback=1) == 1:        
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
    def setHealthDynamics(self,up,down,codePtr=True): 
        logEdge('Actor\'s risk','Actor\'s health','often','Higher levels of personal risk lead to higher likelihoods and higher severity of health loss for themselves')
        #//GT: edge 32; from 25; to 21; 1 of 1; next 24 lines
        if self.config.getint('Simulation','phase',fallback=1) < 3:
            tree = {'if': thresholdRow(makeFuture(stateKey(self.name,'risk')),likert[5][:]),
                    0: approachMatrix(stateKey(self.name,'health'),up,self.health)}
        else:
            tree = {'if': thresholdRow(stateKey(self.name,'risk'),likert[5][:]),
                    0: approachMatrix(stateKey(self.name,'health'),up,self.health)}
        for level in range(1,6):
            value = likert[5][level-1]
            dist = [(approachMatrix(stateKey(self.name,'health'),down,0.),value),
                    (approachMatrix(stateKey(self.name,'health'),up,self.health),1.-value)]
            tree[level] = {'distribution': dist}
        if self.config.getint('Simulation','phase',fallback=1) < 3:
            tree = {'if': trueRow(stateKey(self.name,'alive')),
                             True: tree, False: setToConstantMatrix(stateKey(self.name,'health'),0.)}
        if self.horizon <= 2:
            # Make sure even the most short-sighted actors are aware that the hurricane will impact their health
            if self.config.getint('Simulation','phase',fallback=1) == 1:
                self.world.setDynamics(stateKey(self.name,'health'),Action({'subject': self.name}),makeTree(tree),codePtr=codePtr)
            else:
                for action in self.actions:
                    self.world.setDynamics(stateKey(self.name,'health'),action,makeTree(tree),codePtr=codePtr)
        else:
            self.world.setDynamics(stateKey(self.name,'health'),ActionSet([Action({'subject': 'Nature','verb': 'evolve'})]),
                makeTree(tree),codePtr=codePtr)

    def makeFriend(self,friend,config):
        logNode('Actor friendOf Actor','Friendship relationship between two actors','Boolean','Static')
        #//GT: node 54; 1 of 1; next 1 lines
        self.friends.add(friend.name)

        if self.config.getint('Simulation','phase',fallback=1) == 1:
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
        #//GT: node 1; 1 of 2; next 25 lines
        friendMax = config.getint('Actors','friends')
        friendMin = config.getint('Actors','friendMin',fallback=0)
        if len(self.friends) < friendMax:
            # Social network
            if 'friendOf' in self.world.relations:
                # Backward compatibility with saved social network
                friendCount = {}
                for key in self.world.relations['friendOf']:
                    relation = key2relation(key)
                    if relation['subject'] == self.name:
                        self.friends.add(relation['object'])
                    else:
                        friendCount[relation['subject']] = friendCount.get(relation['subject'],0)+1
            else:
                friendCount = {agent.name: len(agent.friends) for agent in population}
            numFriends = random.randint(max(friendMin,len(self.friends)),friendMax)
            possibles = [agent.name for agent in population
                         if friendCount.get(agent.name,0) < friendMax
                         and agent.name not in self.friends]
            if len(population) > 1:
                # For illustrative graph purposes, we allow links to self, but not otherwise
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
                if other in self.friends:
                    R += self.Rweights['friends']
                if R > 1e-8:
                    self.setReward(maximizeFeature(stateKey(other.name,'health'),self.name),R)
        
    def _initializeBeliefs(self,config):
        # Beliefs
        friends = set()
        population = {a for a in self.world.agents.values() if isinstance(a,self.__class__)}
        neighbors = self.getNeighbors()
        if config.getboolean('Simulation','graph',fallback=False):
            if len(population) == 1:
                neighbors.add(self.name)
            for name in neighbors:
                if self.config.getint('Simulation','phase',fallback=1) == 1:
                    key = self.world.defineRelation(self.name,name,'neighbor',bool,codePtr=True)
                    self.world.setFeature(key,True)
                if self.Rweights['neighbors'] > 0.:
                    self.setReward(maximizeFeature(key,self.name),1.)

        regions = {self.demographics['home']}
        if config.getint('Simulation','phase',fallback=1) == 3:
            regions |= set(self.shelters)
            regions.add(self.world.agents[self.demographics['home']].evacuationPath()[-1])

        include = set()
        altNeighbor = config.getint('Actors','altruism_neighbors_%s' % (self.demographics['religion']))
        altFriend = config.getint('Actors','altruism_friends_%s' % (self.demographics['religion']))
        for key in self.world.state.keys():
            if isBinaryKey(key):
                if config.getint('Simulation','phase',fallback=1) != 2:
                    agent = key2relation(key)['subject']
                else:
                    continue
            elif key == CONSTANT:
                continue
            else:
                agent = state2agent(key)
            if agent == self.name:
                if not isModelKey(key):
                    logNode('ActorBeliefOfActor\'s risk','Belief about own personal risk','Probability Distribution over reals in [0-1]')
                    #//GT: node 33; 1 of 1; next 4 lines
                    if not config.getboolean('Simulation','graph',fallback=False):
                        include.add(key)
                    elif state2feature(key) == 'risk':
                        include.add(key)

                    elif isBinaryKey(key):
                        include.add(key)

    
            elif agent == 'Nature':
                if not isModelKey(key):
                    logNode('ActorBeliefOfNature\'s category','Belief about hurricane severity','Probability Distribution over [0-5]')
                                #//GT: node 11; 1 of 1; next 4 lines
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
                if not config.getboolean('Simulation','graph',fallback=False) and config.getint('Simulation','phase',fallback=1) == 1:
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
                if agent in regions:
                    if not isModelKey(key):
                        logNode('ActorBeliefOfRegion\'s risk','Belief about risk level of region','Probability Distribution over reals in [0-1]')
                        #//GT: node 12; 1 of 1; next 6 lines
                        logNode('ActorBeliefOfRegion\'s shelterRisk','Belief about risk level at shelter','Probability Distribution over reals in [0-1]')
                        #//GT: node 13; 1 of 1; next 4 lines
                        if not config.getboolean('Simulation','graph',fallback=False):
                            include.add(key)
                        elif state2feature(key) == 'risk':
                            include.add(key)

                elif agent in self.shelters:
                    if state2feature(key)[:7] == 'shelter':
                        if not config.getboolean('Simulation','graph',fallback=False):
                            include.add(key)

        beliefs = self.resetBelief(include=include)

    def memberOf(self,state):
        inGroup = []
        for group in self.groups:
            key = binaryKey(self.name,group,'memberOf')
            if self.world.getFeature(key,state,unique=True):
                inGroup.append(group)
        return inGroup
    
    def getActions(self,state,actions=None):
        for group in self.memberOf(state):
            key = stateKey(group,ACTION)
            if key in state:
                action = self.world.getFeature(key,state,unique=True)
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
    
    def projectObservations(self,s,actions,select=None):
        logEdge('Nature\'s category','Actor\'s perceivedCategory','often','The information received influences the actors\' subsequent belief')
        #//GT: edge 51; from 10; to 39; 2 of 2; next 11 lines
        logEdge('Actor\'s information distortion','Actor\'s perceivedCategory','often','The information received influences the actors\' subsequent belief')
        #//GT: edge 52; from 38; to 39; 2 of 2; next 9 lines
        futures = set()
        for omega,table in self.O.items():
            if actions in table:
                futures.add(omega)
                tree = table[actions]
                if select is True:
                    tree = tree.sample()
                s *= tree
        return futures

    def projectState(self,s,actions,trueState=None,select=None,debug=False):
        extra = set()
        if len(actions) == 1:
            self.world.setFeature(actionKey(actions['subject']),actions,s)
            turn = actions['subject']
        else:
            for action in actions:
                self.world.setFeature(actionKey(action['subject']),ActionSet(action),s)
                if action['subject'] != self.name:
                    extra.add(actionKey(action['subject']))
                    key = binaryKey(action['subject'],'Group%s' % (self.demographics['home']),'memberOf')
                    extra.add(key)
                    if trueState is not None:
                        self.world.setFeature(key,self.world.getFeature(key,trueState),s)
                turn = action['subject']
        if turn[:5] == 'Actor':
            turn = 'Actor'
        elif turn == 'System':
            if trueState is not None:
                # In case there's an election
                self.world.setState('System','ethnicBias',self.world.getState('System','ethnicBias',trueState),s)
                self.world.setState('System','religiousBias',self.world.getState('System','religiousBias',trueState),s)
        # Determine what features in this state are going to possibly change
        order = [{k for k in keySet if k in s} for keySet in self.world.dependency.getEvaluation()]
        order = [keySet for keySet in order if keySet]
        # Project individual effects
        observable = {key for key in s.keys() if state2feature(key) == 'shelterOccupancy'}
        futures = set()
        for i in range(len(order)):
            keySet = order[i]
            futures |= keySet
            for key in keySet:
                trees = [self.world.dynamics[action][key] for action in actions if action in self.world.dynamics and key in self.world.dynamics[action]]
                if key in observable and trueState is not None:
                    s.join(makeFuture(key),trueState[key])
                    continue
                elif len(trees) == 0:
                    try:
                        trees = [self.world.dynamics[key][True]]
                    except KeyError:
                        value = s[key]
                        if len(value) == 1:
                            s.join(makeFuture(key),value)
                        else:
                            substate = s.keyMap[key]
                            dist = s.distributions[substate]
                            future = makeFuture(key)
                            for vector in dist.domain():
                                prob = dist[vector]
                                del dist[vector]
                                vector[future] = vector[key]
                                dist[vector] = prob
                            s.keyMap[future] = substate
                        continue
                if len(trees) == 1:
                    if select is True:
                        tree = trees[0].sample()
                    elif select == 'max':
                        tree = trees[0].sample(True)
                    else:
                        tree = trees[0]
                    s *= tree
                else:
                    assert len(trees) > 1
                    cumulative = None
                    for tree in trees:
                        matrix = tree[s]
                        if cumulative is None:
                            cumulative = copy.deepcopy(matrix)
                        else:
                            cumulative.makeFuture([key])
                            cumulative *= matrix
                    if select is True:
                        s.__imul__(cumulative,True)
                    else:
                        s *= cumulative
        s.simpleRollback(futures)
        if extra:
            s.deleteKeys(extra)
        # Update turn
        dynamics = self.world.deltaTurn(s,actions)
        for key,tree in dynamics.items():
            assert len(tree) == 1
            s *= tree[0]
        s.simpleRollback(set(dynamics.keys()))
        if trueState is not None:
            # Things I directly observe
            observable = {stateKey(self.name,'health'),stateKey(self.name,'employed'),stateKey(self.name,'perceivedCategory'),
                stateKey('Nature','location'),stateKey('Nature','phase'),stateKey('Nature','days')}
            if stateKey(self.name,'childrenHealth') in self.world.variables:
                observable.add(stateKey(self.name,'childrenHealth'))
            for omega in observable:
                value = trueState[omega]
                assert len(value) == 1
                s[omega] = value.first()
                if len(s[omega]) > 1:
                    self.world.printState(s)
                    raise RuntimeError
        return s

    def updateBeliefs(self,trueState,actions,debug=False):
        if self.config.getint('Simulation','phase',fallback=1) == 1:
            return Agent.updateBeliefs(self,trueState,actions)
        elif self.config.getint('Simulation','phase',fallback=1) >= 3:
            hurricane = self.world.getState('Nature','phase',trueState,unique=True)
            beliefs = self.getBelief(trueState)
            if isinstance(beliefs,dict):
                assert len(beliefs) == 1
                model,beliefs = next(iter(beliefs.items()))
            else:
                model = self.world.getModel(self.name,trueState)
            if hurricane == 'none':
                # No hurricane, so no uncertainty
                newDists = {}
                for substate,dist in beliefs.distributions.items():
                    vec = dist.first()
                    dist.clear()
                    for key in vec.keys():
                        if key != CONSTANT:
                            if len(dist) > 0:
                                # Already put one key in
                                newDists[key] = trueState[key]
                                del beliefs.keyMap[key]
                            elif isinstance(trueState,VectorDistributionSet):
                                # Put this key back in
                                vec = KeyedVector({keys.CONSTANT:1.,key: trueState[key].first()})
                                dist[vec] = 1.
                            else:
                                # Put this key back in
                                vec = KeyedVector({keys.CONSTANT:1.,key: trueState[key]})
                                dist[vec] = 1.
                substate = 0
                for key,value in newDists.items():
                    while substate in beliefs.distributions:
                        substate += 1
                    if isinstance(value,Distribution):
                        assert len(value) == 1
                        value = value.first()
                    beliefs.distributions[substate] = VectorDistribution({KeyedVector({keys.CONSTANT:1.,key: value}):1.})
                    beliefs.keyMap[key] = substate
            else:
                logEdge('Actor\'s perceivedCategory','ActorBeliefOfNature\'s category','often','The information received influences the actors\' subsequent belief')
                #//GT: edge 91; from 39; to 11; 1 of 1; next 75 lines
                knownActions = set()
                for action in actions:
                    if actionKey(action['subject']) in beliefs:
                        knownActions.add(action)
                if isinstance(trueState,KeyedVector):
                    print(self.name)
                    self.world.printState(beliefs)
                    for substate,dist in beliefs.distributions.items():
                        if len(dist) > 1:
                            print(sorted(substate,dist.keys()))
                            raise RuntimeError
                    newdist = VectorDistribution()
                    for vector,prob in beliefs.worlds():
                        outcome = self.world.step(knownActions,vector,keySubset=vector.keys(),updateBeliefs=False)
                        for newvec in outcome.domain():
                            newdist.addProb(newvec,outcome[newvec]*prob)
                    print(len(newdist))
                    for key in self.omega:
                        for newvec in newdist.domain():
                            if newvec[key] == trueState[key]:
                                break
                        else:
                            print(key)
                            raise ValueError
                        change = False
                        for newvec in newdist.domain():
                            if newvec[key] != trueState[key]:
                                del newdist[newvec]
                                change = True
                        if change:
                            newdist.normalize()
                            print(key,len(newdist))
#                    for newvec in newdist.domain():
#                        print(newdist[newvec])
#                        print(dict(newvec))
                    raise RuntimeError
                else:
                    self.projectState(beliefs,actions.__class__(knownActions))
                    if actions == self.world.agents['Nature'].evolution:
                        self.projectObservations(beliefs,actions)
                        # Things I directly observe
                        observable = {stateKey(self.name,'health'),stateKey(self.name,'employed'),
                            stateKey('Nature','location'),stateKey('Nature','phase'),stateKey('Nature','days')}
                        for region in self.shelters:
                            if stateKey(region,'shelterOccupancy') in self.world.variables:
                                observable.add(stateKey(region,'shelterOccupancy'))
                        if stateKey(self.name,'childrenHealth') in self.world.variables:
                            observable.add(stateKey(self.name,'childrenHealth'))
                        for omega in observable:
                            value = trueState[omega]
                            if isinstance(value,Distribution):
                                assert len(value) == 1
                                value = value.first()
                            if value in beliefs[omega].domain():
                                beliefs[omega] = value
                            elif state2feature(omega) == 'shelterOccupancy':
                                dist = beliefs.distributions[beliefs.keyMap[omega]]
                                for vector in dist.domain():
                                    prob = dist[vector]
                                    del dist[vector]
                                    vector[omega] = value
                                    dist[vector] = prob
                            else:
                                raise ValueError('True value %s not in %s\'s beliefs about %s' % (value,self.name,omega))
                        omega = stateKey(self.name,'perceivedCategory')
                        if isinstance(trueState,VectorDistributionSet):
                            beliefs.simpleRollback({omega})
                        realOmega = trueState[makeFuture(omega)]
                        if isinstance(realOmega,Distribution):
                            realOmega = realOmega.first()
                        if realOmega not in beliefs[omega]:
                            print('Category:',trueState['Nature\'s category'])
                            self.world.printState(beliefs)
                            raise RuntimeError
                        beliefs[omega] = realOmega

                    else:
                        observable = {stateKey(self.name,'health'),stateKey(self.name,'employed')}
                        if stateKey(self.name,'childrenHealth') in self.world.variables:
                            observable.add(stateKey(self.name,'childrenHealth'))
                        for omega in observable:
                            value = trueState[omega]
                            if isinstance(value,Distribution):
                                assert len(value) == 1
                                beliefs[omega] = value.first()
                            else:
                                beliefs[omega] = value

                if len(beliefs) > 2:
                    self.world.printState(beliefs)
                    raise RuntimeError

                assert beliefs[stateKey('Nature','category')].expectation() is not None

        else:
            logEdge('Actor\'s perceivedCategory','ActorBeliefOfNature\'s category','often','The information received influences the actors\' subsequent belief')
            #
            beliefs = self.getBelief(trueState)
            if isinstance(beliefs,dict):
                assert len(beliefs) == 1
                model,beliefs = next(iter(beliefs.items()))
            else:
                model = self.world.getModel(self.name,trueState)
            knownActions = actions.__class__({action for action in actions if actionKey(action['subject']) in beliefs})
            self.world.step(knownActions,beliefs,keySubset=beliefs.keys(),updateBeliefs=False)
            omega = stateKey(self.name,'perceivedCategory')
            omegaState = beliefs.keyMap[omega]
            real = trueState[makeFuture(omega)].first()
            debug = False
            for substate,dist in beliefs.distributions.items():
                if len(dist) > 1:
                    change = False
                    for key,prob in sorted(dict.items(dist),key=lambda i: i[1]):
                        vec = dist._domain[key]
                        for key in vec.keys():
                            if key == CONSTANT:
                                pass
                            elif key == omega:
                                if vec[key] != real:
                                    del dist[vec]
                                    change = True
                                    break
                            elif key not in self.uncertainKeys or real == 0:
                                # If this is not an uncertain key, or there is no hurricane
                                if vec[key] != trueState[key].first():
                                    del dist[vec]
                                    change = True
                                    break
                        if len(dist) == 1:
                            break
                    if change: 
                        dist.normalize()
                    # Delete any incorrect beliefs that are below threshold
                    change = False
                    threshold = self.config.getfloat('Actors','likelihood_threshold',fallback=0.001)
                    for key,prob in list(dict.items(dist)):
                        if prob < threshold:
                            vec = dist._domain[key]
                            for subkey in vec.keys():
                                if subkey != CONSTANT and vec[subkey] != trueState[subkey].first():
                                    # This vector does not represent true state
                                    dict.__delitem__(dist,key)
                                    del dist._domain[key]
                                    change = True
                                    break
                    if change:
                        dist.normalize()

        assert len(beliefs) <= 2
        self.setAttribute('beliefs',beliefs,model)
        return set()

    def recvMessage(self,key,msg,myScale=1.,yrScaleOpt=1.,yrScalePess=1.,model=None):
        logEdge('Actor friendOf Actor','ActorBeliefOfNature\'s category','often','Actors share their beliefs about the hurricane\'s category with their friends on a daily basis and their beliefs are influence by the incoming messages')
        #//GT: edge 94; from 54; to 11; 2 of 2; next 61 lines
        beliefs = self.getBelief()
        if model is None:
            if isinstance(beliefs,dict):
                assert len(beliefs) == 1,'Unable to incorporate messages when identity is uncertain'
                model,myBelief = next(iter(beliefs.items()))
            else:
                myBelief = beliefs
                model = self.world.getModel(self.name)
        else:
            myBelief = beliefs[model]
        dist = myBelief[key]
        old = dist.expectation()
        if old is None:
            logging.error('%s [%s] has null belief on %s' % (self.name,model,key))
        elif isinstance(msg,list):
            # Phase 2 messages
            if self.correctInfo:
                # Used for hypothetical prescription
                msg.append(self.world.getFeature(key))
            total = Distribution({el: myScale*dist[el] for el in dist.domain()})
            for bel in msg:
                scale = yrScaleOpt if bel.expectation() > old else yrScalePess
                for value in bel.domain():
                    total.addProb(value,scale*bel[value])
            total.normalize()
            logging.info('%s new belief in %s: %s' % (self.name,key,total))
            if self.config.getint('Simulation','phase',fallback=1) == 3:
                newvalues = set(total.domain())
                oldvalues = {}
                subbelief = myBelief.distributions[myBelief.keyMap[key]]
                for vec in subbelief.domain():
                    assert vec[key] not in oldvalues
                    subbelief[vec] = total[vec[key]]
                    oldvalues[vec[key]] = vec
                    newvalues.remove(vec[key])
                assert len(subbelief)+len(newvalues) == len(total)
                if newvalues:
                    domain = sorted(oldvalues.keys())
                    for el in newvalues:
                        if el < domain[0]:
                            # Even less severe than I could possibly imagine, so increase belief in best possible imagined
                            subbelief[oldvalues[domain[0]]] += total[el]
                        elif el > domain[-1]:
                            # Even more severe than I could possibly imagine, so increase belief in worst possible imagined
                            subbelief[oldvalues[domain[-1]]] += total[el]
                        else:
                            # Should not get here!
                            raise RuntimeError
                    subbelief.normalize()
            else:
                self.setBelief(key,total,model)
        else:
            # Original Phase 1 messages
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
        if actions is not None and len(actions) == 1:
            return {'action': next(iter(actions))}
        if state is None:
            state = self.world.state
        if selection is None:
            selection = 'uniform'
        if model is None:
            try:
                model = self.world.getModel(self.name,state)
            except KeyError:
                # Use real model as fallback?
                model = self.world.getModel(self.name)
            if isinstance(model,Distribution):
                assert len(model) == 1
                model = model.first()
            assert model != True

        if actions is None:
            actions = self.getActions(state)

        if hasattr(self,'spouse') and self.spouse is not None and self.spouse in others:
            logEdge('Actor marriedTo Actor','Actor\'s Expected Reward','sometimes','Spouses have the highest expected reward for coordinated action')
            #//GT: edge 85; from 22; to 35; 1 of 1; next 12 lines
            spouseKey = actionKey(self.spouse)
            joint = self.world.float2value(spouseKey,others[self.spouse][makeFuture(spouseKey)][makeFuture(spouseKey)][CONSTANT])
            for action in self.actions:
                if action['verb'] == joint['verb']:
                    if 'object' in action:
                        if action['object'] == joint['object']:
                            return {'action': action}
                    else:
                        return {'action': action}
            else:
                raise ValueError('%s unable to match spouse action: %s' % (self.name,joint))
        actionMap = {action: action for action in actions}

        for group in self.groups:
            if self.world.getFeature(binaryKey(self.name,group,'memberOf'),state,unique=True):
                # I'm in this group; has there been a group decision?
                action = self.world.getFeature(stateKey(group,ACTION),state,unique=True)
                if action['verb'] != 'noDecision':
                    logEdge('Actor memberOf Group','Actor\'s Expected Reward','sometimes','Group members have highest expected reward when abiding by group decision')
                    #
                    logEdge('Group-decreaseRisk','Actor-decreaseRisk','sometimes','Group members must either follow group decision or leave group')
                    #
                    logEdge('Group-decreaseRisk','Actor-leave-Group','sometimes','Group members must either follow group decision or leave group')
                    #
                    candidates = []
                    for lonely in actions:
                        if lonely['verb'] == action['verb']:
                            if 'object' in action:
                                if lonely['object'] == action['object']:
                                    candidates = {lonely}
                                    break
                            elif 'object' in lonely:
                                candidates.append(lonely)
                            else:
                                candidates = {lonely}
                                break
                    assert len(candidates) == 1,'Multiple options for agent %s to satisfy group %s decision %s:\n%s' % (self.name,group,action,candidates)
                    actionMap = {lonely: lonely, self.nop: ActionSet([Action({'subject': self.name,'verb': 'leave','object': group})])}
                    break

        logEdge('ActorBeliefOfActor\'s risk','Actor\'s Expected Reward','often','Actor\'s expected reward computation uses perception of its risk (not actual value)')
        #//GT: edge 75; from 33; to 35; 1 of 2; next 56 lines
        logEdge('ActorBeliefOfNature\'s category','Actor\'s Expected Reward','often','Actor\'s expected reward computation uses perception of hurricane category (not actual value)')
        #//GT: edge 76; from 11; to 35; 1 of 2; next 54 lines
        logEdge('ActorBeliefOfRegion\'s risk','Actor\'s Expected Reward','often','Actor\'s expected reward computation uses perception of region risk (not actual value)')
        #//GT: edge 50; from 12; to 35; 2 of 3; next 52 lines
        logEdge('ActorBeliefOfRegion\'s shelterRisk','Actor\'s Expected Reward','often','Actor\'s expected reward computation uses perception of shelter risk (not actual value)')
        #//GT: edge 77; from 13; to 35; 1 of 2; next 50 lines
        logNode('Actor\'s Expected Reward','Expected utility (desirability) of candidate actions','Real for each action choice')
        #//GT: node 35; 1 of 1; next 48 lines
        logEdge('Actor\'s Expected Reward','Actor-decreaseRisk','often','Action choice determined by the expected reward calculation')
        #//GT: edge 78; from 35; to 31; 1 of 1; next 46 lines
        logEdge('Actor\'s Expected Reward','Actor-evacuate','often','Action choice determined by the expected reward calculation')
        #//GT: edge 79; from 35; to 29; 1 of 1; next 44 lines
        logEdge('Actor\'s Expected Reward','Actor-moveTo-home','often','Action choice determined by the expected reward calculation')
        #//GT: edge 80; from 35; to 30; 1 of 1; next 42 lines
        logEdge('Actor\'s Expected Reward','Actor-moveTo-shelter','often','Action choice determined by the expected reward calculation')
        #//GT: edge 81; from 35; to 28; 1 of 1; next 40 lines
        logEdge('Actor\'s Expected Reward','Actor-stayInLocation','often','Action choice determined by the expected reward calculation')
        #//GT: edge 82; from 35; to 27; 1 of 1; next 38 lines
        logEdge('Actor\'s Expected Reward','Actor-takeResources','often','Action choice determined by the expected reward calculation')
        #//GT: edge 83; from 35; to 32; 1 of 1; next 36 lines
        logEdge('Actor\'s horizon','Actor\'s Expected Reward','often','How far into the future an Actor looks when deciding what to do')
        #//GT: edge 84; from 14; to 35; 1 of 1; next 34 lines
        logEdge('ActorBeliefOfActor\'s risk','Actor\'s Expected Reward','often','Actor\'s expected reward computation uses perception of its risk (not actual value)')
        #//GT: edge 75; from 33; to 35; 2 of 2; next 32 lines
        logEdge('ActorBeliefOfNature\'s category','Actor\'s Expected Reward','often','Actor\'s expected reward computation uses perception of hurricane category (not actual value)')
        #//GT: edge 76; from 11; to 35; 2 of 2; next 30 lines
        logEdge('ActorBeliefOfRegion\'s risk','Actor\'s Expected Reward','often','Actor\'s expected reward computation uses perception of region risk (not actual value)')
        #//GT: edge 50; from 12; to 35; 3 of 3; next 28 lines
        logEdge('ActorBeliefOfRegion\'s shelterRisk','Actor\'s Expected Reward','often','Actor\'s expected reward computation uses perception of shelter risk (not actual value)')
        #//GT: edge 77; from 13; to 35; 2 of 2; next 26 lines
        belief = self.getBelief(state,model)
        if horizon is None:
            horizon = self.getAttribute('horizon',model)
        if self.config.getint('Simulation','phase',fallback=1) >= 3:
            assert len(belief) <= 2
            if isinstance(self.world.state,KeyedVector):
                decision = {'__EV__':  {}}
                join = None
                for vector,prob in belief.worlds():
                    for action in self.getActions(vector):
                        if action['verb'] == 'join':
                            joint = self.world.getFeature(actionKey(action['object']),vector,unique=True)
                            if joint['verb'] != 'noDecision':
                                if join is None:
                                    join = {'action': action,'decision': joint}
                                else:
                                    # Assume group decision is the same across beliefs (not true in general, but true here)
                                    assert join['decision'] == joint
                            continue
                        else:
                            ER = self.vectorValue(copy.deepcopy(vector),action,horizon,model)*prob
                        try:
                            decision['__EV__'][action] += ER
                        except KeyError:
                            decision['__EV__'][action] = ER
                decision['action'] = max([(ER,action) for action,ER in decision['__EV__'].items()])[1]

                logEdge('Group-decreaseRisk','Actor-join-Group','sometimes','Nonmembers who decide they want to be prosocial will join group that has made the same decision')
                #
                if join is not None:
                    if join['decision']['verb'] == decision['action']['verb']:
                        decision['action'] = join['action']

            else:
                best,EV = self.chooseAction(belief,horizon,model=model)
                decision = {'action': best,'__EV__': EV}
        else:
            decision = Agent.decide(self,state,horizon,None if self.config.getint('Simulation','phase',fallback=1) > 1 else others,
                model,selection,actionMap.keys(),belief.keys(),debug)
        if not hasattr(self,'riskAttitude') or self.riskAttitude is None:
            if len(decision['action']) > 1 and selection == 'uniform':
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
                    decision['action'] = actionMap[decision['action'].first()]
        elif 'V' in decision:
            # Used in a Phase 2 Prescribe request
            values = set()
            V = {}
            for action,value in decision['V'].items():
                if action in self.actions:
                    V[action] = []
                    for s_t in value['__S__']:
                        V[action].append(s_t[rewardKey(self.name)])
                        values |= set(V[action][-1].domain())
            values = sorted(values)
            best = None
            for action,seq in V.items():
                EV = 0
                for ER in seq:
                    for R in ER.domain():
                        # Higher values are scaled more
                        EV += ER[R]*R*values.index(R)
                if best is None or EV > best[1]:
                    best = action,EV
            decision['action'] = best[0]
        return decision

    def reinforceHome(self,config):
        impact = likert[5][config.getint('Actors','health_impact')-1]
        self.setHealthDynamics(impact,impact/2,False)

    def getFriends(self,network=None):
        if network is None:
            return self.friends
        else:
            return network['friendOf'].get(self.name,set())

    def getNeighbors(self):
        logNode('Actor neighborOf Actor','Neighbor relationship between two actors','Boolean','Static')
        #//GT: node 20; 1 of 1; next 9 lines
        logEdge('Actor\'s health','Actor neighborOf Actor','sometimes','Actors cannot be neighbors with dead people')
        #//GT: edge 14; from 21; to 20; 1 of 1; next 7 lines
        try:
            return {a.name for a in self.world.agents.values() if isinstance(a,Actor) and \
                not a.name == self.name and a.demographics['home'] == self.demographics['home'] and stateKey(a.name,'health') in self.world.state}
        except AttributeError:
            # Old school (i.e., terrible
            return {a.name for a in self.world.agents.values() if isinstance(a,Actor) and \
                not a.name == self.name and a.home == self.home}

    def chooseAction(self,belief,horizon,action=None,model=None):
        if horizon > 0:
            if action is not None:
                self.projectState(belief,action,select='max')
                self.world.agents['Nature'].step('max',belief,False)
                V = self.reward(belief,model)
                if horizon > 1:
                    best,EV = self.chooseAction(belief,horizon-1,None,model)
                    V += EV
                return action,V
            else:
                V = {action: self.chooseAction(copy.deepcopy(belief),horizon,action,model)[1] for action in self.getActions(belief)}
                best = None
                for action,EV in V.items():
                    if best is None or EV > best[1]:
                        best = action,EV
                return best[0],best[1]
        else:
            EV = self.reward(belief,model)
            return None,EV

    def vectorChoice(self,current,actions,horizon,model):
        V = [(self.vectorValue(copy.deepcopy(current),action,horizon,model),action) for action in actions]
        return max(V)[1]

    def vectorValue(self,current,action,horizon,model):
        """
        :warning: The current state passed in as modified in place
        """
        ER = 0.
        for t in range(horizon):
            # A day in the life
            if t == 0:
                current = self.world.step(action,current,select='max',keySubset=current.keys(),updateBeliefs=False)
            else:
                subactions = [action for action in self.getActions(current) if action['verb'] not in {'join','leave'}]
                subaction = self.vectorChoice(current,subactions,horizon-1,model)
                current = self.world.step(subaction,current,select='max',keySubset=current.keys(),updateBeliefs=False)
            current = self.world.step(self.world.agents['System'].nop,current,select='max',keySubset=current.keys(),
                updateBeliefs=False)
            current = self.world.step(self.world.agents['Nature'].evolution,current,select='max',keySubset=current.keys(),
                updateBeliefs=False)
            ER += self.reward(current,model)
            current = self.world.step(self.world.agents['Group%s' % (self.demographics['home'])].nop,current,
                select='max',keySubset=current.keys(),updateBeliefs=False)
        return ER