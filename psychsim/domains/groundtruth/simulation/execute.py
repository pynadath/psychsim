import cProfile
try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO
import csv
import logging
import os
import os.path
import pickle
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


preSurveyRecords = []
postSurveyRecords = []

def runInstance(instance,args,config,rerun=True):
    if args['visualize']:
        import psychsim.domains.groundtruth.simulation.visualize as visualize
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
            if config.getint('Simulation','phase',fallback=1) == 1:
                world = loadPickle(args['instance'],run,args['reload'])
                world.addActionEffects()
            else:
                try:
                    world = loadPickle(args['instance'],run,args['reload'])
                except FileNotFoundError:
                    # Load original world, then re-apply logged states/belief states
                    world = loadPickle(args['instance'],run,0)
                    with open(os.path.join(dirName,'state%d%s.pkl' % (args['reload']-1,'Nature')),'rb') as f:
                        oldStates = pickle.load(f)
                    for name in world.agents:
                        if name[:5] == 'Actor' and name not in oldStates:
                            # He's dead Jim
                            killAgent(name,world)
                    for name,state in oldStates.items():
                        if name == '__state__':
                            world.state = state
                        else:
                            agent = world.agents[name]
                            if isinstance(state,dict):
                                for model,belief in state.items():
                                    agent.models[model]['beliefs'] = belief
                            else:
                                assert len(agent.models) == 1,'Unable to apply single belief state to multiple models'
                                next(iter(agent.models.values()))['beliefs'] = state
            population = [agent for agent in world.agents.values() if isinstance(agent,Actor)]
            try:
                population[0].demographics
            except AttributeError:
                for agent in population:
                    agent.prescription = None
                    agent.demographics = {}
                    for key,feature in oldDemographics.items():
                        agent.demographics[demographics[key]] = world.getState(agent.name,feature).first()
            try:
                population[0].config
            except AttributeError:
                for agent in population:
                    agent.config = config
            regions = {agent.name: {'agent': agent,
                                    'inhabitants': [a for a in population if a.demographics['home'] == agent.name]}
                       for agent in world.agents.values() if isinstance(agent,Region)}
            if config.getboolean('Data','livecdf',fallback=True):
                cdfTables = makeCDFTables(population,[world.agents[r] for r in regions],regions)
            else:
                cdfTables = {}
            if config.getboolean('Data','presurvey',fallback=True):
                preSurvey(world,None,dirName,0,args['TA2BTA1C10'])
            if config.getboolean('Data','postsurvey',fallback=True):
                postSurvey(None,dirName,0,args['TA2BTA1C10'],config.getboolean('Data','postprevious',fallback=False))
        else:
            scenarios = [int(name[8:-4]) for name in os.listdir(dirName) if name[:8] == 'scenario' and name[-4:] == '.pkl']
            if scenarios and not rerun:
                # Already ran this
                print('Skipping instance %d, run %d, through day %d' % (instance,run,max(scenarios)))
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
        # Let's get started
        logging.info('Running Instance %d' % (instance))
        print('Running instance %d, run %d' % (instance,run))
        if world is None:
            # Initialize new world
            world = createWorld(config)
            if config.getboolean('Data','livecdf',fallback=True):
                writeHurricane(world,0,dirName)
            if config.getboolean('Data','presurvey',fallback=True):
                preSurvey(world,None,dirName,0,False)
            if config.getboolean('Data','postsurvey',fallback=True):
                postSurvey(None,dirName,0,False,config.getboolean('Data','postprevious',fallback=False))
            if args['TA2BTA1C10']:
                preSurvey(world,None,dirName,0,True)
                postSurvey(None,dirName,0,True)
            population = [agent for agent in world.agents.values() if isinstance(agent,Actor)]
            regions = {agent.name: {'agent': agent,
                                    'inhabitants': [a for a in population if a.demographics['home'] == agent.name]}
                       for agent in world.agents.values() if isinstance(agent,Region)}
            if config.getboolean('Data','livecdf',fallback=True):
                writeCensus(world,regions,dirName)
                cdfTables = makeCDFTables(population,[world.agents[r] for r in regions],regions)
                toCDF(world,dirName,cdfTables)
            else:
                cdfTables = {}
            # Write definition files
            if args['write']:
                defDir = os.path.join(os.path.dirname(__file__),'SimulationDefinition')
                if not os.path.exists(defDir):
                    os.makedirs(defDir)
                writeDefinition(world,defDir)
            if args['pickle']:
                with open(os.path.join(dirName,'scenario0.pkl'),'wb') as outfile:
                    pickle.dump(world,outfile)
        world.setParallel(args['multiprocessing'])
        groups = [agent for agent in world.agents.values() if isinstance(agent,Group)]
        del preSurveyRecords[:]
        del postSurveyRecords[:]
        # Set up tables for visualization
        allTables = {'Region': {'fields': [#('alive','casualties','invert'),
                                           ('location','evacuated','#evacuated'),
                                           ('location','shelter','#shelter'),
                                           ('risk','safety','invert')],
                                'population': Region,
                                'series': True,
                                'log': []},
                     'Actors': {'fields': [#('alive','alive',None),
                                           ('location','shelter','=shelter'),
                                           ('location','evacuated','=evacuated'),
                                           ('risk','safety','invert'),
                                           ('health','health',None),
                     ],
                                'population': Actor,
                                'series': True,
                                'log': []},
                     'Display': {'fields': [('x','x',None),
                                            ('y','y',None),
                                            ('home','region',None)],
                                 'population': Actor,
                                 'series': False,
                                 'log': []}
        }
        if config.getboolean('System','system'):
            allTables['Actors']['fields'].append(('grievance','satisfaction','invert'))
        if args['visualize']:
            addState2tables(world,0,allTables,population,regions,config)
            
        # Load any pre-specified future hurricanes
        if args['hurricane']:
            future = readHurricaneFile(args['hurricane'])
            # Any hurricanes that are already past need to be registered as such
            hurricanes = [h for h in future if h['End'] < world.getState(WORLD,'day',unique=True)]
        else:
            future = []
        if args['profile']:
            prof = cProfile.Profile()
            prof.enable()
        if args['compile']:
            for agent in population:
                print('Compiling: %s' % (agent.name))
                print(agent.compilePi(debug=True))
                exit()
        random.seed(config.getint('Simulation','seedRun')+run)
        survey = set()
        oldPhase = world.getState('Nature','phase',unique=True)
        start = time.time()
        state = {'hurricanes': len(hurricanes),
                 'phase': world.getState('Nature','phase',unique=True),
                 'TA2BTA1C10': args['TA2BTA1C10'],
                 'election': 1,
                 'panels': {}, 'participants': {}}
        if args['TA2BTA1C10']:
            state['panels']['TA2BTA1C10pre'] = {}
            state['panels']['TA2BTA1C10post'] = {}
            state['participants']['TA2BTA1C10pre'] = set()
            state['participants']['TA2BTA1C10post'] = set()
        if not config.getboolean('Simulation','graph',fallback=False):
            season = world.getState(WORLD,'day',unique=True) // config.getint('Disaster','year_length',fallback=365)
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
        elif args['phase2predictlong'] or args['phase3predictlong']:
            for agent in population:
                if stateKey(agent.name,'resources') in world.state:
                    value = 0.9*agent.getState('resources').expectation()
                    agent.setState('resources',value)
                    beliefs = agent.getBelief()
                    model,myBelief = next(iter(beliefs.items()))
                    agent.setBelief(stateKey(agent.name,'resources'),value,model)
            world.agents['System'].setAidDynamics([agent.name for agent in population],1.5)
        if args['phase1predictshort'] or args['phase2predictshort'] or args['phase3predictshort']:
            for agent in population:
                key = stateKey(agent.name,'location')
                if key in world.state:
                    for action in list(agent.actions):
                        if action['verb'] == 'moveTo' and action['object'][:7] == 'shelter':
                            agent.actions.remove(action)
                    if world.getFeature(key,unique=True)[:7] == 'shelter':
                        # Move them home first
                        world.setFeature(key,agent.demographics['home'])
                        beliefs = agent.getBelief()
                        model,myBelief = next(iter(beliefs.items()))
                        world.setFeature(key,agent.demographics['home'],myBelief)
        # Load any prescription
        if args['prescription']:
            if args['prescription'] == 'NULL':
                # Remove aid possibility
                world.agents['System'].actions = {action for action in world.agents['System'].actions if action['verb'] != 'allocate'}
                world.agents['System'].prescription = None
                world.agents['System'].setNullGrievance([a.name for a in population])
            elif args['prescription'] == 'evaluation/Phase2/Prescribe/TA2A/ConstrainedPrescriptionCasualties.tsv':
                world.agents['System'].prescription = readPrescription(args['prescription'])
            elif args['prescription'] == 'evaluation/Phase2/Prescribe/TA2A/UnconstrainedPrescriptionCasualties.tsv':
                for agent in population:
                    agent.prescription = readPrescription(args['prescription'])
                world.agents['System'].resources = 0.1*len(population)
            elif args['prescription'] == 'evaluation/Phase2/Prescribe/TA2B/TA2B_ConstrainedPrescriptionCasualties.tsv':
                # "Evacuations subsidized as in UnconstrainedPrescriptionCasualties.tsv"
                world.agents['System'].prescription = readPrescription(args['prescription'])
            elif args['prescription'] == 'phase2prescribeshortbunconstrained':
                targets = [agent for agent in population if agent.demographics['pet'] or agent.demographics['ethnicGroup'] == 'minority'
                    or agent.demographics['age'] > 46 or agent.demographics['kids'] == 0]
                incentive = 0.1*len(population) / len(targets)
                for agent in targets:
                    evacuationIncentive(world,config,agent.name,incentive)
            elif args['prescription'] == 'phase2prescribelongb':
                # "A national weather service and alert system that notifies the population of the future path and category of an impending hurricane is implemented"
                config['System']['broadcast_category'] = 'yes'
                # "ALl actors with wealth > 4 are taxed at a rate of 50%"
                world.agents['System'].resources = 0
                for agent in population:
                    wealth = agent.getState('resources',unique=True)
                    if toLikert(wealth,7) > 4:
                        world.agents['System'].resources += wealth/2
                        agent.setState('resources',wealth/2)
                # "All hurricane shelters are modified to include pet facilities that allow anyone who has a pet to bring them with them to the shelter"
                for region in regions:
                    key = stateKey(region,'shelterPets')
                    if key in world.variables:
                        world.setFeature(key,True)
                        # Assume nominal cost to build pet facilities
                        world.agents['System'].resources -= 1
                # "Evacuations subsidized as in UnconstrainedPrescriptionCasualties.tsv"
                targets = [agent for agent in population if agent.demographics['pet'] or agent.demographics['ethnicGroup'] == 'minority'
                    or agent.demographics['age'] > 46 or agent.demographics['kids'] == 0]
                incentive = world.agents['System'].resources / len(targets)
                for agent in targets:
                    key = stateKey(agent.name,'resources')
                    action = ActionSet(Action({'subject': agent.name,'verb': 'evacuate'}))
                    tree = world.dynamics[key][action].children[True]
                    cost = tree[makeFuture(key)][makeFuture(key)][CONSTANT]
                    tree[makeFuture(key)][makeFuture(key)][CONSTANT] = cost+incentive
                # "Pet owners have their pets remanded to an area that can only be visited via the evacuation action"
                # Has no effect: there is no value associated with visitation/separation, only whether the pet lives or dies
            elif args['prescription'] == 'phase2prescribelonga':
                """Raise the perception of risk / fear surrounding each hurricane by devoting
                more television and radio airtime; as also online and print ads to (i)
                sponsored reportage about the imminence of hurricanes this season; and
                (ii) documentary evidence regarding the danger of hurricanes and their
                consequences. This coverage should feature the benefits of evacuation."""
                config['System']['broadcast_category'] = 'yes'
                """Implement a tax policy"""
                world.agents['System'].resources = 0
                for agent in population:
                    wealth = agent.getState('resources',unique=True)
                    bracket = toLikert(wealth,7)
                    if bracket > 4:
                        if bracket == 7:
                            tax = .75*wealth
                        elif bracket == 6:
                            tax = wealth/2
                        elif bracket == 5:
                            tax = wealth/4
                        world.agents['System'].resources += tax
                        agent.setState('resources',wealth-tax)
                """Offer monetary incentive to evacuate"""
                """Offer additional 100% bonus to members of a minority religion to evacuate
                (they receive 2 times what a non-minority religion member would receive)."""
                targets = {agent.name for agent in population if agent.demographics['religion'] == 'minority'}
                incentive = world.agents['System'].resources / (len(population)+len(targets))
                for agent in population:
                    key = stateKey(agent.name,'resources')
                    action = ActionSet(Action({'subject': agent.name,'verb': 'evacuate'}))
                    tree = world.dynamics[key][action].children[True]
                    cost = tree[makeFuture(key)][makeFuture(key)][CONSTANT]
                    if agent.name in targets:
                        tree[makeFuture(key)][makeFuture(key)][CONSTANT] = cost+2*incentive
                    else:
                        tree[makeFuture(key)][makeFuture(key)][CONSTANT] = cost+incentive
            else:
                world.agents['System'].prescription = readPrescription(args['prescription'])
                if isinstance(world.agents['System'].prescription,list):
                    if 'Field' in world.agents['System'].prescription[0]:
                        # In/Offseason prediction
                        targets = set()
                        for entry in world.agents['System'].prescription[:]:
                            if entry['Action'].strip() == 'reinforce':
                                if entry['Value'] == 'Old':
                                    assert entry['Field'].strip() == 'age'
                                    targets |= set([a.name for a in sorted(population,key=lambda a: a.demographics[entry['Field'].strip()],
                                        reverse=True)[:int(round(len(population)/10))]])
                                else:
                                    targets |= {agent.name for agent in population if agent.demographics[entry['Field'].strip()] == entry['Value'].strip()}
                                world.agents['System'].prescription.remove(entry)
                            elif entry['Action'].strip() == 'pay':
                                pass
                        for name in targets:
                            world.agents[name].reinforceHome(config)
        else:
            world.agents['System'].prescription = None
        if args['target']:
            for name,prescription in args['target']:
                world.agents[name].prescription = readPrescription(prescription)
        if args['tax']:
            total = 0.
            for name in args['tax']:
                # Tax time!
                agent = world.agents[name]
                if agent.getState('alive').first():
                    value = agent.getState('resources')
                    assert len(value) == 1
                    value = value.first()
                    delta = value/5.
                    total += delta
                    agent.setState('resources',value-delta)
            world.agents['System'].resources = int(100*total)
        if args['aid']:
            world.agents['System'].prescription = args['aid'][:]
            world.agents['System'].setAidDynamics([a.name for a in population])
        terminated = False
        while True:
            if isinstance(args['number'],int):
                if state['hurricanes'] >= args['number']:
                    # Hurricane-based stopping condition is satisfied
                    terminated = True
            elif isinstance(args['days'],int):
                if world.getState(WORLD,'day').first() > args['days']:
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
                elif state['phase'] == 'none' and world.getState('Nature','days',unique=True) >= config.getint('Disaster','phase_min_days'):
                    break
            nextDay(world,groups,state,config,dirName,survey,start,cdfTables,future=future,maximize=args['max'])
            if args['visualize']:
                addState2tables(world,world.getState(WORLD,'day',unique=True)-1,allTables,population,regions,config)
                visualize.addDayToQueue(world.getState(WORLD,'day',unique=True)-1)
            hurricaneEntry = writeHurricane(world,state['hurricanes']+1,dirName)
            if args['visualize']:
                if hurricaneEntry is not None:
                    visualize.addToVizData("hurricane", hurricaneEntry)
            newSeason = False
            if world.getState(WORLD,'day',unique=True) - season*config.getint('Disaster','year_length',fallback=365) > config.getint('Disaster','season_length'):
                # Might be a new season
                if world.getState('Nature','phase',unique=True) == 'none' \
                    and world.getState('Nature','days',unique=True) > config.getint('Disaster','phase_min_days'):
                    newSeason = True
                elif world.getState('Nature','phase',unique=True) == 'approaching' \
                    and world.getState('Nature','days',unique=True) == 0:
                    world.setState('Nature','phase','none')
                    world.setState('Nature','days',config.getint('Disaster','phase_min_days')+1)
                    world.setState('Nature','location','none')
                    world.setState('Nature','category',0)
                    newSeason = True
            if newSeason:
                # Jump to new season
                if config.getint('Simulation','phase',fallback=1) == 1:
                    phase = stateKey('Nature','phase')
                    dayKey = stateKey('Nature','days')
                    evolution = ActionSet([Action({'subject': 'Nature','verb': 'evolve'})])
                    treePhase = world.dynamics[phase][evolution]
                    world.setDynamics(phase,evolution,makeTree(setToConstantMatrix(phase,'none')))
                    treeDays = world.dynamics[dayKey][evolution]
                    world.setDynamics(dayKey,evolution,makeTree(setToConstantMatrix(dayKey,0)))
    #                world.printState()
                    first = True
                    while world.getState(WORLD,'day',unique=True) < season*config.getint('Disaster','year_length',fallback=365):
                        # Advance simulation to next season
                        names = world.next()
                        turn = world.agents[next(iter(names))].__class__.__name__
                        print('Fast-forward:',world.getState(WORLD,'day',unique=True),turn)
                        if turn == 'Actor':
                            if first:
                                actions = {name: ActionSet([Action({'subject': name,'verb': 'moveTo', 'object': world.agents[name].home})]) for name in names}
                            else:
                                actions = {name: ActionSet([Action({'subject': name,'verb': 'stayInLocation'})]) for name in names}
                            world.step(actions,select='max' if args['max'] else True)
                            first = False
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
                else:
                    fastForward(world,config)
                state['phase'] = world.getState('Nature','phase',unique=True)
