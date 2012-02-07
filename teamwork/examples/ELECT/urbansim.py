import cStringIO
import datetime
import fileinput
import os.path
import sys
import time
from psychsim_interface import USim_Proxy
from strategies import SamplingStrategy,CorrectSamplingStrategy
from teamwork.math.KeyedVector import KeyedVector
from teamwork.math.Keys import StateKey,LinkKey
from teamwork.action.PsychActions import Action
from teamwork.multiagent.pwlSimulation import loadScenario

floors = {'Economics': -1.,
          'Governance': -1.,
          'HN Security Forces': 0.,
          'Essential Services': 0.,
          'Civil Security': -1.,
          'Information Operations': -1.,
          'Population Support': -1.,
          }

def parsePrecondition(root):
    conditions = []
    node = root.firstChild
    while node:
        if node.nodeType == node.ELEMENT_NODE:
            if node.tagName == 'USER_ACTION_PRECONDITION':
                conditions.append({'type': 'action',
                                   'subject': str(node.getAttribute('SUBJECT')),
                                   'verb': str(node.getAttribute('VERB1')),
                                   'object': str(node.getAttribute('OBJECT'))})
            elif node.tagName == 'WORLD_STATE_PRECONDITION':
                if str(node.getAttribute('OPERATOR')) == 'LESSTHAN':
                    test = lambda value,threshold=float(node.getAttribute('VALUE')):\
                           value < threshold
                elif str(node.getAttribute('OPERATOR')) == 'GREATERTHAN':
                    test = lambda value,threshold=float(node.getAttribute('VALUE')):\
                           value > threshold
                elif str(node.getAttribute('OPERATOR')) == 'EQUAL':
                    test = lambda value,threshold=float(node.getAttribute('VALUE')):\
                           value == threshold
                else:
                    raise ValueError,'Unknown operator: %s' % (str(node.getAttribute('OPERATOR')))
                condition = {'type': 'state',
                             'key': StateKey({'entity': str(node.getAttribute('SUBJECT')),
                                              'feature': str(node.getAttribute('ATTRIBUTE'))}),
                             'test': test}
                if len(condition['key']['entity']) == 0:
                    # Tied to class, not specific entity
                    nodeList = node.getElementsByTagName('CLASS')
                    assert len(nodeList) == 1,'Multiple CLASS elements in WORLD_STATE_PRECONDITION'
                    condition['key']['entity'] = str(nodeList[0].firstChild.data).strip()
                conditions.append(condition)
            elif node.tagName == 'TIME_PRECONDITION':
                condition = {'type': 'time'}
                child = node.firstChild
                while child:
                    if child.nodeType == child.ELEMENT_NODE:
                        if child.tagName == 'EXACT_DATE':
                            start = datetime.date(2008,10,10)
                            year,month,day = map(int,str(child.firstChild.data).split('-'))
                            condition['day'] = (datetime.date(year,month,day)-start).days
                        elif child.tagName == 'RELATIVE_EVENT':
                            condition['day'] = int(child.getAttribute('DAYS'))
                            condition['event'] = str(child.firstChild.data)
                        else:
                            raise NameError,'Unknown time precondition: %s' % (child.tagName)
                    child = child.nextSibling
                conditions.append(condition)
            else:
                raise NameError,'Unknown precondition: %s' % (node.tagName)
        node = node.nextSibling
    return conditions

def parseEffect(root):
    effects = []
    node = root.firstChild
    while node:
        if node.nodeType == node.ELEMENT_NODE:
            effect = {'feature': str(node.getAttribute('FEATURE'))}
            if node.tagName == 'ABSOLUTE_EFFECT':
                effect['value'] = float(node.getAttribute('VALUE'))
            elif node.tagName == 'RELATIVE_EFFECT':
                effect['delta'] = float(node.getAttribute('DELTA'))
            else:
                raise NameError,'Unknown effect type: %s' % (node.tagName)
            child = node.firstChild
            while child:
                if child.nodeType == child.ELEMENT_NODE:
                    if child.tagName == 'EFFECT_SUBJECT':
                        effect['subject'] = str(child.getAttribute('SUBJECT'))
                    elif child.tagName == 'EFFECT_COLOCATION':
                        location = str(child.getAttribute('EXACT_LOCATION')).strip().upper()
                        if location:
                            effect['colocation'] = location
                    else:
                        raise NameError,'Unknown effect field: %s' % (child.tagName)
                child = child.nextSibling
            effects.append(effect)
        node = node.nextSibling
    return effects

