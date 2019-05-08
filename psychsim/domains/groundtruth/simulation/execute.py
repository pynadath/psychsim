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
    
from psychsim.domains.groundtruth.simulation.data import *
from psychsim.domains.groundtruth.simulation.region import Region
from psychsim.domains.groundtruth.simulation.nature import Nature
from psychsim.domains.groundtruth.simulation.system import System
from psychsim.domains.groundtruth.simulation.group import Group
from psychsim.domains.groundtruth.simulation.actor import Actor
from psychsim.domains.groundtruth.simulation.cdf import *
from psychsim.domains.groundtruth.simulation.create import *

import psychsim.domains.groundtruth.simulation.visualize as visualize

preSurveyRecords = []
postSurveyRecords = []

def runInstance(instance,args,config,rerun=True):
    if args['visualize']:
        visualize.initVisualization(args)
    # Determine what runs to do
    if args['singlerun']:
        runs = [args['runs']]
    else:
        runs = range(args['runs'])
    for run in runs:
        world = None
        hurricanes = []
        # Verify directory structure
        dirName = os.path.join(os.path.dirname(__file__),'..','Instances',
                               'Instance%d' % (instance),'Runs','run-%d' % (run))
        if not os.path.exists(dirName):
            os.makedirs(dirName)
        if args['reload']:
            world = loadPickle(args['instance'],run,args['reload'])
            hurricanes = readHurricanes(args['instance'],run)
            population = [agent for agent in world.agents.values() if isinstance(agent,Actor)]
            regions = {agent.name: {'agent': agent,
                                    'inhabitants': [a for a in population if a.home == agent.name]}
                       for agent in world.agents.values() if isinstance(agent,Region)}
            cdfTables = makeCDFTables(population,[world.agents[r] for r in regions],regions)
            preSurvey(world,None,dirName,0,args['TA2BTA1C10'])
            postSurvey(None,dirName,0,args['TA2BTA1C10'],config.getboolean('Data','postprevious',fallback=False))
        elif os.path.exists(os.path.join(dirName,'scenario.pkl')) and not rerun:
            # Already ran this
            print('Skipping instance %d, run %d' % (instance,run))
            continue
        # Set up logging
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
        # Load any pre-specified future hurricanes
        if args['hurricane']:
            future = readHurricaneFile(args['hurricane'])
        else:
            future = []
        # Let's get started
        logging.info('Running Instance %d' % (instance))
        print('Running instance %d, run %d' % (instance,run))
        if world is None:
            # Initialize new world
            world = createWorld(config)
            writeHurricane(world,0,dirName)
            preSurvey(world,None,dirName,0,False)
            postSurvey(None,dirName,0,False,config.getboolean('Data','postprevious',fallback=False))
            if args['TA2BTA1C10']:
                preSurvey(world,None,dirName,0,True)
                postSurvey(None,dirName,0,True)
            population = [agent for agent in world.agents.values() if isinstance(agent,Actor)]
            regions = {agent.name: {'agent': agent,
                                    'inhabitants': [a for a in population if a.demographics['home'] == agent.name]}
                       for agent in world.agents.values() if isinstance(agent,Region)}
            writeCensus(world,regions,dirName)
            cdfTables = makeCDFTables(population,[world.agents[r] for r in regions],regions)
            toCDF(world,dirName,cdfTables)
            # Write definition files
            if args['write']:
                defDir = os.path.join(os.path.dirname(__file__),'SimulationDefinition')
                if not os.path.exists(defDir):
                    os.makedirs(defDir)
                writeDefinition(world,defDir)
        world.setParallel(args['multiprocessing'])
        groups = [agent for agent in world.agents.values() if isinstance(agent,Group)]
        del preSurveyRecords[:]
        del postSurveyRecords[:]
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
        survey = set()
        oldPhase = world.getState('Nature','phase').first()
        start = time.time()
        state = {'hurricanes': len(hurricanes),
                 'phase': world.getState('Nature','phase').first(),
                 'TA2BTA1C10': args['TA2BTA1C10'],
                 'panels': {}, 'participants': {}}
        if args['TA2BTA1C10']:
            state['panels']['TA2BTA1C10pre'] = {}
            state['panels']['TA2BTA1C10post'] = {}
            state['participants']['TA2BTA1C10pre'] = set()
            state['participants']['TA2BTA1C10post'] = set()
        if not config.getboolean('Simulation','graph',fallback=False):
            season = world.getState(WORLD,'day').first() // config.getint('Disaster','year_length')
        if args['phase1predictlong']:
            for agent in population:
                value = 0.9*agent.getState('resources').expectation()
                agent.setState('resources',value)
                beliefs = agent.getBelief()
                model,myBelief = next(iter(beliefs.items()))
                agent.setBelief(stateKey(agent.name,'resources'),value,model)
            for region in regions:
                risk = stateKey(region,'risk')
                impact = 1.5*likert[5][config.getint('System','system_impact')-1]
                tree = makeTree(approachMatrix(risk,impact,0.))
                world.setDynamics(risk,{'verb': 'allocate','object': region},tree)
        if args['phase1predictshort']:
            for agent in population:
                for action in list(agent.actions):
                    if action['verb'] == 'moveTo' and action['object'][:7] == 'shelter':
                        agent.actions.remove(action)
        terminated = False
        while True:
            if isinstance(args['number'],int):
                if state['hurricanes'] >= args['number']:
                    # Hurricane-based stopping condition is satisfied
                    terminated = True
            elif isinstance(args['days'],int):
                if world.getState(WORLD,'day').first() >= args['days']:
                    # Day-based stopping condition is satisfied
                    terminated = True
            elif isinstance(args['seasons'],int):
                if season >= args['seasons']:
                    # Season-based stopping condition is satisfied
                    terminated = True
            else:
                # No stopping condition, so assume we don't even want to start
                break
            if terminated:
                if state['hurricanes'] == 0:
                    # We haven't run any hurricanes, so just exit
                    break
                # Make sure we're not terminating in the middle of hurricane
                elif state['phase'] == 'none' and world.getState('Nature','days').first() >= config.getint('Disaster','phase_min_days'):
                    break
            nextDay(world,groups,state,config,dirName,survey,start,cdfTables,future=future,maximize=args['max'])
            if args['visualize']:
                addState2tables(world,world.getState(WORLD,'day').first()-1,allTables,population,regions)
                visualize.addDayToQueue(world.getState(WORLD,'day').first()-1)
            hurricaneEntry = writeHurricane(world,state['hurricanes']+1,dirName)
            if args['visualize']:
                if hurricaneEntry is not None:
                    visualize.addToVizData("hurricane", hurricaneEntry)
            newSeason = False
            if world.getState(WORLD,'day').first() - season*config.getint('Disaster','year_length') > config.getint('Disaster','season_length'):
                # Might be a new season
                if world.getState('Nature','phase').first() == 'none' \
                    and world.getState('Nature','days').first() > config.getint('Disaster','phase_min_days'):
                    newSeason = True
                elif world.getState('Nature','phase').first() == 'approaching' \
                    and world.getState('Nature','days').first() == 0:
                    world.setState('Nature','phase','none')
                    world.setState('Nature','days',config.getint('Disaster','phase_min_days')+1)
                    world.setState('Nature','location','none')
                    world.setState('Nature','category',0)
                    newSeason = True
            if newSeason:
                # Jump to new season
                season += 1
                if isinstance(args['seasons'],int) and season >= args['seasons']:
                    # All done
                    break
                phase = stateKey('Nature','phase')
                dayKey = stateKey('Nature','days')
                evolution = ActionSet([Action({'subject': 'Nature','verb': 'evolve'})])
                treePhase = world.dynamics[phase][evolution]
                world.setDynamics(phase,evolution,makeTree(setToConstantMatrix(phase,'none')))
                treeDays = world.dynamics[dayKey][evolution]
                world.setDynamics(dayKey,evolution,makeTree(setToConstantMatrix(dayKey,0)))
                while world.getState(WORLD,'day').first() < season*config.getint('Disaster','year_length'):
                    # Advance simulation to next season
                    names = world.next()
                    turn = world.agents[next(iter(names))].__class__.__name__
                    print('Fast-forward:',world.getState(WORLD,'day').first(),turn)
                    if turn == 'Actor':
                        actions = {name: ActionSet([Action({'subject': name,'verb': 'moveTo', 'object': world.agents[name].home})]) for name in names}
                        world.step(actions,select='max' if args['max'] else True)
                    elif turn == 'System':
                        world.step(select='max' if args['max'] else True)
                    elif turn == 'Nature':
                        world.step(select=True)
                    else:
                        raise NameError('Unknown default action for %s' % (turn))
                # Reset to begin of next season
                world.dynamics[phase][evolution] = treePhase
                world.dynamics[dayKey][evolution] = treeDays
                for name in world.agents:
                    if name[:5] == 'Actor':
                        world.agents[name].setState('resources',world.agents[name].wealth)
                state['phase'] = world.getState('Nature','phase').first()
        logging.info('Total time: %f' % (time.time()-start))
        if args['pickle']:
            print('Pickling...')
            import pickle
            if config.getboolean('Simulation','graph',fallback=False):
                day = 1
            else:
                day = world.getState(WORLD,'day').first()
            with open(os.path.join(dirName,'scenario%d.pkl' % (day)),'wb') as outfile:
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
        if (args['visualize']):
            visualize.closeViz()