#                print('Next season')
#                world.printState()
                season += 1
                if isinstance(args['seasons'],int) and season >= args['seasons']:
                    # All done
                    break
                if args['pickle']:
                    # Not done, but let's just save after fast-forwarding
                    day = world.getState(WORLD,'day',unique=True)
                    with open(os.path.join(dirName,'scenario%d.pkl' % (day)),'wb') as outfile:
                        pickle.dump(world,outfile)
        logging.info('Total time: %f' % (time.time()-start))
        if args['pickle']:
            print('Pickling...')
            if config.getboolean('Simulation','graph',fallback=False):
                day = 1
            else:
                day = world.getState(WORLD,'day',unique=True)
            with open(os.path.join(dirName,'scenario%d.pkl' % (day)),'wb') as outfile:
                pickle.dump(world,outfile)
        elif args['xml']:
            print('Saving...')
            world.save(os.path.join(dirName,'scenario.psy'))
#        else:
#            with open(os.path.join(dirName,'scenario.pkl'),'w') as outfile:
#                print('%d' % (state['hurricanes']),file=outfile)
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
    state['today'] = world.getState(WORLD,'day',unique=True)
    logging.info('Day %d' % (state['today']))
    day = state['today']
    if config.getboolean('Data','livecdf',fallback=True):
        updateCDF(world,dirName,cdfTables)
    while day == state['today']:
        if config.getint('Simulation','phase',fallback=1) < 3:
            living = [a for a in world.agents.values() if isinstance(a,Actor) and a.getState('alive',unique=True)]
        else:
            living = []
            for actor in [a for a in world.agents.values() if isinstance(a,Actor) and stateKey(a.name,'health') in world.state]:
                if float(actor.getState('health')) > config.getfloat('Actors','life_threshold'):
                    # still going strong
                    living.append(actor)
                else:
                    # not so much
                    killAgent(actor.name,world)
        agents = world.next()
        turn = world.agents[next(iter(agents))].__class__.__name__
        if start:
            print('Day %3d: %-6s %-11s (%8.2f)' % (state['today'],turn,state['phase'] if state['phase'] != 'active' else world.getState('Nature','location',unique=True),time.time()-start))
        else:
            print(('Day %3d: %-6s %-11s' % (state['today'],turn,state['phase'] if state['phase'] != 'active' else world.getState('Nature','location',unique=True))))
        if turn == 'Actor':
