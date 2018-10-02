from __future__ import print_function
from argparse import ArgumentParser
import cProfile
try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO
import csv
import logging
import os
import os.path
import pstats
import random
import sys
import time

if (sys.version_info > (3, 0)):
    from configparser import ConfigParser
else:
    from ConfigParser import SafeConfigParser as ConfigParser

import psychsim.probability
from psychsim.pwl import *
from psychsim.action import powerset
from psychsim.reward import *
from psychsim.world import *
from psychsim.agent import Agent
try:
    from psychsim.ui.diagram import Diagram
    __ui__ = True
except:
    __ui__ = False
    
from psychsim.domains.groundtruth.data import *
from psychsim.domains.groundtruth.region import Region
from psychsim.domains.groundtruth.nature import Nature
from psychsim.domains.groundtruth.system import System
from psychsim.domains.groundtruth.group import Group
from psychsim.domains.groundtruth.actor import Actor
from psychsim.domains.groundtruth.cdf import *

def runInstance(instance,args,config,rerun=True):
    for run in range(args['runs']):
        # Verify directory structure
        dirName = os.path.join(os.path.dirname(__file__),'Instances',
                               'Instance%d' % (instance),'Runs','run-%d' % (run))
        if not os.path.exists(dirName):
            os.makedirs(dirName)
        if not rerun and os.path.exists(os.path.join(dirName,'scenario.pkl')):
            # Already ran this
            print('Skipping instance %d, run %d' % (instance,run))
            continue
        logfile = os.path.join(dirName,'psychsim.log')
        try:
            os.stat(dirName)
        except OSError:
            os.makedirs(dirName)
        try:
            os.remove(logfile)
        except OSError:
            pass
        logging.basicConfig(level=level,filename=logfile)

        logging.info('Running Instance %d' % (instance))
        print('Running instance %d, run %d' % (instance,run))
        # Initialize world
        world = createWorld(config)
        population = [agent for agent in world.agents.values() if isinstance(agent,Actor)]
        living = population[:]
        groups = [agent for agent in world.agents.values() if isinstance(agent,Group)]
        regions = {agent.name: {'agent': agent,
                                'inhabitants': [a for a in population if a.home == agent.name]}
                   for agent in world.agents.values() if isinstance(agent,Region)}
        # Write definition files
        if args['write']:
            defDir = os.path.join(os.path.dirname(__file__),'SimulationDefinition')
            if not os.path.exists(defDir):
                os.makedirs(defDir)
            writeDefinition(world,defDir)
        writeCensus(world,regions,dirName)
        writeHurricane(world,0,dirName)
        preSurvey(None,dirName,0)
        postSurvey(None,dirName,0)
        # Setup entity lists for CDF tables
        cdfTables = {'InstanceVariable': [],
                     'RunData': [],
                     'SummaryStatisticsData':
                     [(population,'alive','count=False','Deaths'),
                      (population,'health','count<0.2','Casualties'),
                      (population,'location','count=evacuated','Evacuees'),
                      (population,'location','count=shelter','Sheltered'),
                      (population,'health','mean','Wellbeing'),
                      (population,'resources','mean','Wealth'),
                      ([world.agents[r] for r in regions],'risk','invert,mean','Safety'),
                      (population,ACTION,'count=decreaseRisk','Prosocial'),
                      (population,ACTION,'count=takeResources','Antisocial'),
                      (regions,'health','mean','Regional Wellbeing'),
                      (regions,'alive','count=False','Regional Deaths'),
                      (regions,'health','count<0.2','Regional Casualties'),
                      (regions,'location','count=shelter','Regional Sheltered'),
                     ],
                     'QualitativeData': [],
                     'RelationshipData': [],
                     'Population': {'Deaths': (population,'alive','count=False'),
                                    'Casualties': (population,'health','count<0.2'),
                                    'Evacuees': (population,'location','count=evacuated'),
                                    'Sheltered': (population,'location','count=shelter'),
                     },
                     'Regional': {'Deaths': (regions,'alive','count=False'),
                                  'Casualties': (regions,'health','count<0.2'),
                                  'Sheltered': (regions,'location','count=shelter')
                     },
        }
        toCDF(world,dirName,cdfTables)
        # Set up tables for visualization
        allTables = {'Region': {'fields': [('alive','casualties','invert'),
                                           ('location','evacuated','#evacuated'),
                                           ('location','shelter','#shelter'),
                                           ('risk','safety','invert')],
                                'population': Region,
                                'series': True,
                                'log': []},
                     'Actors': {'fields': [('alive','alive',None),
                                           ('location','shelter','=shelter'),
                                           ('location','evacuated','=evacuated'),
                                           ('risk','safety','invert'),
                                           ('health','health',None),
                                           ('grievance','grievance','invert'),
                     ],
                                'population': Actor,
                                'series': True,
                                'log': []},
                     'Display': {'fields': [('x','x',None),
                                            ('y','y',None),
                                            ('region','region',None)],
                                 'population': Actor,
                                 'series': False,
                                 'log': []}
        }
        if args['visualize']:
            addState2tables(world,0,allTables,population,regions)
        if args['profile']:
            prof = cProfile.Profile()
            prof.enable()
        if args['compile']:
            for agent in population:
                agent.compileV()
        try:
            random.seed(config.getint('Simulation','seedRun')+run)
        except ValueError:
            # Non int, so assume None
            random.seed()
        hurricanes = 0
        endDay = None
        survey = set()
        oldPhase = world.getState('Nature','phase').first()
        start = time.time()
        stats = {}
        while hurricanes < args['number'] or (args['number'] > 0 and oldPhase == 'none' and world.getState('Nature','days').first() <= config.getint('Disaster','phase_min_days')):
            today = world.getState(WORLD,'day').first()
            logging.info('Day %d' % (today))
            day = today
            updateCDF(world,dirName,cdfTables)
            while day == today:
                agents = world.next()
                turn = world.agents[next(iter(agents))].__class__.__name__
                print(today,turn,oldPhase,time.time()-start)
                actions = {}
                if turn == 'Actor':
                    if groups:
                        # Make group decisions
                        pass
                    if config.getboolean('Actors','messages') and oldPhase != 'none':
                        myScale = likert[5][config.getint('Actors','self_trust')-1]
                        optScale = likert[5][config.getint('Actors','friend_opt_trust')-1]
                        pessScale = likert[5][config.getint('Actors','friend_pess_trust')-1]
                        for actor in living:
                            friends = [friend for friend in actor.friends
                                       if world.agents[friend] in living]
                            if friends:
                                beliefs = actor.getBelief()
                                assert len(beliefs) == 1
                                model,myBelief = next(iter(beliefs.items()))
                                key = 'Nature\'s category'
                                dist = myBelief[key]
                                total = Distribution({el: myScale*dist[el] for el in dist.domain()})
                                for friend in friends:
                                    yrBelief = next(iter(world.agents[friend].getBelief().values()))
                                    msg = yrBelief[key]
                                    if msg.expectation() > dist.expectation():
                                        yrScale = pessScale
                                    else:
                                        yrScale = optScale
                                    for value in msg.domain():
                                        total.addProb(value,yrScale*msg[value])
                                total.normalize()
                                actor.setBelief(key,total,model)
                if oldPhase == 'approaching':
                    if turn == 'Actor':
                        # Pre-hurricane survey
                        count = 0
                        sampleLimit = int(float(len(living))*config.getfloat('Data','presample')/
                                          float(config.getint('Disaster','phase_min_days')))
                        remaining = {actor.name for actor in living} - survey
                        while count < sampleLimit and remaining:
                            actor = world.agents[random.choice(list(remaining))]
                            remaining.remove(actor.name)
                            if actor.getState('alive').first():
                                preSurvey(actor,dirName,hurricanes+1)
                                survey.add(actor.name)
                            else:
                                living.remove(actor)
                            count += 1
                elif oldPhase == 'none':
                    if turn == 'Actor':
                        if hurricanes > 0:
                            # Post-hurricane survey
                            count = 0
                            sampleLimit = int(float(len(living))*config.getfloat('Data','postsample')/
                                              float(config.getint('Disaster','phase_min_days')))
                            remaining = {actor.name for actor in living} - survey
                            while count < sampleLimit and remaining:
                                actor = world.agents[random.choice(list(remaining))]
                                remaining.remove(actor.name)
                                if actor.getState('alive').first():
                                    postSurvey(actor,dirName,hurricanes)
                                    survey.add(actor.name)
                                else:
                                    living.remove(actor)
                                count += 1
                else:
                    assert oldPhase == 'active'
                    print(world.getState('Nature','location').first())
                # if oldPhase == 'active' and turn == 'Actor' and hurricanes == 0:
                #     samaritans = set()
                #     for index in range(1,100,10):
                #         actor = 'Actor%04d' % (index)
                #         samaritans.add(actor)
                #         for action in world.agents[actor].actions:
                #             if action['verb'] == 'decreaseRisk':
                #                 actions[actor] = action
                #                 break
                # elif day == 2 and turn == 'Actor':
                #     for name in ['Actor0033','Actor0034']:
                #         actor = world.agents[name]
                #         for action in actor.actions:
                #             if action['verb'] == 'stayInLocation':
                #                 actions[name] = action
                #                 break
                try:
                    newState = world.step(actions,select=True)
                except:
                    raise
                buf = StringIO()
                joint = world.explainAction(newState,level=1,buf=buf)
                joint = {name: action for name,action in joint.items()
                         if world.agents[name].__class__.__name__ == turn}
                logging.debug('\n'+buf.getvalue())
                buf.close()
                buf = StringIO()
                world.printState(newState,buf)
                logging.debug(buf.getvalue())
                buf.close()
                if oldPhase == 'active':
                    # Record what these doomed souls did to postpone the inevitable
                    evacuees = 0
                    shelter = 0
                    for name,action in joint.items():
                        agent = world.agents[name]
                        if isinstance(agent,Actor):
                            if agent.getState('alive').first():
                                belief = agent.getBelief()
                                assert len(belief) == 1,'Unable to store beliefs over uncertain models'
                                belief = next(iter(belief.values()))
                                entry = {'action': action}
                                for feature in ['location','risk','health','grievance']:
                                    entry[feature] = agent.getState(feature,belief)
                                    if feature == 'location':
                                        if entry[feature].first() == 'evacuated':
                                            evacuees += 1
                                        elif entry[feature].first()[:7] == 'shelter':
                                            shelter += 1
                                history[name] = history.get(name,[])+[entry]
                    qualData = cdfTables['QualitativeData'][-1]
                    qualData['evacuated'] = max(evacuees,qualData.get('evacuated',0))
                    qualData['went to shelters'] = max(shelter,qualData.get('shelter',0))
                day = world.getState(WORLD,'day').first()
                phase = world.getState('Nature','phase').first()
                if phase != oldPhase:
                    # Reset survey on each phase change
                    survey.clear()
                    if phase == 'active':
                        # New hurricane
                        cdfTables['QualitativeData'].append({})
                if phase == 'none':
                    if oldPhase == 'active':
                        hurricanes += 1
                        logging.info('Completed Hurricane #%d' % (hurricanes))
                        endDay = day
                # if endDay and day == endDay + 7:
                #     outFile = os.path.join(os.path.dirname(__file__),'Instances','Instance100001',
                #                            'Runs','run-0','AccessibilityDemo14Table')
                #     fields = ['Region','Risk','Deaths','Prosocial+']
                #     with open(outFile,'w') as csvfile:
                #         writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
                #         writer.writeheader()
                #         risk = 0.
                #         for region,entry in regions.items():
                #             risk += world.getState(region,'risk').expectation()
                #             record = {'Region': region,
                #                       'Deaths': 0,
                #                       'Prosocial+': 'no'}
                #             for actor in entry['inhabitants']:
                #                 if not actor.getState('alive').first():
                #                     record['Deaths'] += 1
                #                 if actor.name in samaritans:
                #                     record['Prosocial+'] = 'yes'
                #             writer.writerow(record)
                #         writer.writerow({'Region': 'all',
                #                          'Risk': risk/float(len(regions))})
                #     sys.exit(0)
                                
                oldPhase = phase
                if args['visualize']:
                    addState2tables(world,today,allTables,population,regions)
                    vizUpdateLoop(day)
            writeHurricane(world,hurricanes+1,dirName)
        if args['pickle']:
            print('Pickling...')
            import pickle
            with open(os.path.join(dirName,'scenario.pkl'),'wb') as outfile:
                pickle.dump(world,outfile)
        elif args['xml']:
            print('Saving...')
            world.save(os.path.join(dirName,'scenario.psy'))
        else:
            with open(os.path.join(dirName,'scenario.pkl'),'w') as outfile:
                print('%d' % (hurricanes),file=outfile)
        if args['profile']:
            prof.disable()
            buf = StringIO()
            profile = pstats.Stats(prof, stream=buf)
            profile.sort_stats('time').print_stats()
            logging.critical(buf.getvalue())
            buf.close()
    