def nextDay(world,groups,state,config,dirName,survey=None,start=None,cdfTables={},actions={},future={},maximize=False):
    state['today'] = world.getState(WORLD,'day').first()
    logging.info('Day %d' % (state['today']))
    day = state['today']
    updateCDF(world,dirName,cdfTables)
    while day == state['today']:
        living = [a for a in world.agents.values() if isinstance(a,Actor) and a.getState('alive').first()]
        agents = world.next()
        turn = world.agents[next(iter(agents))].__class__.__name__
        if start:
            print('Day %3d: %-6s %-11s (%8.2f)' % (state['today'],turn,state['phase'] if state['phase'] != 'active' else world.getState('Nature','location').first(),time.time()-start))
        else:
            print(('Day %3d: %-6s %-11s' % (state['today'],turn,state['phase'] if state['phase'] != 'active' else world.getState('Nature','location').first())))
        if turn == 'Actor':
#            world.history[day] = {}
            if groups:
                # Make group decisions
                pass
            if config.getboolean('Actors','messages') and state['phase'] != 'none':
                # Friends exchange messages
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
                    preSurvey(world,actor,dirName,state['hurricanes']+1)
                    survey.add(actor.name)
                    count += 1
                if state['TA2BTA1C10']:
                    # Augmented pre-hurricane survey
                    surveyLimit = int(len(living)/10)
                    oldSample = {name for name,entry in state['panels']['TA2BTA1C10pre'].items() 
                        if state['hurricanes'] in entry and state['hurricanes']-1 not in entry}               
                    newSample = {name for name,entry in state['panels']['TA2BTA1C10pre'].items() 
                        if state['hurricanes']+1 in entry}
                    # Initialize pool to be anyone first used in previous hurricane
                    alive = {actor.name for actor in living}
                    existing = (oldSample - newSample) & alive
                    # Survey only part of the needed group today, unless we've already filled survey
                    dailyLimit = min(surveyLimit-len(newSample),
                        int(surveyLimit/config.getint('Disaster','phase_min_days')))
                    for i in range(dailyLimit):
                        if existing:
                            # Draw from current pool
                            name = random.choice(list(existing))
                            existing.remove(name)
                        else:
                            # Reset pool to be anyone not used lately
                            existing = alive - state['participants']['TA2BTA1C10pre']
                            if not existing:
                                # We've used everybody, so start over
                                state['participants']['TA2BTA1C10pre'] = set()
                                existing = alive - newSample
                            name = random.choice(list(existing))
                        if not name in state['panels']['TA2BTA1C10pre']:
                            state['panels']['TA2BTA1C10pre'][name] = set()
                        state['panels']['TA2BTA1C10pre'][name].add(state['hurricanes']+1)
                        state['participants']['TA2BTA1C10pre'].add(name)
                        newSample.add(name)
                        preSurvey(world,world.agents[name],dirName,state['hurricanes']+1,True)
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
                        postSurvey(actor,dirName,state['hurricanes'],previous=config.getboolean('Data','postprevious',fallback=False))
                        survey.add(actor.name)
                    else:
                        living.remove(actor)
                    count += 1
                if state['TA2BTA1C10']:
                    # Augmented pre-hurricane survey
                    surveyLimit = int(len(living)/10)
                    oldSample = {name for name,entry in state['panels']['TA2BTA1C10post'].items() 
                        if state['hurricanes']-1 in entry and state['hurricanes']-2 not in entry}               
                    newSample = {name for name,entry in state['panels']['TA2BTA1C10post'].items() 
                        if state['hurricanes'] in entry}
                    # Initialize pool to be anyone first used in previous hurricane
                    alive = {actor.name for actor in living}
                    existing = (oldSample - newSample) & alive
                    # Survey only part of the needed group today, unless we've already filled survey
                    dailyLimit = min(surveyLimit-len(newSample),
                        int(surveyLimit/config.getint('Disaster','phase_min_days')))
                    for i in range(dailyLimit):
                        if existing:
                            # Draw from current pool
                            name = random.choice(list(existing))
                            existing.remove(name)
                        else:
                            # Reset pool to be anyone not used lately
                            existing = alive - state['participants']['TA2BTA1C10post']
                            if not existing:
                                # We've used everybody, so start over
                                state['participants']['TA2BTA1C10post'] = set()
                                existing = alive - newSample
                            name = random.choice(list(existing))
                        if not name in state['panels']['TA2BTA1C10post']:
                            state['panels']['TA2BTA1C10post'][name] = set()
                        state['panels']['TA2BTA1C10post'][name].add(state['hurricanes'])
                        state['participants']['TA2BTA1C10post'].add(name)
                        newSample.add(name)
                        postSurvey(world.agents[name],dirName,state['hurricanes'],True)
        else:
            assert state['phase'] == 'active'
        debug = {}
        #            debug.update({name: {'V': True} for name in world.agents if name[:5] == 'Group'})
        #            for name in debug:
        #                for agent in world.agents[name].members():
        #                    debug[name][agent] = {}
        if turn == 'Nature':
            try:
                hurr = future[state['hurricanes']]
                if hurr:
                    select = {stateKey('Nature')}
                print(hurr)
                raise RuntimeError
            except IndexError:
                select = True
        elif maximize:
            select = 'max'
        else:
            select = True            
        newState = world.step(actions.get(turn,None),select=select,debug=debug)
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
            if turn == 'Actor' and isinstance(world.history,dict):
                world.history[day][actor.name] = joint[actor.name].first()
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
                        entry = {'action': action, 'hurricane': state['hurricanes']}
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
                visualize.addToVizData("Region", entry)
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
                    visualize.addToIndividualList(entry)
                visualize.addToVizData("Actor", entry)
       
        