def parseEvent(root):
    event = {'fired': -1,'preconditions':[]}
    node = root.firstChild
    while node:
        if node.nodeType == node.ELEMENT_NODE:
            if node.tagName == 'PRECONDITIONS':
                event['preconditions'] += parsePrecondition(node)
            elif node.tagName == 'EFFECTS':
                event['effects'] = parseEffect(node)
            elif node.tagName == 'EVENT_PREREQ':
                event['preconditions'].append({'type': 'event',
                                               'name':node.firstChild.data})
        node = node.nextSibling
    return event
        
def parseStories(filename,scenario):
    try:
        doc = minidom.parse(filename)
    except IOError:
        sys.stderr.write('Unable to parse story file: %s\n' % (filename))
        return {}
    stories = {}
    node = doc.documentElement.firstChild
    while node.nodeType != node.ELEMENT_NODE or \
            node.tagName.lower() != 'arrayofstory':
        node = node.nextSibling
    node = node.firstChild
    while node:
        if node.nodeType == node.ELEMENT_NODE:
            assert node.tagName == 'STORY'
            if str(node.getAttribute('SCENARIO_ID')) == scenario:
                story = str(node.getAttribute('STORY_TITLE'))
                child = node.firstChild
                while child:
                    if child.nodeType == node.ELEMENT_NODE:
                        if child.tagName == 'EVENT':
                            event = str(child.getAttribute('EVENT_TITLE'))
                            if stories.has_key(event):
                                event = '%s (%s)' % (event,story)
                            stories[event] = parseEvent(child)
                            stories[event]['story'] = story
                    child = child.nextSibling
        node = node.nextSibling
    return stories

def applyStories(stories,scenario,day,player,doc):
    root = doc.documentElement.firstChild
    while root:
        if root.nodeType == root.ELEMENT_NODE:
            if root.tagName == 'GAMETURN':
                break
        root = root.nextSibling
    # Potential story effects go here
    cycle = doc.createElement('CYCLE')
    cycle.setAttribute('CYCLE_ID','0')
    cycle.setAttribute('LETHAL','0')
    cycle.setAttribute('NONLETHAL','0')
    root.appendChild(cycle)
    # Find out which stories fire
    state = scenario.state.expectation()
    for eventTitle,event in filter(lambda tup: tup[1]['fired'] < 0,stories.items()):
        substitution = {}
        # Story events cannot fire twice
        for condition in event['preconditions']:
            if condition['type'] == 'event':
                # Has the named event happened yet?
                if stories[condition['name']]['fired'] < 0:
                    break
            elif condition['type'] == 'state':
                # Does any entity of this class meet the condition?
                for entity in filter(lambda e: e.instanceof(condition['key']['entity']),
                                     scenario.members()):
                    key = StateKey({'entity': entity.name,'feature': condition['key']['feature']})
                    try:
                        match = condition['test'](state[key])
                    except KeyError:
                        sys.stderr.write('Unknown state feature: %s\n' % (key))
                        continue
                    if match:
                        if entity.name != condition['key']['entity']:
                            # Record which instance generated the match
                            if substitution.has_key(condition['key']['entity']):
                                assert substitution[condition['key']['entity']] == entity.name,\
                                       'Ambiguous match of event preconditions'
                            substitution[condition['key']['entity']] = entity.name
                        break
                else:
                    # Nope
                    break
            elif condition['type'] == 'action':
                # Does any player move match the desired condition?
                for subject,action in player.items():
                    if subject and scenario[subject].instanceof(condition['subject']):
                        if action['type'] == condition['verb'] and \
                           action['object'] == condition['object']:
                            # Match
                            if subject != condition['subject']:
                                # Record which instance generated the match
                                if substitution.has_key(condition['subject']):
                                    assert substitution[condition['subject']] == subject,\
                                           'Ambiguous match of event preconditions'
                                substitution[condition['subject']] = subject
                            break
                else:
                    # Nope
                    break
            elif condition['type'] == 'time':
                # Are we on the right day?
                target = condition['day']
                if condition.has_key('event'):
                    if stories[condition['event']]['fired'] < 0:
                        # Prerequisite event has not occurred
                        break
                    # Add delta to when prerequisite event occurred
                    target += stories[condition['event']]['fired']
                if day != target:
                    # Nope
                    break
            else:
                sys.stderr.write('Unhandled condition: %s\n' % (str(condition)))
        else:
            event['fired'] = day