def addState2tables(world,day,tables,population,regions):
    # Grab all of the relevant fields, but only once
    values = {agent.name: {} for agent in population}
    for agent in population:
        for table in tables.values():
            if not table['population'] is Nature:
                for feature,label,function in table['fields']:
                    if not feature in values[agent.name]:
                        value = world.getState(agent.name,feature)
                        assert len(value) == 1
                        values[agent.name][feature] = value.first()
    # Create tables
    for table in tables.values():
        if table['population'] is Region:
            for region in sorted(regions):
                inhabitants = regions[region]['inhabitants']
                entry = {'day': day,
                         'region': region}
                for feature,label,function in table['fields']:
                    if world.variables[stateKey(population[0].name,feature)]['domain'] is bool:
                        entry[label] = len([a for a in inhabitants if values[a.name][feature]])
                        hi = len(inhabitants)
                    elif function and function[0] == '#':
                        target = function[1:]
                        entry[label] = len([a for a in inhabitants if values[a.name][feature][:len(target)] == target])
                        hi = len(inhabitants)
                    elif function and function[0] == '%':
                        target = function[1:]
                        count = len([a for a in inhabitants if values[a.name][feature][:len(target)] == target])
                        try:
                            entry[label] = float(count)/float(len(inhabitants))
                        except ZeroDivisionError:
                            pass
                        hi = 1.
                    elif function and function[0] == '/':
                        value = [values[a.name][feature] for a in inhabitants]
                        entry[label] = sum(value)/float(len(value))
                        hi = 1.
                    else:
                        value = world.getState(region,feature)
                        assert len(value) == 1
                        entry[label] = value.first()
                        hi = 1.
                    if function == 'invert':
                        entry[label] = hi - entry[label]
                    elif function == 'likert':
                        entry[label] = toLikert(entry[label])
                table['log'].append(entry)
                #print("Region %s"%(entry))
                addToVizData("regions", entry)
        elif table['population'] is Actor:
            for actor in population:
                belief = next(iter(actor.getBelief().values()))
                entry = {'day': day,'participant': actor.name[-4:]}
                for feature,label,function in table['fields']:
                    key = stateKey(actor.name,feature)
                    if world.variables[key]['domain'] is bool:
                        if function == 'invert':
                            entry[label] = not values[actor.name][feature]
                        else:
                            entry[label] = values[actor.name][feature]
                    else:
                        if function == 'likert':
                            entry[label] = toLikert(values[actor.name][feature])
                        elif function and function[0] == '=':
                            entry[label] = values[actor.name][feature] == function[1:]
                        elif function == 'invert':
                            entry[label] = 1.-values[actor.name][feature]
                        else:
                            entry[label] = values[actor.name][feature]
                table['log'].append(entry)
                #print("Actor %s"%(entry))
                #print("Keys %s\nValues %s" %(entry.keys(), entry.values()))
                if 'x' in list(entry.keys()) and 'y' in list(entry.keys()):
                    addToIndividualList(entry)
                addToVizData("actors", entry)
       