#            world.history[day] = {}
            if config.getboolean('Actors','messages') and state['phase'] != 'none':
                logEdge('Actor friendOf Actor','ActorBeliefOfNature\'s category','often','Actors share their beliefs about the hurricane\'s category with their friends on a daily basis and their beliefs are influence by the incoming messages')
                #//GT: edge 94; from 54; to 11; 1 of 2; next 1 lines
                exchangeMessages(world,config,world.state,living)

        elif turn == 'System' and config.getint('System','election_effect',fallback=0) > 0:
            freq = config.get('System','election_frequency',fallback='season')
            electionT = state['today']
            if freq == 'season':
                electionT /= config.getint('Disaster','year_length',fallback=365) + 1
            elif freq == 'hurricane':
                electionT = state['hurricanes']
            if electionT > state['election']:
                # Time for a new election
                world.agents['System'].election(living)
                state['election'] = electionT
        if state['phase'] == 'approaching':
            history.clear()
            if turn == 'Actor' and survey is not None and config.getboolean('Data','presurvey',fallback=True):
                # Pre-hurricane survey
                surveyLimit = int(round(len(living)*config.getfloat('Data','presample')))
                if len(survey) < surveyLimit:
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
            if turn == 'Actor' and survey is not None and state['hurricanes'] > 0 and config.getboolean('Data','postsurvey',fallback=True):
                # Post-hurricane survey
                surveyLimit = int(round(len(living)*config.getfloat('Data','postsample')))
                if len(survey) < surveyLimit:
                    sampleLimit = int(float(len(living))*config.getfloat('Data','postsample')/
                                      float(config.getint('Disaster','phase_min_days')))
                    remaining = {actor.name for actor in living} - survey
                    count = 0
                    while count < sampleLimit and remaining:
                        actor = world.agents[random.choice(list(remaining))]
                        remaining.remove(actor.name)
                        if actor.getState('alive',unique=True):
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
            assert state['phase'] == 'active','Phase has incorrect value of %s' % (state['phase'])
        if turn == 'Nature':
            try:
                hurr = future[state['hurricanes']]
                if hurr:
                    select = {}
                    key = stateKey('Nature','phase')
                    if day+1 < hurr['Start']:
                        setTrack = False
                        select[key] = world.value2float(key,'none')
                    elif day+1 < hurr['Landfall']:
                        setTrack = True
                        select[key] = world.value2float(key,'approaching')
                    elif day+1 < hurr['End']+1:
                        setTrack = True
                        select[key] = world.value2float(key,'active')
                    else:
                        setTrack = False
                        select[key] = world.value2float(key,'none')
                    key = stateKey('Nature','location')
                    if setTrack:
                        if hurr['Actual Location'][day+1-hurr['Start']] == 'leaving':
                            select[key] = world.value2float(key,'none')
                        else:
                            select[key] = world.value2float(key,hurr['Actual Location'][day+1-hurr['Start']])
                    else:
                        select[key] = world.value2float(key,'none')
                    key = stateKey('Nature','category')
                    if setTrack:
                        select[key] = world.value2float(key,int(hurr['Actual Category'][day+1-hurr['Start']]))
                    else:
                        select[key] = world.value2float(key,0)
                else:
                    select = True
            except IndexError:
                select = True
        elif maximize:
            select = 'max'
        else:
            select = True
        policy = actions.get(turn,None)
        if policy:
            policy = dict(policy)
        if world.agents['System'].prescription:
            # Anything to specify here?
            if isinstance(world.agents['System'].prescription,list):
                for entry in world.agents['System'].prescription:
                    if isinstance(entry,dict):
                        if turn == 'Actor':
                            assert entry['Value'][0] == '<','Unknown value filter: %s' % (entry['Value'])
                            targets = {actor for actor in living if float(actor.getState(entry['Field'])) < float(entry['Value'][1:])}
                            if entry['Action'].strip() == 'pay':
                                old = float(actor.getState('resources'))
                                actor.setState('resources',old+(actor.demographics['wealth']-old)/10)
                            elif entry['Action'].strip() == 'evacuate':
                                for actor in targets:
                                    for action in actor.actions:
                                        if action['verb'] == 'evacuate':
                                            if policy is None:
                                                policy = {}
                                            policy[actor.name] = action
                                            break
                                    else:
                                        raise ValueError('Unable to find %s action for %s' % (verb,actor.name))
                            else:
                                raise NameError('Unknown prescription action: %s' % (entry['Action']))
            elif day in world.agents['System'].prescription:
                entry = world.agents['System'].prescription[day]
                if 'Region(To issue mandatory evacuation)' in entry:
                    if turn == 'Actor':
                        region = entry['Region(To issue mandatory evacuation)']
                        if region != 'Not applicable':
                            if policy is None:
                                policy = {}
                            for actor in living:
                                if actor.demographics['home'] == region:
                                    if actor.getState('location',unique=True) == 'evacuated':
                                        verb = 'stayInLocation'
                                    else:
                                        verb = 'evacuate'
                                    for action in actor.actions:
                                        if action['verb'] == verb:
                                            policy[actor.name] = action
                                            break
                                    else:
                                        raise ValueError('Unable to find %s action for %s' % (verb,actor))
                else:
                    # Must be a System aid allocation policy
                    assert 'Region' in entry,'Unknown policy type: %s' % (entry)
        if turn == 'Actor':
            for actor in living:
                if actor.prescription is not None:
                    verb = None
                    if isinstance(actor.prescription,list):
                        if 'current_location' in actor.prescription[0]:
                            # Phase 2 Prescription from TA2A
                            location = world.getState('Nature','location',unique=True)
                            targets = {entry['next_location'] for entry in actor.prescription if entry['current_location'] == location}
                            if actor.demographics['home'] in targets:
                                incentive = world.agents['System'].resources/len([agent for agent in living if agent.demographics['home'] in targets])
                                evacuationIncentive(world,config,actor.name,incentive)
                            else:
                                evacuationIncentive(world,config,actor.name,0)
                            continue
                        else:
                            belief = actor.getBelief()
                            for entry in actor.prescription:
                                try:
                                    val = int(entry['Value1'])
                                except ValueError:
                                    val = entry['Value1']
                                if world.getFeature(entry['Field1']).get(val) < 0.5:
                                    continue
                                if entry['Field2']:
                                    for val in entry['Value2'].split(','):
                                        if world.getFeature(entry['Field2']).get(val) > 0.5:
                                            break
                                        else:
                                            # Does not match
                                            continue
                                break
                            else:
                                logging.warning('No entry when %s=%s' % (entry['Field1'],world.getFeature(entry['Field1'])))
                                continue
                    elif day in actor.prescription:
                        entry = actor.prescription[day]
                    else:
                        entry = None
                    if entry:
                        if policy is None:
                            policy = {}
                        for action in actor.actions:
                            if entry['Action'] == 'shelter':
                                if action['verb'] == 'moveTo' and action['object'][:7] == 'shelter':
                                    policy[actor.name] = action
                                    break
                            elif entry['Action'] == 'moveTo':
                                if action['verb'] == 'moveTo' and action['object'][:7] != 'shelter':
                                    policy[actor.name] = action
                                    break
                            elif entry['Action'] == action['verb']:
                                policy[actor.name] = action
                                break
                        else:
                            raise ValueError('Unable to find action %s for %s' % (entry['Action'],actor.name))
        if turn == 'Nature' and config.getint('Simulation','phase',fallback=1) >= 3:
            newState = world.agents[turn].step(select)
        else:
            debug = {name: {} for name in world.agents if name[:len(turn)] == turn}
        #            debug.update({name: {'V': True} for name in world.agents if name[:5] == 'Group'})
        #            for name in debug:
        #                for agent in world.agents[name].members():
        #                    debug[name][agent] = {}
            newState = world.step(policy,select=select,debug=debug)

        if config.getint('Simulation','phase',fallback=1) == 1:
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
        else:
            record = {agent.name: agent.getBelief() for agent in living}
            record.update({name: world.agents[name].getBelief() for name in world.agents if name[:5] == 'Group'})
            record['__state__'] = world.state
            with open(os.path.join(dirName,'state%d%s.pkl' % (day,turn)),'wb') as outfile:
                pickle.dump(record,outfile)            
        for actor in living:
            if turn == 'Actor' and isinstance(world.history,dict):
                world.history[day][actor.name] = world.getFeature(actionKey(actor.name),newState,unique=True)
            if config.getint('Simulation','phase',fallback=1) == 1:
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
        if state['phase'] == 'active' and config.getint('Simulation','phase',fallback=1) == 1:
            # Record what these doomed souls did to postpone the inevitable
            evacuees = 0
            shelter = 0
            for agent in living:
#            for name,action in joint.items():
#                agent = world.agents[name]
#                if isinstance(agent,Actor):
#                    if agent.getState('alive').first():
                        belief = agent.getBelief()
                        assert len(belief) == 1,'Unable to store beliefs over uncertain models'
                        belief = next(iter(belief.values()))
                        entry = {'action': world.getFeature(actionKey(actor.name),newState,unique=True), 'hurricane': state['hurricanes']}
                        features = ['location','risk','health']
                        if config.getboolean('System','system'):
                            features.append('grievance')
                        for feature in features:
                            entry[feature] = agent.getState(feature,belief)
                            if feature == 'location':
                                if entry[feature].first() == 'evacuated':
                                    evacuees += 1
                                elif entry[feature].first()[:7] == 'shelter':
                                    shelter += 1
                        history[agent.name] = history.get(agent.name,[])+[entry]
            if 'QualitativeData' in cdfTables:
                qualData = cdfTables['QualitativeData'][-1]
                qualData['evacuated'] = max(evacuees,qualData.get('evacuated',0))
                qualData['went to shelters'] = max(shelter,qualData.get('shelter',0))
        day = world.getState(WORLD,'day',unique=True)
        phase = world.getState('Nature','phase',unique=True)
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



from pprint import pprint
import traceback
deadInfo = {}
def addState2tables(world,day,tables,population,regions,config):
    # Grab all of the relevant fields, but only once
    values = {agent.name: {} for agent in population}
    #print(values)
    for agent in population:

        alive = True
        try:
            if float(agent.getState('health')) > config.getfloat('Actors','life_threshold'):
                pass
        except KeyError:
            print ("Agent %s is dead :("%agent.name )
            alive = False
            
        #pprint ("Agent Name %s %s" %(agent.name, dir(agent)))
        #pprint ("Agent Name %s %s" %(agent.name, vars(agent)))
        for table in tables.values():
            if not table['population'] is Nature:
                for feature,label,function in table['fields']:
                    if not feature in values[agent.name]:
                        try:
                            if alive:
                                if feature == 'health' or feature == 'childrenHealth':
                                    values[agent.name][feature]  = world.agents[agent].health
                                elif feature == 'location':
                                    values[agent.name][feature]  = world.agents[agent].demographics['home']   
                                elif feature == 'resources':
                                    values[agent.name][feature]  = world.agents[agent].demographics['wealth']
                                elif feature == 'employed':
                                    values[agent.name][feature]  = world.agents[agent].demographics['job']
                                elif feature == 'risk':
                                    values[agent.name][feature]  = world.getState(world.agents[agent].demographics['home'],'risk') 
                                
                                elif feature in agent.demographics:
                                    values[agent.name][feature] = agent.demographics[feature]
                                elif feature == 'x':
                                    values[agent.name][feature] = agent.x
                                elif feature == 'y':
                                    values[agent.name][feature] = agent.y
                                elif feature == "grievance":
                                    values[agent.name][feature] = agent.grievance 
                                else:
                                    print ("Skipping, Did not add Feature to table. %s not in %s"%(feature, agent.demographics))

                        except KeyError:
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
                        try:
                            entry[label] = len([a for a in inhabitants if values[a.name][feature][:len(target)] == target])
                        except KeyError:
                            print("Error",target)
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
                entry = checkNegative(entry)
                
                visualize.addToVizData("Region", entry)
                
        elif table['population'] is Actor:
            for actor in population:

                entry = {'day': day,'participant': actor.name[-4:]}

                # try:
                #     belief = next(iter(actor.getBelief().values()))
                # except Exception as e:
                #     print("Error %s"%(actor.name))

                #     traceback.print_exc()  
                #     alive = False

                alive = True
                try:
                    if float(actor.getState('health')) > config.getfloat('Actors','life_threshold'):
                        pass
                except KeyError:
                    print ("Agent %s is dead :("%actor.name )
                    alive = False
                if alive == True:
                    for feature,label,function in table['fields']:
                        if feature in actor.demographics:
                            entry[label] = values[actor.name][feature]
                        else:
                            key = stateKey(actor.name,feature)
                            if key in world.variables and world.variables[key]['domain'] is bool:
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
                    entry['alive'] = True
                    if entry['participant'] in deadInfo:
                        pass
                    
                    else:
                        deadInfo[entry['participant']] = {}    
                    
                    if 'x' in entry:
                        deadInfo[entry['participant']]['x'] = entry['x']
                    if 'y' in entry:
                        deadInfo[entry['participant']]['y'] = entry['y']
                    if 'region' in entry:
                        deadInfo[entry['participant']]['region'] = entry['region']
                    table['log'].append(entry)
                else:
                    entry['alive'] = False
                    if (entry['participant'] in deadInfo):
                        entry['x'] = deadInfo[entry['participant']].get('x', 0)
                        entry['y'] = deadInfo[entry['participant']].get('y', 0)
                        entry['region'] = deadInfo[entry['participant']].get('region', 'Region01')
                        
                #print("Actor %s"%(entry))
                #print("Keys %s\nValues %s" %(entry.keys(), entry.values()))
                if 'x' in list(entry.keys()) and 'y' in list(entry.keys()):
                    entry = checkNegative(entry)
                    visualize.addToIndividualList(entry)
                entry = checkNegative(entry)
                visualize.addToVizData("Actor", entry)
                
                #print("Added Entry: %s"%entry)