#            sys.stderr.write('Story firing: %s\nEvent: %s\n' % (event['story'],eventTitle))
            for effect in event['effects']:
                node = doc.createElement('STORY_EFFECT')
                cycle.appendChild(node)
                if substitution.has_key(effect['subject']):
                    entities = [substitution[effect['subject']]]
                else:
                    entities = []
                    for entity in scenario.members():
                        if entity.name == effect['subject'] or \
                                entity.instanceof(effect['subject']):
                            if effect['colocation'] == 'ANYWHERE':
                                entities.append(entity.name)
                            else:
                                assert len(substitution) > 0
                                for colocator in substitution.values():
                                    if entity.getState('Location') == scenario[colocator].getState('Location'):
                                        entities.append(entity.name)
                                        break
                keys = map(lambda name: StateKey({'entity': name,
                                                  'feature': effect['feature']}),
                           entities)
                for key in keys:
                    assert state.has_key(key),'Unknown feature: %s' % (key)
                    child = doc.createElement('EFFECT')
                    node.appendChild(child)
                    child.setAttribute('SUBJECT',str(key['entity']))
                    child.setAttribute('FEATURE',str(key['feature']))
                    try:
                        child.setAttribute('DELTA',str(effect['delta']))
                    except KeyError:
                        try:
                            child.setAttribute('DELTA',str(effect['value']-state[key]))
                        except KeyError:
                            raise NotImplementedError,'Unable to determine story effect: %s' % (str(effect))
    
def parseLogs(scenario,directory='.'):
    first = True
    files = os.listdir(os.path.join(directory,'logs'))
    names = {'first': 1, 'second': 2, 'third': 3,
             'fourth': 4, 'fifth': 5}
    for name in files:
        if name[-4:] == '.log':
            output = open(os.path.join(directory,'processed/%s.csv' % (name[:-4])),'w')
            print >> output,'  # ,   Time, Type, Content'
            strategy = Replay(scenario,name,options.horizon,'logs',output,
                              options.turns)
            output.close()
            assert name[:len(strategy.subject)] == strategy.subject,'%s filename does not match subject name %s' % (name,strategy.subject)
            elements = name[len(strategy.subject):-4].split('.')
            assert len(elements[0]) == 0
            assert elements[1][-3:] == 'run',name
            number = names[elements[1][:-3]]
            empty = len(elements) == 3
            changes = sum(map(len,strategy.turns))
            try:
                duration = strategy.times[-1] - strategy.times[0]
                finalScore = strategy.LOEs[-1]
                LOEs = finalScore.keys()
                LOEs.sort()
                scores = ','.join(map(lambda loe: '%d' % (100.*finalScore[loe]),LOEs))
            except IndexError:
                duration = 'crash'
                LOEs = ['LOEs']
                scores = 'crash'
            if first:
#                print 'Subject,Run,Empty,LOE,Aggressive,Changes,Time,%s' % (','.join(LOEs))
                first = False