def writeHurricane(world,hurricane,dirName):
    fields = ['Timestep','Name','Category','Location','Landed']
    if hurricane == 0:
        mode = 'w'
    else:
        mode = 'a'
    with open(os.path.join(dirName,'HurricaneTable.tsv'),mode) as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        if hurricane == 0:
            writer.writeheader()
        else:
            today = world.getState(WORLD,'day').first()
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
                return record                
                
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
        ages = [a.demographics['age'] for a in world.agents.values() if isinstance(a,Actor)]
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
                              sum([a.demographics['kids'] for a in table['inhabitants']])}
                    writer.writerow(record)
                    total += record['Count']
                elif field == 'Age':
                    histogram = [0 for limit in limits]
                    histogram.append(0)
                    for agent in table['inhabitants']:
                        histogram[0] += agent.demographics['kids']
                        for i in range(len(limits)):
                            if agent.demographics['age'] < limits[i]:
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
                        try:
                            value = agent.demographics[feature]
                        except KeyError:
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

preSurveyFields = ['Timestep','Participant','Hurricane']
preSurveyFields += sorted(list(demographics.keys()))
preSurveyQuestions = {'At Shelter': ('location','=shelter'),
                      'Evacuated': ('location','=evacuated'),
                      'Severity': ('Nature\'s category','round')}