def checkNegative(entry):
    entrydict = dict ((k,v) for k,v in entry.items() if (type(v)  is int or type(v) is float) and v < 0 )
    if (len(entrydict) > 0):

        for (k,v) in entrydict.items():
            print("Clamping %s to 0 from %f" %(k, v))
            entry[k] = 0 
    
    return entry

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
            today = world.getState(WORLD,'day',unique=True)
            phase = world.getState('Nature','phase',unique=True)
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
                        record[field] = world.getState('Nature',field.lower(),unique=True)
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
                            value = agent.getState(feature,unique=True)
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

def fastForward(world,config):
    if config.getint('Simulation','phase',fallback=1) < 3:
        beliefs = {name: next(iter(world.agents[name].getBelief().values())) for name in world.agents
            if name[:5] == 'Actor' and world.getState(name,'alive').first()}
    else:
        beliefs = {name: next(iter(world.agents[name].getBelief().values())) for name in world.agents
            if name[:5] == 'Actor' and stateKey(name,'health') in world.state.keys()}
        print(len(beliefs),'agents still alive')
    for key in world.state.keys():
        if isStateKey(key):
            agent,feature = state2tuple(key)
            if feature[0] == '_':
                # Special key (model, turn, action, reward)
                continue
            if agent == 'Nature':
                if feature == 'category' or feature == 'days':
                    value = 0
                elif feature == 'phase' or feature == 'location':
                    value = 'none'
                else:
                    raise NameError('Unhandled key: %s' % (key))
                world.setFeature(key,value)
                for belief in beliefs.values():
                    world.setFeature(key,value,belief)
            elif agent[:len('Region')] == 'Region':
                if feature == 'risk':
                    value = world.agents[agent].risk
                elif feature == 'shelterRisk':
                    riskLevel = int(config.get('Shelter','risk').split(',')[world.agents[agent].configIndex()])
                    if riskLevel > 0:
                        value = likert[5][riskLevel-1]
                    else:
                        value = 0.
                else:
                    value = None
                if value is not None:
                    world.setFeature(key,value)
                    for name,value in beliefs.items():
                        if world.agents[name].demographics['home'] == 'agent':
                            world.setFeature(key,value,beliefs[name].keys())
            elif agent[:len(WORLD)] == WORLD:
                if feature == 'day':
                    world.setFeature(key,config.getint('Disaster','year_length',fallback=365)+1)
                else:
                    raise NameError('Unhandled key: %s' % (key))
            elif agent[:len('Actor')] == 'Actor':
                if config.getint('Simulation','phase',fallback=1) < 3:
                    if not world.getState(agent,'alive').first():
                        continue
                if feature == 'health' or feature == 'childrenHealth':
                    value = world.agents[agent].health
                elif feature == 'location':
                    value = world.agents[agent].demographics['home']
                elif feature == 'resources':
                    value = world.agents[agent].demographics['wealth']
                elif feature == 'employed':
                    value = world.agents[agent].demographics['job']
                elif feature == 'risk':
                    value = world.getState(world.agents[agent].demographics['home'],'risk')
                else:
                    value = None
                if value is not None:
                    world.setFeature(key,value)
                    world.setFeature(key,value,beliefs[agent])
            elif agent[:len('Group')] == 'Group':
                # Group features don't change
                pass
            else:
                assert agent == 'System'
        else:
            assert isBinaryKey(key)
            # Relationships don't change
            pass
    for name,belief in beliefs.items():
        model = next(iter(world.agents[name].getBelief().keys()))
        world.agents[name].models[model]['beliefs'] = belief