def addToIndividualList(entry):
    vm.individualList.append(viz.Individual(entry['x'], entry['y'], viz.SimColor.GRAY,
                                            int(entry['participant'])))
    

def vizUpdateLoop(day):
    global simpaused
    i = 0.0
    #pygame.time.delay(100)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            exit()
        elif event.type == pygame.KEYUP:
            simpaused = not simpaused
            print("Day %d %s" % (day, "(Paused)" if simpaused else "" ))
            

    viz.handleInput()
    vm.update(day)        

    pygame.display.set_caption("Visualization Day %d %s" % (day, "(Paused)" if simpaused else "" ))
    pygame.display.update()


def addToVizData(keyname, entry):

    
    if not keyname in simdata:
        simdata[keyname] = []
        simdata[keyname].append({})

    headervalues = list(entry.keys())
    values = list(entry.values())
    entityname = values[1]
    simday = int(values[0])

    #print ("Simday %s EntityName %s %d" %(simday, entityname, len(simdata[keyname])))
    if len(simdata[keyname]) == simday:
        simdata[keyname].append({})
    
    if not entityname in simdata[keyname][simday]:
        simdata[keyname][simday][entityname] = {}

    for h in range(2,len(headervalues)):
        simdata[keyname][simday][entityname][headervalues[h]] = []

    entityname = list(entry.values())[1]
    for cntr in range (2, len(entry)):
        
        simdata[keyname][simday][entityname][headervalues[cntr]].append(values[cntr])
        