preSurveyFields += sorted(list(preSurveyQuestions.keys()))
    
def preSurvey(world,actor,dirName,hurricane,TA2BTA1C10=False):
    if actor is None:
        mode = 'w'
    else:
        mode = 'a'
    fields = preSurveyFields[:]
    questions = dict(preSurveyQuestions)
    if TA2BTA1C10:
        fname = 'ActorPreNewTable'
        fields += ['LastEvacuated','LastSheltered']
        questions['LastEvacuated'] = (ACTION,'last=evacuate')
        questions['LastSheltered'] = (ACTION,'last=moveTo-shelter')
    else:
        fname = 'ActorPreTable'
    with open(os.path.join(dirName,'%s.tsv' % (fname)),mode) as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        if actor is None:
            writer.writeheader()
        else:
            today = actor.world.getState(WORLD,'day').first()
            record = {'Timestep': today,
                      'Hurricane': hurricane,
                      'Actor': actor.name,
                      'Survey': fname}
            try:
                record['Participant'] = max([entry['Participant'] for entry in preSurveyRecords if entry['Survey'] == fname]) + 1
            except ValueError:
                record['Participant'] = 1
            if TA2BTA1C10:
                # Link participant IDs when applicable
                prev = [entry for entry in preSurveyRecords if entry['Survey'] == fname and entry['Actor'] == actor.name]
                if len(prev) % 2 == 1:
                    record['Participant'] = prev[-1]['Participant']
                if hurricane == 2:
                    assert len(prev) == 1
                    assert len(prev) % 2 == 1
                    assert record['Participant'] < 17
            preSurveyRecords.append(record)
            logging.info('%s %d, Participant %d: %s' % (fname,hurricane,record['Participant'],actor.name))
            record.update(getDemographics(actor))
            # Answer questions
            belief = actor.getBelief()
            assert len(belief) == 1,'Unable to answer pre-survey with uncertain models'
            belief = next(iter(belief.values()))
            for field,answer in questions.items():
                key,fun = answer
                if not isStateKey(key):
                    if ',' in key:
                        feature,key = key.split(',')
                        agent = actor.world.getState(actor.name,feature).first()
                    else:
                        agent = actor.name
                    key = stateKey(agent,key)
                if key != ACTION:
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
                elif fun[:5] == 'last=':
                    assert isinstance(world.history,dict),'Relying on obsolete world history'
                    assert isActionKey(key)
                    for t in range(today,0,-1):
                        if fun[5:] in str(world.history.get(t,{}).get(actor.name,'')):
                            record[field] = t
                            break
                    else:
                        record[field] = 'NA'
            writer.writerow(record)