def exchangeMessages(world,config,state,living):
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
    if config.getint('Simulation','phase',fallback=1) == 1:
        # Original phase 1 messages
        for actor in living:
            friends = [friend for friend in actor.friends
                       if world.agents[friend] in living]
            if friends:
                key = stateKey('Nature','category')
                for friend in friends:
                    yrBelief = next(iter(world.agents[friend].getBelief(state).values()))
                    msg = yrBelief[key]
                    logging.info('%s receives message %s from %s' % (actor.name,msg,friend))
                    actor.recvMessage(key,msg,myScale,optScale,pessScale)
    else:
        # Phase 2 messages
        key = stateKey('Nature','category')
        beliefs = {actor.name: actor.getBelief(state) for actor in living}
        beliefs = {name: next(iter(belief.values())) if isinstance(belief,dict) else belief for name,belief in beliefs.items()}
        messages = {}
        for actor in living:
            friends = [friend for friend in actor.friends
                       if world.agents[friend] in living]
            msg = [beliefs[friend][key] for friend in friends]
            if config.getboolean('System','broadcast_category',fallback=False):
                msg.append(world.getFeature(key,state))
            if msg:
                messages[actor.name] = msg
                logging.info('%s receives message %s' % (actor.name,msg))
                actor.recvMessage(key,msg,myScale,optScale,pessScale)