#            print '%s,%s,%s,%s,%s,%d,%s,%s' % (strategy.subject,number,empty,strategy.initialLOE,strategy.aggressive,changes,duration,scores)
            sys.stdout.flush()
#     table = {}
#     for agent in filter(lambda e: e.instanceof('Player'),scenario.members()):
#         for option in agent.actions.getOptions():
#             assert len(option) == 1
#             if scenario[option[0]['object']].getState('Legal Object').expectation() < 0.5:
#                 sys.stderr.write('%s\n' % (agent.makeActionKey(option)))
#                 continue
#             try:
#                 entry = table[option[0]['type']]
#             except KeyError:
#                 entry = {}
#                 table[option[0]['type']] = entry
#             try:
#                 subentry = entry[agent.classes[0]]
#             except KeyError:
#                 subentry = {}
#                 entry[agent.classes[0]] = subentry
#             subentry[scenario[option[0]['object']].classes[0]] = True
#     for verb in table.keys():
#         for actor,objects in table[verb].items():
#             for obj in objects.keys():
#                 print '%s,%s,%s' % (actor,verb,obj)
#     sys.stderr.write('Load %s\n' % (options.scenario))
#            sys.exit(-1)
    
if __name__ == '__main__':
    try:
        from numpy.core.numeric import array
        from numpy.matlib import std
    except ImportError:
        from Numeric import array
        std = None
    from optparse import OptionParser
    from xml.dom import minidom

    parser = OptionParser()
    # Optional argument that sets the location of the scenario
    parser.add_option('--scenario',action='store',type='string',
                      dest='scenario',default='AlHamra3.xml.bz2',
                      help='scenario file [default: %default]')
    # Optional argument that sets the location of the society
    parser.add_option('--society',action='store',type='string',
                      dest='society',default='alhamra.soc',
                      help='society file [default: %default]')
    # Optional argument that sets the number of iterations
    parser.add_option('-i','--iterations',action='store',
                      dest='iterations',type='int',default=1,
                      help='number of iterations to run [default: %default]')
    # Optional argument that sets the number of days per iteration
    parser.add_option('--horizon',action='store',
                      dest='horizon',type='int',default=15,
                      help='number of days to simulate per iteration [default: %default]')
    # Optional argument that sets the player strategy to simulate
    parser.add_option('--strategy',action='store',type='string',
                      dest='strategy',default=None,
                      help='Player strategy to test (e.g., "chb")')
    # Optional argument that specifies a game log to replay
    parser.add_option('--replay',action='store',type='string',
                      dest='replay',default=None,
                      help='Game log to replay')
    # Optional argument for parsing logs
    parser.add_option('--parse',action='store_true',
                      dest='parse',default=False,
                      help='Extract from log [default: %default]')
    # Optional argument for biasing toward correct strategies
    parser.add_option('-c','--correct',action='store_true',
                      dest='correct',default=False,
                      help='Use correct strategies [default: %default]')
    # Optional argument for extracting turns
    parser.add_option('--turns',action='store_true',
                      dest='turns',default=False,
                      help='Extract only committed turns from log [default: %default]')
    (options, args) = parser.parse_args()
    if options.parse:
        scenario = loadScenario(options.scenario)
        parseLogs(scenario)
        sys.exit(0)
    # Create UrbanSim proxy
    proxy = USim_Proxy()
    proxy.loadLOEs('LOE_Definitions.xml')
    if len(proxy.society) == 0:
        proxy.loadSociety(options.society,absolute=True)
    proxy.loadScenario(options.scenario,absolute=True)
    if options.correct:
        strategy = CorrectSamplingStrategy(proxy.scenario)
    else:
        strategy = SamplingStrategy(proxy.scenario)
    stories = parseStories('Stories.xml',options.scenario[:options.scenario.find('.')])
    history = {}
    player = {}
    # Print out headings
    line = ['Iteration','Feature']
    line += sum(map(lambda x: ['mean(%d)' % (x),'std(%d)' % (x)],
                    range(options.horizon+1)),[])
    line.append('mean(delta)')
    line.append('std(delta)')
