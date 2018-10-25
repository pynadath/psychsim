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
import time

from psychsim.pwl import *
from psychsim.action import powerset
from psychsim.reward import *
from psychsim.agent import Agent
    
from .data import *
from .region import Region
from .nature import Nature
from .system import System
from .group import Group
from .actor import Actor
from .cdf import *
from .create import *

preSurveyRecords = []
postSurveyRecords = []

def runInstance(instance,args,config,rerun=True):
    for run in range(args['runs']):
        # Verify directory structure
        dirName = os.path.join(os.path.dirname(__file__),'..','Instances',
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
        l = logging.getLogger()
        for h in l.handlers:
            l.removeHandler(h)
        l.addHandler(logging.FileHandler(logfile,'w'))

        logging.info('Running Instance %d' % (instance))
        print('Running instance %d, run %d' % (instance,run))
        # Initialize world
        world = createWorld(config)
        world.setParallel(args['multiprocessing'])
        population = [agent for agent in world.agents.values() if isinstance(agent,Actor)]
        living = population[:]
        groups = [agent for agent in world.agents.values() if isinstance(agent,Group)]
        regions = {agent.name: {'agent': agent,
                                'inhabitants': [a for a in population if a.home == agent.name]}
                   for agent in world.agents.values() if isinstance(agent,Region)}
        del preSurveyRecords[:]
        del postSurveyRecords[:]
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
        random.seed(config.getint('Simulation','seedRun')+run)
        endDay = None
        survey = set()
        oldPhase = world.getState('Nature','phase').first()
        start = time.time()
        state = {'hurricanes': 0,
                 'phase': world.getState('Nature','phase').first()}
        while state['hurricanes'] < args['number'] or \
              (args['number'] > 0 and state['phase'] == 'none' and
               world.getState('Nature','days').first() <= config.getint('Disaster','phase_min_days')):
            try:
                nextDay(world,living,groups,state,config,dirName,survey,start,cdfTables)
            except ValueError:
                break
            if args['visualize']:
                addState2tables(world,today,allTables,population,regions)
                vizUpdateLoop(day)
            writeHurricane(world,state['hurricanes']+1,dirName)
        logging.info('Total time: %f' % (time.time()-start))
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
                print('%d' % (state['hurricanes']),file=outfile)
        if args['profile']:
            prof.disable()
            buf = StringIO()
            profile = pstats.Stats(prof, stream=buf)
            profile.sort_stats('time').print_stats()
            logging.critical(buf.getvalue())
            buf.close()

def nextDay(world,living,groups,state,config,dirName,survey=None,start=None,cdfTables={},actions={}):
    state['today'] = world.getState(WORLD,'day').first()
    logging.info('Day %d' % (state['today']))
    day = state['today']
    updateCDF(world,dirName,cdfTables)
    while day == state['today']:
        agents = world.next()
        turn = world.agents[next(iter(agents))].__class__.__name__
        if start:
            print('Day %3d: %-6s %-11s (%8.2f)' % (state['today'],turn,state['phase'] if state['phase'] != 'active' else world.getState('Nature','location').first(),time.time()-start))
        else:
            print(('Day %3d: %-6s %-11s' % (state['today'],turn,state['phase'] if state['phase'] != 'active' else world.getState('Nature','location').first())))
        if turn == 'Actor':
            if groups:
                # Make group decisions
                pass
            if config.getboolean('Actors','messages') and state['phase'] != 'none':
                myScale = likert[5][config.getint('Actors','self_trust')-1]
                if config.getint('Actors','friend_opt_trust') > 0:
                    optScale = likert[5][config.getint('Actors','friend_opt_trust')-1]
                else:
                    optScale = 0.
                if config.getint('Actors','friend_pess_trust') > 0:
                    pessScale = likert[5][config.getint('Actors','friend_pess_trust')-1]
                else:
                    pessScale = 0.
                for actor in living:
                    friends = [friend for friend in actor.friends
                               if world.agents[friend] in living]
                    if friends:
                        key = stateKey('Nature','category')
                        for friend in friends:
                            yrBelief = next(iter(world.agents[friend].getBelief().values()))
                            msg = yrBelief[key]
                            actor.recvMessage(key,msg,myScale,optScale,pessScale)
        if state['phase'] == 'approaching':
            if turn == 'Actor' and survey is not None:
                # Pre-hurricane survey
                count = 0
                sampleLimit = int(float(len(living))*config.getfloat('Data','presample')/
                                  float(config.getint('Disaster','phase_min_days')))
                remaining = {actor.name for actor in living} - survey
                while count < sampleLimit and remaining:
                    actor = world.agents[random.choice(list(remaining))]
                    remaining.remove(actor.name)
                    if actor.getState('alive').first():
                        preSurvey(actor,dirName,state['hurricanes']+1)
                        survey.add(actor.name)
                    else:
                        living.remove(actor)
                    count += 1
        elif state['phase'] == 'none':
            if turn == 'Actor' and survey is not None and state['hurricanes'] > 0:
                # Post-hurricane survey
                count = 0
                sampleLimit = int(float(len(living))*config.getfloat('Data','postsample')/
                                  float(config.getint('Disaster','phase_min_days')))
                remaining = {actor.name for actor in living} - survey
                while count < sampleLimit and remaining:
                    actor = world.agents[random.choice(list(remaining))]
                    remaining.remove(actor.name)
                    if actor.getState('alive').first():
                        postSurvey(actor,dirName,state['hurricanes'])
                        survey.add(actor.name)
                    else:
                        living.remove(actor)
                    count += 1
        else:
            assert state['phase'] == 'active'
        debug = {}
        #            debug.update({name: {'V': True} for name in world.agents if name[:5] == 'Group'})
        #            for name in debug:
        #                for agent in world.agents[name].members():
        #                    debug[name][agent] = {}
        newState = world.step(actions.get(turn,None),select=True,debug=debug)
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
        for actor in living:
            belief = actor.getBelief()
            for dist in belief.values():
                for sdist in dist.distributions.values():
                    if len(sdist) > 3:
#                        print(actor.name)
#                        world.printState(sdist)
#                        print(sorted([sdist[e] for e in sdist.domain()]))
                        true = {}
                        for key in sdist.keys():
                            if key != CONSTANT:
                                trueDist = world.state.distributions[world.state.keyMap[key]]
                                assert len(trueDist) == 1
                                true[key] = trueDist.first()[key]
                        sdist.prune(actor.epsilon,true)
#                        world.printState(sdist)
        if state['phase'] == 'active':
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
            if 'QualitativeData' in cdfTables:
                qualData = cdfTables['QualitativeData'][-1]
                qualData['evacuated'] = max(evacuees,qualData.get('evacuated',0))
                qualData['went to shelters'] = max(shelter,qualData.get('shelter',0))
        day = world.getState(WORLD,'day').first()
        phase = world.getState('Nature','phase').first()
        if phase != state['phase']:
            if survey is not None:
                # Reset survey on each phase change
                survey.clear()
            if phase == 'active' and 'QualitativeData' in cdfTables:
                # New hurricane
                cdfTables['QualitativeData'].append({})
        if phase == 'none':
            if state['phase'] == 'active':
                state['hurricanes'] += 1
                logging.info('Completed Hurricane #%d' % (state['hurricanes']))
                endDay = day
        state['phase'] = phase
    
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
       
        
def writeHurricane(world,hurricane,dirName):
    fields = ['Timestep','Name','Category','Location','Landed']
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
                    elif field == 'Landed':
                        if phase == 'approaching':
                            record[field] = 'no'
                        else:
                            record[field] = 'yes'
                    else:
                        record[field] = world.getState('Nature',field.lower()).first()
                    if field == 'Location':
                        if record[field] == 'none':
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

preSurveyFields = ['Timestep','Participant','Hurricane']
preSurveyFields += sorted(list(demographics.keys()))
preSurveyQuestions = {'At Shelter': ('location','=shelter'),
                      'Evacuated': ('location','=evacuated'),
                      'Severity': ('Nature\'s category','round')}
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
            logging.info('PreSurvey %d, Participant %d: %s' % (hurricane,record['Participant'],actor.name))
            record.update(getDemographics(actor))
            # Answer questions
            belief = actor.getBelief()
            assert len(belief) == 1,'Unable to answer pre-survey with uncertain models'
            belief = next(iter(belief.values()))
            for field,answer in preSurveyQuestions.items():
                key,fun = answer
                if not isStateKey(key):
                    if ',' in key:
                        feature,key = key.split(',')
                        agent = actor.world.getState(actor.name,feature).first()
                    else:
                        agent = actor.name
                    key = stateKey(agent,key)
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
                elif fun == 'round':
                    record[field] = int(round(value.expectation()))
            writer.writerow(record)

history = {}
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
            logging.info('PostSurvey %d, Participant %d: %s' % (hurricane,record['Participant'],actor.name))
            record.update(getDemographics(actor))
            belief = actor.getBelief()
            assert len(belief) == 1,'Unable to answer post-survey with uncertain models'
            belief = next(iter(belief.values()))
            for field,answer in postSurveyQuestions.items():
                feature,fun = answer
                if fun == 'likert':
                    if ',' in feature:
                        agentFeature,feature = feature.split(',')
                        agent = actor.getState(agentFeature,belief).first()
                    else:
                        agent = actor.name
                    if stateKey(agent,feature) in belief:
                        value = actor.world.getState(agent,feature,belief)
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