def writeHurricane(world,hurricane,dirName):
    fields = ['Timestep','Name','Category','Location']
    today = world.getState(WORLD,'day').first()
    if hurricane == 0:
        mode = 'w'
    else:
        mode = 'a'
    with open(os.path.join(dirName,'HurricaneTable.tsv'),mode) as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        if hurricane == 0:
            writer.writeheader()
        else:
            phase = world.getState('Nature','phase').first()
            if phase != 'none':
                record = {}
                for field in fields:
                    if field == 'Timestep':
                        record[field] = today
                    elif field == 'Name':
                        record[field] = hurricane
                    else:
                        record[field] = world.getState('Nature',field.lower()).first()
                    if field == 'Location':
                        if phase == 'approaching':
                            record[field] = phase
                        elif record[field] == 'none':
                            record[field] = 'leaving'
                writer.writerow(record)
                
def writeCensus(world,regions,dirName,filename='CensusTable',fieldSubset=None):
    census = {'Population': None,
              'Gender': 'gender',
              'Ethnicity': 'ethnicGroup',
              'Religion': 'religion',
              'Age': 'age',
              'Employment': 'employed',
    }
    fields = ['Region','Field','Value','Count']
    with open(os.path.join(dirName,'%s.tsv' % (filename)),'w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        ages = [a.age for a in world.agents.values() if isinstance(a,Actor)]
        limits = [18]+[i for i in range(25,max(ages),5)]
        labels = ['<%d' % (limits[0])]
        labels += ['%d-%d' % (limits[i],limits[i+1]-1) for i in range(len(limits)-1)]
        labels.append('>%d' % (limits[-1]-1))
        for field,feature in census.items():
            if fieldSubset and field not in fieldSubset:
                continue
            if field == 'Population':
                total = 0
            else:
                total = {}
            for name,table in regions.items():
                if field == 'Population':
                    record = {'Region': name,
                              'Field': field,
                              'Count': len(table['inhabitants']) + \
                              sum([a.kids for a in table['inhabitants']])}
                    writer.writerow(record)
                    total += record['Count']
                elif field == 'Age':
                    histogram = [0 for limit in limits]
                    histogram.append(0)
                    for agent in table['inhabitants']:
                        histogram[0] += agent.kids
                        for i in range(len(limits)):
                            if agent.age < limits[i]:
                                histogram[i] += 1
                                break
                    else:
                        histogram[-1] += 1
                    for i in range(len(histogram)):
                        record = {'Region': name,
                                  'Field': field,
                                  'Value': labels[i],
                                  'Count': histogram[i]}
                        writer.writerow(record)
                        total[record['Value']] = total.get(record['Value'],0)+record['Count']
                else:
                    histogram = {}
                    for agent in table['inhabitants']:
                        value = agent.getState(feature).first()
                        histogram[value] = histogram.get(value,0) + 1
                    for value,count in histogram.items():
                        total[value] = total.get(value,0) + count
                        record = {'Region': name,
                                  'Field': field,
                                  'Value': value,
                                  'Count': count}
                        writer.writerow(record)
            if field == 'Population':
                record = {'Region': 'All',
                          'Field': field,
                          'Count': total}
                writer.writerow(record)
            else:
                for value,count in sorted(total.items()):
                    record = {'Region': 'All',
                              'Field': field,
                              'Value': value,
                              'Count': count}
                    writer.writerow(record)

demographics = {'Gender': 'gender',
                'Age': 'age',
                'Ethnicity': 'ethnicGroup',
                'Religion': 'religion',
                'Children': 'children',
                'Fulltime Job': 'employed',
                'Pets': 'pet',
                'Wealth': 'resources',
                'Residence': None}

preSurveyRecords = []
preSurveyFields = ['Timestep','Participant','Hurricane']
preSurveyFields += sorted(list(demographics.keys()))
preSurveyQuestions = {'At Shelter': ('location','=shelter'),
                      'Evacuated': ('location','=evacuated'),
                      'Risk': ('risk','expectation')}
preSurveyFields += sorted(list(preSurveyQuestions.keys()))

def getDemographics(actor):
    record = {}
    # Demographic info
    for field,answer in demographics.items():
        if isinstance(answer,str):
            value = actor.getState(answer).first()
            if field == 'Wealth':
                record[field] = int(value*5.1)
            elif isinstance(value,bool):
                if value:
                    record[field] = 'yes'
                else:
                    record[field] = 'no'
            else:
                record[field] = value
        elif field == 'Residence':
            record[field] = actor.home
        else:
            raise RuntimeError('Unable to process pre-survey field: %s' % (field))
    return record
    
def preSurvey(actor,dirName,hurricane):
    if actor is None:
        mode = 'w'
    else:
        mode = 'a'
    with open(os.path.join(dirName,'ActorPreTable.tsv'),mode) as csvfile:
        writer = csv.DictWriter(csvfile,preSurveyFields,delimiter='\t',extrasaction='ignore')
        if actor is None:
            writer.writeheader()
        else:
            today = actor.world.getState(WORLD,'day').first()
            record = {'Timestep': today,
                      'Hurricane': hurricane}
            preSurveyRecords.append(record)
            record['Participant'] = len(preSurveyRecords)
            logging.debug('PreSurvey %d, Participant %d: %s' % (hurricane,record['Participant'],actor.name))
            record.update(getDemographics(actor))
            # Answer questions
            belief = actor.getBelief()
            assert len(belief) == 1,'Unable to answer pre-survey with uncertain models'
            belief = next(iter(belief.values()))
            for field,answer in preSurveyQuestions.items():
                key,fun = answer
                if not isStateKey(key):
                    key = stateKey(actor.name,key)
                value = actor.world.getFeature(key,belief)
                if fun == 'max':
                    record[field] = value.max()
                elif fun[0] == '=':
                    target = fun[1:]
                    assert len(value) == 1,'Unable to compute equality for uncertain beliefs'
                    if value.first()[:len(target)] == target:
                        record[field] = 'yes'
                    else:
                        record[field] = 'no'
                elif fun == 'expectation':
                    record[field] = toLikert(value.expectation())
            writer.writerow(record)

history = {}
postSurveyRecords = []
postSurveyFields = ['Timestep','Participant','Hurricane']
postSurveyFields += sorted(list(demographics.keys()))
postSurveyQuestions = {'At Shelter': ('location','=shelter'),
                       'Evacuated': ('location','=evacuated'),
                       'Risk': ('risk','max'),
                       'Injured': ('health','<0.2'),
                       'Dissatisfaction': ('grievance','likert'),
                       }
postSurveyFields += sorted(list(postSurveyQuestions.keys()))

def postSurvey(actor,dirName,hurricane):
    if actor is None:
        mode = 'w'
    else:
        mode = 'a'
    with open(os.path.join(dirName,'ActorPostTable.tsv'),mode) as csvfile:
        writer = csv.DictWriter(csvfile,postSurveyFields,delimiter='\t',extrasaction='ignore')
        if actor is None:
            writer.writeheader()
        else:
            today = actor.world.getState(WORLD,'day').first()
            record = {'Timestep': today,
                      'Hurricane': hurricane}
            postSurveyRecords.append(record)
            record['Participant'] = len(postSurveyRecords)
            logging.debug('PostSurvey %d, Participant %d: %s' % (hurricane,record['Participant'],actor.name))
            record.update(getDemographics(actor))
            belief = actor.getBelief()
            assert len(belief) == 1,'Unable to answer post-survey with uncertain models'
            belief = next(iter(belief.values()))
            for field,answer in postSurveyQuestions.items():
                feature,fun = answer
                if fun == 'likert':
                    if stateKey(actor.name,feature) in belief:
                        value = actor.getState(feature,belief)
                        value = value.expectation()
                        record[field] = toLikert(value)
                else:
                    for entry in history.get(actor.name,[]):
                        value = entry[feature]
                        if fun == 'max':
                            if field in record:
                                record[field] = max(record[field],toLikert(value.expectation()))
                            else:
                                record[field] = toLikert(value.expectation())
                        elif fun[0] == '=':
                            assert len(value) == 1,'Unable to answer question about uncertain %s:\n%s'\
                                % (stateKey(actor.name,feature),value)
                            value = value.first()
                            target = fun[1:]
                            if value[:len(target)] == target:
                                record[field] = 'yes'
                                break
                        elif fun[0] == '<':
                            target = float(fun[1:])
                            if value.expectation() < target:
                                record[field] = 'yes'
                                break
                        else:
                            raise ValueError('Unknown function: %s' % (fun))
                    else:
                        if not field in record:
                            record[field] = 'no'
            writer.writerow(record)

def createWorld(config):
    try:
        random.seed(config.getint('Simulation','seedGen'))
    except ValueError:
        # Non int, so assume None
        random.seed()
    world = World()
    if __ui__:
        world.diagram = Diagram()
        world.diagram.setColor(None,'deepskyblue')

    regions = {}
    shelters = [int(region) for region in config.get('Shelter','region').split(',')]
    for region in range(config.getint('Regions','regions')):
        index = None
        if config.getboolean('Shelter','exists'):
            try:
                index = shelters.index(region+1)
            except ValueError:
                pass

        n = Region(region+1,world,config,index)
        regions[n.name] = {'agent': n, 'inhabitants': [], 'number': region+1}

    world.defineState(WORLD,'day',int,lo=1)
    world.setState(WORLD,'day',1)

    nature = Nature(world,config)

    population = []
    for i in range(config.getint('Actors','population')):
        agent = Actor(i+1,world,config)
        population.append(agent)
        region = agent.getState('region').first()
        regions[region]['inhabitants'].append(agent)

    for region,entry in regions.items():
        entry['agent'].setInhabitants(regions[region]['inhabitants'])

    if config.getboolean('System','system'):
        system = System(world,config)
    else:
        system = None

    groups = []
    if config.getboolean('Groups','region'):
        for region,info in regions.items():
            group = Group(info['agent'].name,world,config)
            group.potentialMembers([a.name for a in info['inhabitants']],
                                   membership=config.getint('Groups','region_membership'))
            groups.append(group)
    if config.getboolean('Groups','ethnic'):
        group = Group('EthnicMinority',world,config)
        group.potentialMembers([a.name for a in population \
                                if a.getState('ethnicGroup').first() == 'minority'])
        if world.diagram:
            world.diagram.setColor(group.name,'mediumpurple')
        groups.append(group)
        group = Group('EthnicMajority',world,config)
        group.potentialMembers([a.name for a in population \
                                if a.getState('ethnicGroup').first() == 'majority'])
        if world.diagram:
            world.diagram.setColor(group.name,'blueviolet')
        groups.append(group)
    if config.getboolean('Groups','religion'):
        group = Group('ReligiousMinority',world,config)
        group.potentialMembers([a.name for a in population \
                                if a.getState('religion').first() == 'minority'])
        if world.diagram:
            world.diagram.setColor(group.name,'rosybrown')
        groups.append(group)
        group = Group('ReligiousMajority',world,config)
        group.potentialMembers([a.name for a in population \
                                if a.getState('religion').first() == 'majority'])
        if world.diagram:
            world.diagram.setColor(group.name,'darkorange')
        groups.append(group)
    if config.getboolean('Groups','generic'):
        group = Group('',world,config)
        group.potentialMembers([a.name for a in population])
        if world.diagram:
            world.diagram.setColor(group.name,'mediumpurple')
        groups.append(group)

    toInit = [agent.name for agent in population]
    while toInit:
        name = random.choice(toInit)
        toInit.remove(name)
        world.agents[name]._initializeRelations(config)

    order = []
    if groups:
        order.append({g.name for g in groups})
    if population:
        order.append({agent.name for agent in population})
    if system:
        order.append({system.name})
    order.append({'Nature'})

    world.setOrder(order)

    for agent in population:
        agent._initializeBeliefs(config)
        if not config.getboolean('Actors','beliefs'):
            agent.setAttribute('static',True)

    if system and config.getboolean('System','beliefs'):
        system.resetBelief()


    world.dependency.computeEvaluation()
    return world

def getConfig(instance):
    """
    @type instance: int
    """
    # Extract configuration
    config = ConfigParser()
    config.read(os.path.join(os.path.dirname(__file__),'config','%06d.ini' % (instance)))
    return config
    
if __name__ == '__main__':

    parser = ArgumentParser()
    parser.add_argument('-d','--debug',default='WARNING',help='Level of logging detail')
    parser.add_argument('-n','--number',default=1,type=int,help='Number of hurricanes to run')
    parser.add_argument('-r','--runs',default=1,type=int,help='Number of runs to run')
    parser.add_argument('-p','--profile',action='store_true',help='Profile simulation step')
    parser.add_argument('-c','--compile',action='store_true',help='Pre-compile agent policies')
    parser.add_argument('-w','--write',action='store_true',help='Write simulation definition tables')
    parser.add_argument('-v','--visualize',default=None,help='Visualization feature')
    parser.add_argument('--rerun',action='store_true',help='Run instance, even if previously saved')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--pickle',action='store_true',help='Use Python pickle, not XML, to save scenario')
    group.add_argument('--xml',action='store_true',help='Save scenario as XML')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-i','--instance',default=None,type=int,help='Instance number')
    group.add_argument('-s','--samples',default=None,help='File of sample parameter settings')
    
    args = vars(parser.parse_args())
    
    # Extract logging level from command-line argument
    level = getattr(logging, args['debug'].upper(), None)
    if not isinstance(level, int):
        raise ValueError('Invalid debug level: %s' % args['debug'])

    # Initialize visualization
    global vm
    global simpaused
    simpaused = False

    if args['visualize']:
        import pygame
        import psychsim.ui.viz as viz

        simdata = {}
        win = pygame.display.set_mode((1024, 768))
        pygame.init()

        vm = viz.VizMap(1024, 768, 7, 7, simdata, 2, "", win, "safety", args['visualize'])


    if args['samples']:
        with open(args['samples']) as csvfile:
            base = int(os.path.splitext(os.path.split(args['samples'])[1])[0])
            config = getConfig(base)
            reader = csv.DictReader(csvfile,delimiter='\t')
            for row in reader:
                shelters = []
                risks = []
                pets = []
                healths = []
                wealths = []
                for key,value in row.items():
                    key = key.strip()
                    if key == 'Sample ID':
                        instance = base+int(row[key])
                    elif key == '\'Actor’s distribution over gender\'':
                        value = int(value)
                        if value == 1:
                            config.set('Actors','male_prob',str(0.5))
                        elif value == 2:
                            config.set('Actors','male_prob',str(0.4))
                        else:
                            assert value == 3
                            config.set('Actors','male_prob',str(0.6))
                    elif key[:6] == 'Region' and key[-9:] == ' shelter\'':
                        if value == '1':
                            shelters.append(int(key[6:-9]))
                            config.set('Shelter','exists','yes')
                            config.set('Shelter','region','%s' % (','.join(['%02d' % (r)
                                                                            for r in shelters])))
                    elif key[:7] == 'Shelter' and key[-22:] == 'initial level of risk\'':
                        region = int(key[7:-22])
                        if region in shelters:
                            risks.append(reverseLikert[value])
                            config.set('Shelter','risk',','.join(risks))
                    elif key[:7] == 'Shelter' and key[-11:] == 'pet policy\'':
                        region = int(key[7:-11])
                        if region in shelters:
                            if value == '0':
                                pets.append('no')
                            else:
                                assert value == '1'
                                pets.append('yes')
                            config.set('Shelter','pets',','.join(pets))
                    elif key[:-2] == '\'Actor’s distribution over health: group ':
                        healths.append(str(max(min(1.,float(value)),0.2)))
                        assert int(key[-2:-1]) == len(healths)
                        config.set('Actors','health_value_age',','.join(healths))
                    elif key[:-2] == '\'Actor’s distribution over resources: group ':
                        wealths.append(str(max(min(1.,float(value)),0.2)))
                        assert int(key[-2:-1]) == len(wealths)
                        config.set('Actors','wealth_value_age',','.join(wealths))
                    else:
                        section,option,fun = mapFromTandE[key]
                        if fun is not None:
                            value = fun[value]
                        if section == 'Regions':
                            value = str(max(min(1.,float(value)),0.2))
                        config.set(section,option,value)
                with open(os.path.join(os.path.dirname(__file__),'config',
                                       '%06d.ini' % (instance)),'w') as csvfile:
                    config.write(csvfile)
                runInstance(instance,args,config,args['rerun'])
    else:
        config = getConfig(args['instance'])
        runInstance(args['instance'],args,config,args['rerun'])
        