history = {} #TODO: This should reset after each hurricane
postSurveyFields = ['Timestep','Participant','Hurricane']
postSurveyFields += sorted(list(demographics.keys()))
postSurveyQuestions = {'At Shelter All Hurricanes': ('location','=shelter'),
                       'Evacuated All Hurricanes': ('location','=evacuated'),
                       'Risk All Hurricanes': ('risk','max'),
                       'Injured All Hurricanes': ('health','<0.2'),
                       'Dissatisfaction All Hurricanes': ('grievance','likert'),
                       }
postSurveyFields += sorted(list(postSurveyQuestions.keys()))

def postSurvey(actor,dirName,hurricane,TA2BTA1C10=False,previous=False):
    if actor is None:
        mode = 'w'
    else:
        mode = 'a'
    fields = postSurveyFields[:]
    questions = dict(postSurveyQuestions)
    if previous:
        fields = [field.replace('All Hurricanes','Previous Hurricane') for field in fields]
        questions = {field.replace('All Hurricanes','Previous Hurricane'): fun for field,fun in questions.items()}
    if TA2BTA1C10:
        fname = 'ActorPostNewTable'
        fields += sorted(['At Shelter Previous Hurricane','Evacuated Previous Hurricane','Risk Previous Hurricane',
            'Injured Previous Hurricane','Dissatisfaction Previous Hurricane'])
        questions.update({'At Shelter Previous Hurricane': ('location','=shelter'),
                       'Evacuated Previous Hurricane': ('location','=evacuated'),
                       'Injured Previous Hurricane': ('health','<0.2'),
#                       'Injury Adult Previous Hurricane': ('health','<0.2'),
#                       'Injury Children Previous Hurricane': ('childrenHealth','<0.2count'),
                       'Risk Previous Hurricane': ('risk','max'),
                       'Dissatisfaction Previous Hurricane': ('grievance','delta'),
#                       'Property Previous Hurricane': ('region,risk','max'),
#                       'Assistance Previous Hurricane': ('System','likert'),
                       })
    else:
        fname = 'ActorPostTable'
    with open(os.path.join(dirName,'%s.tsv' % (fname)),mode) as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        if actor is None:
            writer.writeheader()
        else:
            today = actor.world.getState(WORLD,'day').first()
            record = {'Timestep': today,
                      'Hurricane': hurricane,
                      'Actor': actor.name,
                      'Survey': fname}
            try:
                record['Participant'] = max([entry['Participant'] for entry in postSurveyRecords if entry['Survey'] == fname]) + 1
            except ValueError:
                record['Participant'] = 1
            if TA2BTA1C10:
                # Link participant IDs when applicable
                prev = [entry for entry in postSurveyRecords if entry['Survey'] == fname and entry['Actor'] == actor.name]
                if len(prev) % 2 == 1:
                    record['Participant'] = prev[-1]['Participant']
            postSurveyRecords.append(record)
            logging.info('%s %d, Participant %d: %s' % (fname,hurricane,record['Participant'],actor.name))
            record.update(getDemographics(actor))
            belief = actor.getBelief()
            assert len(belief) == 1,'Unable to answer post-survey with uncertain models'
            belief = next(iter(belief.values()))
            for field,answer in questions.items():
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
                        if 'All Hurricanes' not in field and entry['hurricane']+1 != hurricane:
                            continue
                        value = entry[feature]
                        if fun == 'max':
                            if field in record:
                                record[field] = max(record[field],toLikert(value.expectation()))
                            else:
                                record[field] = toLikert(value.expectation())
                        elif fun == 'delta':
                            if field in record:
                                record[field]['new'] = toLikert(value.expectation())
                            else:
                                record[field] = {'old': toLikert(value.expectation())}
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
                                if fun[-5:] == 'count':
                                    record[field] = record.get(field,0) + 1
                                else:
                                    record[field] = 'yes'
                                    break
                        else:
                            raise ValueError('Unknown function: %s' % (fun))
                    else:
                        if not field in record:
                            if fun[-5:] == 'count':
                                record[field] = 0
                            else:
                                record[field] = 'no'
                    if isinstance(record[field],dict):
                        delta = record[field]['new'] - record[field]['old']
                        if previous:
                            record[field] = toLikert(4.*delta+0.5)
                        else:
                            record[field] = toLikert((delta+1.)/2.)
            writer.writerow(record)