#    print ','.join(line)
    for iteration in range(options.iterations):
        start = time.time()
        proxy.loadScenario(options.scenario,absolute=True)
        # if proxy.society is None:
        #     proxy.loadSociety(options.society)
        # sys.stderr.write('Load %s: %d s\n' % (options.scenario,int(time.time()-start)))
        # assert len(proxy.scenario) > 0,'Unable to load %s scenario' % (options.scenario)
        if strategy is None:
            if options.replay:
                strategy = Replay(proxy.scenario,options.replay,options.horizon)
            elif options.strategy:
                strategy = ClearHoldBuild(proxy.scenario,options.strategy,options.horizon)
            else:
                strategy = Strategy(proxy.scenario,options.horizon)
        else:
            strategy.reset()
        # Set up record of simulation history
        state = proxy.scenario.state.expectation()
        previous = proxy.evaluateLOEs()
        # for key,value in loes.items():
        #     try:
        #         history[proxy.LOEs[key]['name']][0].append(value)
        #     except KeyError:
        #         history[proxy.LOEs[key]['name']] = [[value]]
        for t in range(options.horizon):
            # sys.stderr.write('%d\n' % (t))
            # Generate LOE deltas player actions
            current = proxy.evaluateLOEs()
            state = {}
            for key,value in current.items():
                state[key] = value - previous[key]
                if state[key] > 0:
                    state[key] = 'increase'
                elif state[key] < 0:
                    state[key] = 'decrease'
                else:
                    state[key] = 'no change'
            # Generate player actions
            player.clear()
            player.update(strategy.execute(t,state))
            # Process day
            doc = proxy.generateTurn('commit',1,player=player)
            applyStories(stories,proxy.scenario,t,player,doc)
            # for actor,option in player.items():
            #     if actor:
            #         try:
            #             history[actor][t].append(option)
            #         except IndexError:
            #             history[actor].append([option])
            #         except KeyError:
            #             history[actor] = [[option]]
            proxy.onMessage(doc.toxml())
            state = proxy.scenario.state.expectation()
            previous = current
        current = proxy.evaluateLOEs()
        pairs = current.items()
        pairs.sort()
        print ','.join(map(str,[strategy.good,sum(current.values()),
                                int(time.time()-start)]+sum(map(list,pairs),[])))
        sys.stdout.flush()
    #         # Calculate scores
    #         proxy.evaluateLOEs(state,loes)
    #         for key,value in loes.items():
    #             try:
    #                 history[proxy.LOEs[key]['name']][t+1].append(value)
    #             except IndexError:
    #                 history[proxy.LOEs[key]['name']].append([value])
    #     # Calculate LOE deltas
    #     for loe in proxy.LOEs:
    #         delta = history[loe['name']][options.horizon][-1] - history[loe['name']][0][-1]
    #         try:
    #             history[loe['name']][options.horizon+1].append(delta)
    #         except IndexError:
    #             history[loe['name']].append([delta])
    # # Print out LOE history
    # for loe in proxy.LOEs:
    #     line = ['n/a',loe['name']]
    #     for t in range(options.horizon+2):
    #         values = history[loe['name']][t]
    #         line += ['%8.3f' % (sum(values)/float(options.iterations)),
    #                  '%8.3f' % (std(array(values)))]
    #     print ','.join(line)
    # Print player moves
    # players = map(lambda a: a.name,filter(lambda a: a.instanceof('Player'),
    #                                       proxy.scenario.members()))
    # players.sort()
    # for iteration in range(options.iterations):
    #     for actor in players:
    #         line = [str(iteration),actor]
    #         for t in range(options.horizon):
    #             option = history[actor][t][iteration]
    #             line.append('%s,%s' % (option['type'],option['object']))
    #         print ','.join(line)