def killAgent(name,world):
    toDelete = [key for key in world.state.keys() if (isStateKey(key) and state2agent(key) == name) or \
        (isBinaryKey(key) and key2relation(key)['subject'] == name)]
    try:
        # VectorDistributionSet
        world.state.deleteKeys(toDelete)
    except AttributeError:
        # KeyedVector
        for key in toDelete:
            del world.state[key]
    world.dependency.deleteKeys(set(toDelete))

    logEdge('Actor\'s health','Actor memberOf Group','sometimes','Actors can no longer be group members when they die')
    #//GT: edge 93; from 21; to 52; 1 of 1; next 3 lines
    for group in [g for g in world.agents if g[:5] == 'Group']:
        if name in world.agents[group].potentials:
            world.agents[group].potentials.remove(name)

    logEdge('Actor\'s health','Actor marriedTo Actor','sometimes','Actors are no longer married if their spouse dies')
    #//GT: edge 94; from 21; to 22; 1 of 1; next 2 lines
    actor = world.agents[name]
    try:
        if actor.spouse is not None:
            world.agents[actor.spouse].spouse = None
    except AttributeError:
        pass

    logEdge('Actor\'s health','Actor friendOf Actor','sometimes','Actors cannot be friends with dead people')
    #//GT: edge 95; from 21; to 57; 1 of 1; next 3 lines
    for friend in [f for f in world.agents.values() if f.name[:5] == 'Actor']:
        if name in friend.friends:
            friend.friends.remove(name)

def evacuationIncentive(world,config,name,incentive):
    cost = likert[5][config.getint('Actors','evacuation_cost')-1]
    key = stateKey(name,'resources')
    action = ActionSet(Action({'subject': name,'verb': 'evacuate'}))
    tree = world.dynamics[key][action].children[True]
    tree[makeFuture(key)][makeFuture(key)][CONSTANT] = incentive-cost
