
"""
Modeling the decision-making of residents after an anthrax release. Based on:
Heather Rosoff, Richard John, William J. Burns, and Robert Siko (2012). 
"Structuring Uncertainty and Conflicting Objectives for Life or Death
Decisions Following an Urban Biological Catastrophe". 
Journal of Integrated Disaster Risk Management.
"""

import psychsim.probability
from psychsim.keys import *
from psychsim.pwl import *
from psychsim.action import powerset
from psychsim.reward import *
from psychsim.world import *
from psychsim.agent import Agent
#from psychsim.modeling import *

try:
    import psychsim.ui.diagram as diagram
    __gui__ = True
except ImportError:
    __gui__ = False

from argparse import ArgumentParser
import csv
import itertools
import logging
import os.path
import random
import sys

# Statements about a resident's beliefs
beliefs = {
    # TODO: what is their attitude toward living in city (how long have they been there, have they thought about moving?)
    'RiskCity': \
    {'statement': 'I believe the anthrax attack poses a serious risk to residents of the Seattle area.',
     'alt': ['RiskSeattle','Risk_to_Bay'],
     'agent': False},
    'RiskMe': \
    {'statement': 'I believe the anthrax attack  poses a serious risk to me.',
     'alt': ['Risk_to_me'],
     'agent': True},
    'Anxiety': \
    {'statement': 'The anthrax attack has created a great deal of anxiety for me. ',
     'agent': True},
    'MissPay1': \
    {'statement': 'If I miss ONE paycheck, I would not have enough money to buy food and pay bills. ',
     'alt': ['One_paycheck_problem'],
     'agent': True},
    'MissPayMany': \
    {'statement': 'If I miss SEVERAL paychecks, I would not have enough money to buy food and pay bills.',
     'alt': ['Several_paycheck_problem'],
     'agent': True},
    'GovtProvides': \
    {'statement': 'I believe the government will provide emergency response and health services I might need, for example antibiotics.',
     'alt': ['Believe_gov_supplies'],
     'agent': False},
    'FeelUnsafe': \
    {'statement': 'I feel unsafe because of the increasing number of deaths and new anthrax infections.',
     'agent': True},
    'Traffic': \
    {'implies': 'RiskTrafficLeave',
     'statement': 'Leaving the area risks sitting in traffic for hours and running out of car fuel.',
     'agent': False},
    'Decontaminated': \
    {'implies': 'LiveHZNeedDecon',
     'statement': 'My home and the homes in my neighborhood have been decontaminated.',
     'agent': True},
    'BusinessesNotReopened': \
    {'implies': 'BOReturnOthersNot',
     'statement': 'Hundreds of businesses have yet to reopen.',
     'agent': False},
    'ZipDistance4': \
    {'statement': 'What is the zip code of your current home address?',
     'global': True,
     'agent': True},
    'ZIPWithWork4': \
    {'statement': 'What is the zip code of your place of employment?',
     'global': True,
     'agent': True},
    'JobFulltime': \
    {'statement': 'What is your current employment status (paid opportunities only)?',
     'alt': ['Work_Fulltime'],
     'domain': 'binary',
     'agent': True,
     'global': True},
    }
response2prob = [0., .1, .25, .5, .75, .9, 1.]

def prob2response(prob):
    """
    Converts a probability to a 1-5 Likert-scale kind of thing
    @rtype: int
    """
    for response in range(1,5):
        if prob < (response2prob[response]+response2prob[response+1])/2.:
            return response
    else:
        return 5

# TODO: How does changing the value from False to True impact your decision to stay/leave?
importance = {
    'RiskExposure':
        {'statement': 'Risk of anthrax exposure or infection.',
         'belief': 'RiskMe',
         'agent': False},
    'AvailableHealthCare':
        {'statement': 'Availability of health care services including antibiotics.',
         'agent': False},
    'NumExposed':
        {'statement': 'The increasing number of deaths and new anthrax infections.',
         'agent': False},
    'AvailableGoods':
        {'statement': 'Availability of goods (e.g.  food, water, and other essentials).',
         'agent': False},
    'AvailableJob':
        {'statement': 'Availability of employment in the Seattle area.',
         'agent': False},
    'FinanceStable':
        {'statement': 'Being financially stable (e.g. having savings to cover your living expenses).',
         'belief': 'FinanceStable',
         'agent': True},
    'WillingAntibiotic':
        {'statement': 'My willingness to take the antibiotics for 60 days.',
         'agent': True},
    }
for belief,entry in importance.items():
    if not 'belief' in  entry:
        beliefs[belief] = entry

        
# Statements about a resident's hypothetical behaviors
# TODO: location in hot zone vs not
# TODO: where do you work
behaviors = {
    'ChangeRoutine': \
    {'statement': 'I would change my daily routine to avoid exposure to anthrax.',
     'alt': ['Change_routine'],
     'phase': 'how','location': 'Seattle',
 },
    'ContWorkSch': \
    {'statement': 'I would continue going to work or school if open.',
     'alt': ['Attend_work_school'],
     'phase': 'how','location': 'Seattle',
 },
    'OutdoorPrecaution': \
    {'statement': 'I would take necessary precautions to avoid anthrax exposure when outside.',
     'alt': ['Take_protective_measures'],
     'phase': 'how','location': 'Seattle',
 },
    'TakeAntiBiotic': \
    {'statement': 'I would obtain the antibiotic and take it as directed.',
     'alt': ['Take_antibiotic'],
     'phase': 'how','location': 'Seattle',
 },
#    'KidsSchool': \
#        {'statement': 'I would continue to take my children to school if open.',
#         'phase': 'how','location': 'Seattle'},
    'Leave': \
    # TODO: Can they leave?
    {'statement': 'I would LEAVE the Seattle area for at least a short time after watching the earlier news video.',
     'alt': ['LeaveSeattle'],
     'phase': 'where','location': 'Seattle',
 },
    'StaySeattle': \
    {'phase': 'where','location': 'Seattle',
 },
    'ReturnSeattle': \
    {'phase': 'where','location': 'beyond',
 },
    # TODO: what if you do neither, e.g., just take a vacation
    'TempWork': \
    {'statement': 'I would look for temporary work.',
     'alt': ['Leave_LookforWork'],
     'phase': 'how','location': 'beyond',
 },
    # TODO: maybe your work is already out of Seattle
    'PermanentMove': \
    {'statement': 'I would plan to move out of the Seattle area (e.g. look for permanent employment, school, housing).',
     'alt': ['Leave_LookforWork'],
     'phase': 'how','location': 'beyond',
 },
}

objectives = {
    'PersonalSafety': \
    {'objective': 'Personal safety (from crime)',
    },
    'FinanceStable': \
    {'objective': 'Financial stability (being financially stable/secure, general affordability of necessities)',
     'alt': ['FinancialStability'],
    },
    
    'PersonalSurvival': \
    {'objective': 'Health safety and personal anthrax survival (effectiveness and access to antibiotic)',
     'alt': ['HealthSafety'],
    },
    'FriendSurvival': \
    {'objective': 'Family or friend anthrax survival',
     'alt': ['FamilyFriend'],
    },
#    'Other': \
#    {'objective': 'Other',
#    },
}

baseEffects = {
    # Effects on beliefs
    'RiskMe': {
        'ChangeRoutine': {True: -1, False: -1},
        'ContWorkSch': {True: 1, False: 1},
        'KidsSchool': {True: 1, False: 1},
        'OutdoorPrecaution': {True: -1, False: -1},
        'TakeAntiBiotic': {True: -1, False: -1},
        # TODO: does leaving expose you to anthrax?
        'Leave': {True: -1, False: -1},
        'PermanentMove': {True: -1, False: -1},
        },
    'JobFulltime': {
        'ChangeRoutine': {True: 0, False: 0},
        'ContWorkSch': {True: 0, False: 0},
        'KidsSchool': {True: 0, False: 0},
        'OutdoorPrecaution': {True: 0, False: 0},
        'TakeAntiBiotic': {True: 0, False: 0},
        'Leave': {True: -1, False: -1},
        'PermanentMove': {True: 0, False: 0},
        },
    # Effects on objectives
    'PersonalSurvival': {
        'RiskMe': {True: 1, False: 5},
        'GovtProvides': {True: 4, False: 1},
        # NOTE: Removed because redundant with respect to behavior TakeAntibiotic
#        'WillingAntibiotic': {True: 4, False: 1},
        'AvailableHealthCare': {True: 5, False: 1},
#        'NumExposed': {True: 4, False: 1},
        },
    'PersonalSafety': {
        'Leave': {True: 3, False: 5},
        'AvailableGoods': {True: 4, False: 2},
        'GovtProvides': {True: 4, False: 2},
        },
    'FinanceStable': {
        'MissPay1': {True: 1, False: 4},
        'MissPayMany': {True: 1, False: 5},
        'ContWorkSch': {True: 5, False: 1},
        'JobFulltime': {True: 5, False: 1},
        },
    'FriendSurvival': {
#        'RiskCity': {True: 3, False: 3},
#        'GovtProvides': {True: 5, False: 1},
#        'WillingAntibiotic': {True: 4, False: 1},
#        'AvailableHealthCare': {True: 5, False: 1},
#        'NumExposed': {True: 4, False: 1},
        },
#    'Other': {
#        },
    }
                    
def noisyOrTree(tree,value):
    if isinstance(tree,dict):
        return {'if': tree['if'],
                True: noisyOrTree(tree[True],value),
                False: noisyOrTree(tree[False],value)}
    else:
        return tree*(1.-value)

def leaf2matrix(tree,key):
    if isinstance(tree,dict):
        return {'if': tree['if'],
                True: leaf2matrix(tree[True],key),
                False: leaf2matrix(tree[False],key)}
    else:
        prob = 1.-tree
        return {'distribution': [(setTrueMatrix(key),prob),(setFalseMatrix(key),1.-prob)]}

def buildWorld():
    world = World()
    if __gui__:
        world.diagram = diagram.Diagram()
        world.diagram.setColor(None,'ivory')

    resident = Agent('resident')
    if __gui__:
        world.diagram.setColor(resident.name,'palegreen')
    world.addAgent(resident)
    family = Agent('family')
    world.diagram.setColor(family.name,'mediumseagreen')
    world.addAgent(family)
    gov = Agent('government')
    if __gui__:
        world.diagram.setColor(gov.name,'cornflowerblue')
    world.addAgent(gov)

    world.setOrder([resident.name])

    # Keep track of orthogonal dimensions of decision-making
    phase = world.defineState(None,'phase',list,['where','how'],
                              description='What is being decided at this stage of the simulation')
    world.setState(None,'phase','where')

    # Where is the resident now?
    location = world.defineState(resident.name,'location',list,['Seattle','beyond'])
    resident.setState('location','Seattle')

    # Decisions
    for name,entry in behaviors.items():
        entry['action'] = Action({'subject': resident.name,'verb': name})

    # Generate possible combinations of actions
    options = {}
    
    # Lifestyle choices in Seattle
    howStayActions = [name for name in behaviors.keys() if behaviors[name]['phase'] == 'how' and \
                      behaviors[name]['location'] == 'Seattle']
    for joint in powerset(howStayActions):
        action = ActionSet([behaviors[name]['action'] for name in joint])
        label = ' '.join(joint)
        options[label] = resident.addAction(action)
        # Only legal during "how" phase and if living in Seattle
        resident.setLegal(options[label],makeTree({'if': equalRow('phase','how'),
                                                   True: {'if': equalRow(location,'Seattle'),
                                                          True: True, False: False},
                                                   False: False}))
    # Lifestyle choices outside Seattle
    howLeaveActions = [name for name in behaviors.keys() if behaviors[name]['phase'] == 'how' and \
                       behaviors[name]['location'] == 'beyond']
    for joint in howLeaveActions:
        options[joint] = resident.addAction(behaviors[joint]['action'])
        # Only legal during "how" phase and if *not* living in Seattle
        resident.setLegal(options[joint],makeTree({'if': equalRow('phase','how'),
                                                   True: {'if': equalRow(location,'beyond'),
                                                          True: True, False: False},
                                                   False: False}))
    # Choices of where to live
    whereActions = [name for name in behaviors.keys() if behaviors[name]['phase'] == 'where']
    for joint in whereActions:
        options[joint] = resident.addAction(behaviors[joint]['action'])
        # Only legal during "where" phase
        tree = makeTree({'if': equalRow('phase','where'),
                         True: {'if': equalRow(location,behaviors[joint]['location']),
                                True: True, False: False},
                         False: False})
        resident.setLegal(options[joint],tree)

    # Objectives
    # ranks = [objective['rank'] for objective in objectives.values()]
    # ceiling = max(ranks) + 1
    # total = float(sum(ranks))
    for name,objective in objectives.items():
        objective['key'] = world.defineState(resident.name,name,bool)
    #     world.setFeature(objective['key'],True)
    #     resident.setReward(maximizeFeature(objective['key']),float(ceiling-objective['rank'])/total)

    # Beliefs
    for name,belief in beliefs.items():
        if belief['agent']:
            agent = resident.name
        else:
            agent = None
        belief['key'] = world.defineState(agent,name,bool,
                                          description=belief['statement'])

    # Movement dynamics
    world.setDynamics(location,behaviors['Leave']['action'],
                      makeTree(setToConstantMatrix(location,'beyond')))
    world.setDynamics(location,behaviors['ReturnSeattle']['action'],
                      makeTree(setToConstantMatrix(location,'Seattle')))

    # Phase dynamics
    world.setDynamics('phase',True,makeTree({'if': equalRow('phase','where'),
                                             True: setToConstantMatrix('phase','how'),
                                             False: setToConstantMatrix('phase','where')}))

    # Decision-making parameters
    resident.setAttribute('horizon',2)
    resident.setAttribute('selection','distribution')
    resident.setAttribute('rationality',10.)
    return world

def applyEffects(world,effects,logger=logging.getLogger()):
    logger = logger.getChild('applyEffects')
    resident = world.agents['resident']
    howStayActions = [name for name in behaviors.keys() if behaviors[name]['phase'] == 'how' and \
                      behaviors[name]['location'] == 'Seattle']
    # Dynamics of beliefs
    for name,entry in beliefs.items():
        if name in effects:
            hi = len([effects[name][verb][True] for verb in effects[name].keys() if effects[name][verb][True] > 0])
            lo = -len([effects[name][verb][True] for verb in effects[name].keys() if effects[name][verb][True] < 0])
            span = float(hi - lo)
            for choices in powerset(howStayActions):
                action = ActionSet([behaviors[verb]['action'] for verb in choices])
                # Count the overall +/- effects across the action choices
                count = sum([effects[name][verb][True] for verb in choices])
                # Convert the count into a 1-5 Likert scale
                response = 1+int(5.*float(count-lo)/span)
                # Convert scale into outcome distribution
                prob = response2prob[response]
                tree = makeTree({'distribution': [(setTrueMatrix(entry['key']),prob),
                                                  (setFalseMatrix(entry['key']),1.-prob)]})
                world.setDynamics(entry['key'],action,tree)

    # Dynamics of objectives
    for name,objective in objectives.items():
        trees = {True: 1.}
        for feature,values in effects[name].items():
            if feature in beliefs:
                for actions,tree in trees.items():
                    trees[actions] = {'if': trueRow(makeFuture(beliefs[feature]['key'])),
                                      True: noisyOrTree(tree,response2prob[values[True]]),
                                      False: noisyOrTree(tree,response2prob[values[False]])}
            elif feature == 'location':
                # Special case for handling "location", which is not a T/F variable
                for actions,tree in trees.items():
                    trees[actions] = {'if': equalRow(makeFuture(beliefs[feature]['key']),'Seattle'),
                                      True: noisyOrTree(tree,response2prob[values[True]]),
                                      False: noisyOrTree(tree,response2prob[values[False]])}
            else:
                for actions,tree in trees.items():
                    trees[actions] = noisyOrTree(trees[actions],response2prob[values[False]])
                trees[feature] = noisyOrTree(trees[True],response2prob[values[True]])
#                logger.warning('Ignoring action %s\'s effect %s. Sorry.' % (feature,name))
        for action,tree in trees.items():
            tree = leaf2matrix(tree,objective['key'])
            if name == 'PersonalSurvival':
                tree = {'if': equalRow(stateKey(resident.name,'location',True),'Seattle'),
                                 True: tree, False: setTrueMatrix(objective['key'])}
            if isinstance(action,str):
                for actionObj in resident.actions:
                    if len(actionObj) == 1 and actionObj['verb'] == action:
                        action = list(actionObj)[0]
                        break
            if not isinstance(action,str):
                world.setDynamics(objective['key'],action,makeTree(tree))
            else:
                print action
                print resident.actions
                
def readVariations(fname):
    variations = []
    # Read in modeling variations from file
    with open(fname) as csvfile:
        reader = csv.DictReader(row for row in csvfile if not row.startswith('#'))
        index = 0
        for link in reader:
            # Read variables involved and possible link values
            link['from'] = link['from'].split(';')
            link['domain'] = [None if val == 'None' else map(int,val.split(':')) for val in link['domain'].split(';')]
            link['range'] = int(link['range'])
            link['index'] = index
            variations.append(link)
            # Derive downstream effects
            link['effects'] = {}
            link['effects'][link['to']] = link['domain'][:]
            index += 1
    return variations
    
def readInputData(fname):
    inData = {}
    # Read in raw data from file
    ids = set()
    with open(fname) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if not 'V1' in row:
                row['V1'] = '%s%s' % (row['V6'],row['V8'].replace(' ',''))
            assert not row['V1'] in ids
            ids.add(row['V1'])
            inData[row['V1']] = row
    return inData

def writeRawData(records,fname):
    fields = sorted([key for key in records[0].keys() if not key[-2:] in ['_B','_C','_D','_E']])
    with open('%s.csv' % (fname),'w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,extrasaction='ignore')
        writer.writeheader()
        for record in records:
            writer.writerow(record)

def writeInput(records,fields,fname):
    with open('%s' % (fname),'w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,extrasaction='ignore')
        writer.writeheader()
        for record in records:
            writer.writerow(record)

def evaluateImpact(record,variations,world,logger=logging.getLogger()):
    """Compute the impact of the different variations on the leave/stay decision
    """
    logger = logger.getChild('evaluateImpact')
    # Determine baseline decision
    model = links2model([0 for i in range(len(variations))],variations)
    decision = generateDecision(world,record,model,logger)
    null = record['P(Leave)'][model]
    logger.info('Null model(Leave,%s) = %5.2f' % (record['V1'],null))
    impact = []
    for variation in variations:
        # Turn on each variation in turn
        logger.info('Applying %s for %s' % (variation['code'],record['V1']))
        links = [0 for i in range(len(variations))]
        for i in range(1,variation['range']):
            deltas = [0.]
            links[variation['index']] = i
            model = links2model(links,variations)
            logger.info(model)
            try:
                record['P(Leave)'][model]
            except KeyError:
                applyModel(world,model,variations)
                generateDecision(world,record,model,logger)
            delta = record['P(Leave)'][model] - null
            logger.info('%s:%5.2f' % (record['V1'],delta))
            deltas.append(delta)
        impact.append(deltas)
    return impact

def correctModels(records,models,variations,world=None,logger=logging.getLogger()):
    logger = logger.getChild('correctModels')
    if world is None:
        world = buildWorld()
    histogram = [[] for real in range(5)]
    for record in records.values():
        if record['Leave']:
            histogram[int(record['Leave'])-1].append(record)
    for real in range(5):
        logger.info('Correct Response: %d (#=%d)' % (real+1,len(histogram[real])))
        for record in histogram[real]:
            sublogger = logger.getChild(record['V1'])
            base = int(record['predictions'][models[0]])
            sublogger.debug('Base prediction: %s' % (base))
            delta = real-base+1
            sublogger.debug('Delta = %d' % (delta))
            impact = evaluateImpact(record,variations,world,sublogger)
            links = []
            for i in range(len(variations)):
                best = None
                for j in range(len(impact[i])):
                    if delta > 0:
                        # Need to want to leave more
                        if best is None or impact[i][j] > best[1]:
                            best = j,impact[i][j]
                    else:
                        # Need to want to stay more
                        if best is None or impact[i][j] < best[1]:
                            best = j,impact[i][j]
                logger.debug('Best choice for %s: %d' % (variations[i]['code'],best[0]))
                links.append(best[0])
            model = links2model(links,variations)
            sublogger.info('Hypothesis: %s' % (model))
            applyModel(world,model,variations)
            decision = generateDecision(world,record,model,sublogger)

def processData(inData,data={},createNew=False,logger=logging.getLogger()):
    """
    Takes in raw data and extracts the relevant fields
    """
    logger = logger.getChild('processData')
    outData = []
    # Process each record
    first = True
    for row in inData:
        logger.debug('Processing record: %s' % (row['V1']))
        try:
            record = data[row['V1']]
            record['complete'] = True
        except KeyError:
            if createNew:
                record = {'V1': row['V1'],
                          'complete': True}
                data[record['V1']] = record
            else:
                continue
        outData.append(record)
        if first:
            keys = []
        # Process beliefs
        for name,belief in beliefs.items():
            if name in importance:
                pass
            elif not name in record:
                if 'global' in belief and belief['global']:
                    key = name
                else:
                    key = '%s_A' % (name)
                if not key in row and 'alt' in belief:
                    for key in belief['alt']:
                        if key in row:
                            break
                        elif '%s_A' % (key) in row:
                            key = '%s_A' % (key)
                            break
                    else:
                        key = None
                try:
                    record[name] = row[key]
                    if name == 'JobFulltime':
                        if not row[key] in ['0','1']:
                            row[key] = '0'
                    if first:
                        keys.append(name)
                except KeyError:
                    logger.warning('Missing field %s from record %s' % \
                                    (name,row['V1']))
        for name,behavior in behaviors.items():
            if not name in record:
                try:
                    record[name] = row['%s_A' % (name)]
                except KeyError:
                    try:
                        record[name] = row['%s_1' % (name)]
                    except KeyError:
                        if 'alt' in behavior:
                            for key in behavior['alt']:
                                if key in row:
                                    record[name] = row[key]
                                    break
                                else:
                                    try:
                                        record[name] = row['%s_1' % (key)]
                                        break
                                    except KeyError:
                                        try:
                                            record[name] = row['%s_A' % (key)]
                                            break
                                        except KeyError:
                                            pass
                            else:
                                logger.warning('Missing field %s from record %s' % \
                                                 (name,row['V1']))
                                record[name] = ''
                        else:
                            logger.warning('Missing field %s from record %s' % \
                                             (name,row['V1']))
                            record[name] = ''
        for name,objective in objectives.items():
            if not name in record:
                if first:
                    keys.append(name)
                try:
                    record[name] = row['PO%s_A' % (name)]
                except KeyError:
                    if 'alt' in objective:
                        for key in objective['alt']:
                            if '%s_1' % (key) in row:
                                record[name] = row['%s_1' % (key)]
                                break
                        else:
                            print [k for k in row.keys() if len(k) < 16]
                            raise KeyError('Missing objective %s and alternatives %s for %s' % \
                                           (name,', '.join(objective['alt']),record['V1']))
                    else:
                        record[name] = row['%s_1' % (name)]
                record[name] = record[name][:1]
        if not 'Leave' in record:
            try:
                record['Leave'] = row['Leave_1']
            except KeyError:
                record['Leave'] = row['LeaveSeattle_A']
        if not record['Leave']:
            record['complete'] = False
        else:
            logger.info('Complete record: %s' % (record['V1']))
        first = False
    return outData

def applyModel(world,model,variations):
    variation = model2links(model,variations)
    world.agents['resident'].setAttribute('rationality',10.)
    effects = copy.deepcopy(baseEffects)
    for linkIndex in range(len(variations)):
        link = variations[linkIndex]
        value = link['domain'][variation[link['code']]]
        if link['code'] == 'Rationality':
            world.agents['resident'].setAttribute('rationality',float(value[0]))
        elif not value is None:
            if isinstance(link['from'],str):
                link['from'] = [link['from']]
            for orig in link['from']:
                try:
                    effects[link['to']][orig][True] = value[0]
                    effects[link['to']][orig][False] = value[1]
                except KeyError:
                    effects[link['to']][orig] = {True: value[0], False: value[1]}
    # Build the model
    applyEffects(world,effects)
#        world.save('anthrax%s.psy' % (model))

def generateDecision(world,record,model,logger=logging.getLogger()):
    logger = logger.getChild('applyEffects')
    resident = world.agents['resident']
    behavior = {}
    # Process beliefs
    for name,belief in beliefs.items():
        if name in importance:
            # Importance, not belief
            world.setFeature(belief['key'],True)
        else:
            try:
                distribution = {True: response2prob[int(record[name])]}
            except KeyError:
                distribution = {True: response2prob[3]}
            except ValueError:
                logger.debug('Empty field %s from record %s' % \
                             (name,record['V1']))
                distribution = {True: response2prob[3]}
            distribution[False] = 1. - distribution[True]
            world.setFeature(belief['key'],psychsim.probability.Distribution(distribution))
    for name,objective in objectives.items():
        if record[name]:
            resident.setReward(maximizeFeature(objective['key']),
                               6.-float(record[name]))
        # TODO: What value to initialize to? Maybe it doesn't matter because it's relative
        world.setFeature(objective['key'],response2prob[3])
    behavior['whereDecision'] = resident.newDecide()
    behavior['whereER'] = {}
    for where,whereProj in behavior['whereDecision'].V.items():
        behavior['whereER'][where] = whereProj.ER(resident)
        whereNode = whereProj.nodes[1][0]
        behavior['howDecision'] = whereNode.decisions[resident.name]
        behavior['howER'] = {}
        full = [how for how in behavior['howDecision'].V.keys() \
                if len(str(how)) == max(map(len,(map(str,behavior['howDecision'].V.keys()))))]
        for action in full[0]:
            if not action['verb'] in record or len(record[action['verb']]) == 0:
                behavior['known'] = False
                break
        else:
            behavior['known'] = True
        for how,howProj in behavior['howDecision'].V.items():
            howNode = howProj.nodes[0][0]
            effect = howNode.effects[how] 
            R = resident.getAttribute('R')
            behavior['howER'][how] = 0.
            for Rtree in R.keys():
                for key in Rtree.getKeysIn():
                    try:
                        tree = effect.dynamics[key][0]
                    except IndexError:
                        continue
                    result,substates = effect.after.applyTree(tree)
                    for matrix in result.domain():
                        behavior['howER'][how] += R[Rtree]*matrix[key][CONSTANT]*result[matrix]
        if behavior['known']:
            behavior['howBehavior'] = psychsim.probability.Distribution()
            behavior['howResponse'] = {}
            for how,howProj in behavior['howDecision'].V.items():
                behavior['howBehavior'][how] = 1.
                for action in full[0]:
                    try:
                        response = int(record[action['verb']])
                        behavior['howResponse'][action['verb']] = response
                    except ValueError:
                        logger.warning('Erroneous response to %s for %s' % (action['verb'],record['V1']))
                        response = 3
                    if action in how:
                        behavior['howBehavior'][how] *= response2prob[response]
                    else:
                        behavior['howBehavior'][how] *= 1.-response2prob[response]
            behavior['howBehavior'].normalize()
        else:
            behavior['howBehavior'] = psychsim.probability.Distribution(behavior['howER'],resident.getAttribute('rationality'))
        for how in behavior['howBehavior'].domain():
            behavior['whereER'][where] += behavior['howBehavior'][how]*behavior['howER'][how]
    behavior['whereBehavior'] = psychsim.probability.Distribution(behavior['whereER'],resident.getAttribute('rationality'))
    logger.info('Predicted Where:\n%s' % (str(behavior['whereBehavior'])))
    logger.debug('Predicted How:\n%s' % (str(behavior['howBehavior'])))
    logger.debug('Real Where: %s' % (record['Leave']))
    record['P(Leave)'][model] = behavior['whereBehavior']['resident-Leave']
    record['predictions'][model] = '%d' % (prob2response(behavior['whereBehavior']['resident-Leave']))
    logger.info('Prediction: %s' % (record['predictions'][model]))
    try:
        realDecision = response2prob[int(record['Leave'])]
    except ValueError:
        assert record['Leave'] == ''
        logger.error('Empty leaving decision: %s' % (record['V1']))
    return behavior
    
def generatePredictions(data,models,variations,world=None,logger=logging.getLogger()):
    logger = logger.getChild('generatePredictions')
    if world is None:
        world = buildWorld()
    change = True
    while change:
        change = False
        for record in data:
            candidates = [m for m in models if not record['predictions'].has_key(m)]
            logger.debug('Record %s has %d untried models' % (record['V1'],len(candidates)))
            if candidates:
                change = True
                candidates.sort(key=lambda m: sum(model2links(m,variations).values()))
                model = candidates[0]
                logger.info('Record %s, Model %s' % (record['V1'],model))
                applyModel(world,model,variations)
                generateDecision(world,record,model)
    return data

def model2links(model,varations):
    """
    @return: a table of link indices for the given model name
    @rtype: strS{->}int
    """
    table = {}
    index = 0
    for link in variations:
        table[link['code']] = int(model[index+len(link['code'])])
        index += len(link['code'])+1
    return table

def links2model(links,variations):
    return ''.join(['%s%s' % (variations[i]['code'],links[i]) for i in range(len(variations))])

def linkDiff(var1,var2):
    """
    @return: a list of links on which two models differ
    @rtype: str[]
    @type var1,var2: strS{->}int
    """
    diff = set()
    for key,value in var1.items():
        if value != var2[key]:
            diff.add(key)
    return diff
    
def reduceModels(data,variations,models):
    """
    Finds equivalence classes of models
    """
    varTable = {}
    linkTable = {}
    coverage = {}
    never = {link['code'] for link in variations}
    for model in models:
        varTable[model] = model2links(model,variations)
        linkTable[model] = [varTable[model][link['code']] for link in variations]
        coverage[model] = {record['V1'] for record in data.values() if model in record and record[model] == record['Leave']}
    # Any models have identical coverage? 
    examined = set()
    mapping = {}
    for i in range(len(models)-1):
        if models[i] in examined:
            continue
        equivalence = []
        equivalence.append(models[i])
        examined.add(models[i])
        for j in range(i+1,len(models)):
            if models[j] in examined:
                continue
            elif coverage[models[i]] == coverage[models[j]]:
                equivalence.append(models[j])
                examined.add(models[j])
        if len(equivalence) > 1:
            # Multiple models have identical coverage
            irrelevant = set()
            for linkIndex in range(len(variations)):
                link = variations[linkIndex]
                # Is this link unnecessary within this class?
                dependency = False
                history = set()
                for model in equivalence:
                    if dependency: break
                    links = linkTable[model][:]
                    for value in range(link['range']):
                        links[linkIndex] = value
                        current = links2model(links,variations)
                        history.add(current)
                        if not current in equivalence:
                            # Changing this link value violates the equivalence class
                            dependency = True
                            never = never - {link['code']}
                            break
                if not dependency:
                    irrelevant.add(link['code'])
            for model in equivalence:
                links = linkTable[model]
                for linkIndex in range(len(variations)):
                    if variations[linkIndex]['code'] in irrelevant:
                        links[linkIndex] = '*'
                current = links2model(links,variations)
                if current in mapping:
                    mapping[current].add(model)
                else:
                    mapping[current] = {model}
        else:
            mapping[models[i]] = {models[i]}
    for link in variations:
        link['never'] = link['code'] in never
    return mapping

def node2models(node,models):
    """
    Converts an integer index into an element from the powerset of possible models
    @param node: the integer representing the binary assignment desired
    @type node: int
    @param models: the set of possible models
    @type models: str[]
    @return: the set of selected models
    @rtype: str{}
    """
    selected = set()
    for bit in range(len(models)):
        if node % 2:
            selected.add(models[bit])
        node /= 2
    return selected

def examineNode(node,models,coverage):
    current = node2models(node,models)
    blanket = reduce(set.union,[coverage[model] for model in current],set())
    return {'models': current,
            'size': len(current),
            'blanket': blanket,
            'coverage': len(blanket)}
    
def searchCover(records,models,limit=None):
    """
    Search for covering set of models of the given data
    @param limit: Maximum number of model coverings to consider (default is no limit)
    @type limit: int
    @param selection: Method for using to choose next node to explore (default is "first")
    @type selection: str
    """
    # Preprocess models to determine set of records each singleton model covers covers
    coverage = {}
    stats = {0: examineNode(0,models,coverage)}
    best = {'coverage': 0,'size': None}
    envelope = []
    for index in range(len(models)):
        model = models[index]
        coverage[model] = {record['V1'] for record in records if model in record['__candidates__']}
        node = pow(2,index)
        stats[node] = examineNode(node,models,coverage)
        envelope.append(node)
        # Figure out baseline based on singleton models
        if stats[node]['coverage'] > best['coverage']:
            best['coverage'] = stats[node]['coverage']
            best['size'] = stats[node]['size']
        elif stats[node]['coverage'] == best['coverage'] and stats[node]['size'] < best['size']:
            best['size'] = stats[node]['size']
    envelope.sort(lambda node1,node2: cmp((-stats[node1]['coverage'],stats[node1]['size']),
                                          (-stats[node2]['coverage'],stats[node2]['size'])))
    # Loop until we can loop no more
    while envelope and (limit is None or len(stats) < limit):
        # Iterate through pairs of subsets
        change = False
        i = 0
        while i < len(envelope)-1:
            if change: break
            node1 = envelope[i]
            if best['coverage'] == len(records) and stats[node1]['size'] >= best['size']:
                # No point in growing this guy
                del envelope[i]
            else:
                j = i+1
                while j < len(envelope):
                    node2 = envelope[j]
                    if best['coverage'] == len(records) and stats[node2]['size'] >= best['size']:
                        # No point in growing this guy
                        del envelope[j]
                    else:
                        node3 = node1 + node2
                        if not node3 in stats:
                            entry = examineNode(node3,models,coverage)
                            stats[node3] = entry
                            if len(stats) % 10000 == 0: print('\t%e' % (len(stats)))
                            if node1 & node2 == 0:
                                # No overlap
                                if best['coverage'] < len(records) or entry['size'] < best['size'] or \
                                   (entry['size'] == best['size'] and \
                                    entry['coverage'] == best['coverage']):
                                    # Is it a new best?
                                    if entry['coverage'] > best['coverage']:
                                        # Clear winner
                                        best['coverage'] = entry['coverage']
                                        best['size']  = entry['size']
                                        print(best['coverage'],best['size'])
                                    elif entry['coverage'] == best['coverage'] and entry['size'] < best['size']:
                                        best['size'] = entry['size']
                                        print('---',best['size'])
                                    # Insert into sorted envelope
                                    for k in range(len(envelope)):
                                        if stats[envelope[k]]['coverage'] < entry['coverage']:
                                            envelope.insert(k,node3)
                                            break
                                    else:
                                        envelope.append(node3)
                                    # Exit loop
                                    change = True
                                    break
                        j += 1
                i += 1
    # Find best covering set
    possibles = [node for node in stats.keys() if stats[node]['coverage'] == best['coverage'] and \
                 stats[node]['size'] == best['size']]
    node = random.choice(possibles)
    choices = [(model,len(coverage[model])) for model in stats[node]['models']]
    print(stats[node]['coverage'],stats[node]['size'])
    print(len(stats),len(history))
    return choices
        
           
def greedyCover(remaining,scoring='match',logger=logging.getLogger()):
    logger = logger.getChild('greedyCover')
    candidates = [record['__candidates__'] for record in remaining]
    models = set.union(*candidates)
    logger.info('%d relevant models' % (len(models)))
    choices = []
    while len(remaining) > 0:
        logger.info('%d records remaining to match' % (len(remaining)))
        count = {}
        pairs = []
        for model in models:
            count[model] = 0
            for record in remaining:
                if scoring == 'match':
                    if model in record['__candidates__']:
                        count[model] += 1
                elif scoring == 'difference':
                    if record[model] and record['Leave']:
                        count[model] += float(4-abs(int(record[model])-int(record['Leave'])))/4.
            count[model] = int(round(count[model]))
            pairs.append((count[model],model))
        for n,model in sorted(pairs,reverse=True):
            if n > 0:
                logger.info('%s: %3d/%3d' % (model,n,len(remaining)))
            else:
                logger.debug('%s: %3d/%3d' % (model,n,len(remaining)))
            for real in range(5):
                logger.debug('%d: %s' % (real+1,[len([record for record in remaining if record['Leave'] == str(real+1) and model in record and record[model] == str(pred+1)]) for pred in range(5)]))
        high = max(count.values())
        candidates = [model for model in models if count[model] == high]
        new = random.choice(candidates)
        choices.append((new,count[new]))
        models.remove(new)
        index = 0
        while index < len(remaining):
            if new in remaining[index]['__candidates__']:
                del remaining[index]
            else:
                index += 1
    return choices

def findImpossibles(data,models,logger=logging.getLogger()):
    """
    Partition data into records with a potential match within the model set and records without any possible match
    @return: the list of matchable records, the list of unmatchable records
    @rtype: [],[]
    """
    logger = logger.getChild('findImpossibles')
    matchable = []
    unmatchable = []
    for record in data.values():
        try:
            record['__candidates__'] = {model for model in record['predictions'] if record['predictions'][model] == record['Leave']}
        except KeyError:
            continue
        if len(record['__candidates__']) == 0:
            logger.info('Unmatched: %s' % (record['V1']))
            unmatchable.append(record)
        else:
            matchable.append(record)
    return matchable,unmatchable

def readOldPredictions(filename,variations,logger=logging.getLogger()):
    logger = logger.getChild('readOldPredictions')
    data = {}
    with open(filename,'r') as csvfile:
        first = True
        reader = csv.DictReader(csvfile)
        for record in reader:
            # Make sure to include models we've processed before,
            # even if we're not including them now
            predictions = [(k,record[k]) for k in record.keys() if k[:len(variations[0]['code'])] == variations[0]['code']]
            matches = [prediction[0] for prediction in predictions if prediction[1] == record['Leave']]
            logger.info('Reading record: %s' % (record['V1']))
            for field in [k for k in record.keys() if not k in fields]:
                # Check whether it's an alternate name for a known field
                for key,value in itertools.chain(beliefs.items(),behaviors.items(),objectives.items()):
                    if 'alt' in value and field in value['alt']:
                        record[key] = record[field]
                        del record[field]
                        break
                else:
                    # Model previously explored
                    links = model2links(field,variations)
                    values = []
                    for link in variations:
                        try:
                            values.append(links[link['code']])
                        except KeyError:
                            # Default is 0
                            values.append(0)
                    model = links2model(values,variations)
                    if field != model:
                        if model in record:
                            raise RuntimeError,\
                                'Field duplication\nOriginal: %s\nMapping: %s' % (field,model)
                        record[model] = record[field]
                        del record[field]
                    if first:
                        fields.append(model)
                    first = False
            data[record['V1']] = record
            record['__predictions__'] = [record[model] for model in models if model in record]
    return data

def writePredictions(data,variations,filename):
    with open(filename,'w') as csvfile:
        fields = None
        for record in sorted(data,key=lambda r: r['V1']):
            if record.has_key('predictions'):            
                for model,prediction in sorted(record['predictions'].items()):
                    newRecord = {'V1': record['V1'],
                                 'Leave': prediction}
                    try:
                        newRecord['P(Leave)'] = record['P(Leave)'][model]
                    except KeyError:
                        newRecord['P(Leave)'] = ''
                    links = model2links(model,variations)
                    for variation in variations:
                        code = variation['code']
                        value = variation['domain'][links[code]]
                        if value is None:
                            newRecord[code] = ''
                        elif len(value) == 1:
                            newRecord[code] = '%d' % (value[0])
                        else:
                            assert len(value) == 2
                            newRecord[code] = '%d:%d' % tuple(value)
                    if fields is None:
                        fields = sorted(newRecord.keys())
                        writer = csv.DictWriter(csvfile,fields,extrasaction='ignore')
                        writer.writeheader()
                    writer.writerow(newRecord)
            
def readPredictions(data,variations,filename):
    with open(filename,'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for record in reader:
            if not data[record['V1']].has_key('predictions'):
                data[record['V1']]['predictions'] = {}
                data[record['V1']]['P(Leave)'] = {}
            links = []
            for variation in variations:
                code = variation['code']
                if record[code] == '':
                    value = None
                else:
                    value = map(int,list(record[code].split(':')))
                links.append(variation['domain'].index(value))
            model = links2model(links,variations)
            data[record['V1']]['predictions'][model] = record['Leave']
            if record['P(Leave)']:
                data[record['V1']]['P(Leave)'][model] = float(record['P(Leave)'])
    return data
    
if __name__ == '__main__':
    logging.basicConfig(level=logging.ERROR)
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',default='WARNING',help='Level of logging detail')
    # Optional argument that forces model search across all records (instead of just ones that
    # don't have matching models yet, which is the default)
    parser.add_argument('-a','--all',action='store_true',
                      help='evaluate models against all records (not just unmatched ones) [default: %(default)s]')
    # Optional argument that forces generation of new predictions on top of any already existing
    # (default is to generate new predictions only if none already exist)
    parser.add_argument('-p','--predict',action='store_true',
                      help='generate new predictions even if some already exist [default: %(default)s]')
    # Optional argument that forces auto-correction if unmatched records
    parser.add_argument('-c','--correct',action='store_true',
                      help='try to auto-find correct models for unmatched data [default: %(default)s]')
    # Positional argument for input file
    parser.add_argument('input',nargs='?',default='seattle',
                        help='Root name of CSV files for input/output [default: %(default)s]')
    args = vars(parser.parse_args())
    # Extract logging level from command-line argument
    level = getattr(logging, args['debug'].upper(), None)
    if not isinstance(level, int):
        raise ValueError('Invalid debug level: %s' % args['debug'])
    logging.getLogger().setLevel(level)
    if os.path.isfile('%s-input.csv' % (args['input'])):
        data = readInputData('%s-input.csv' % (args['input']))
    else:
        raw = readInputData('%s-raw.csv' % (args['input']))
        data = processData(raw.values(),createNew=True)
        fields = data[0].keys()
        for row in data:
            assert set(row.keys()) == set(fields)
        writeInput(data,fields,'%s-input.csv' % (args['input']))
    # What is the hypothesis space?
    variations = readVariations('%s-variations.csv' % (args['input']))
    varLens = [range(link['range']) for link in variations]
    models = [links2model(model,variations) \
              for model in itertools.product(*varLens)]
    # What are the previously tested hypotheses?
    if os.path.isfile('%s-predictions.csv' % (args['input'])):
        generate = args['predict']
        readPredictions(data,variations,'%s-predictions.csv' % (args['input']))
    else:
        # No predictions yet, so must generate regardless of command-line argument
        generate = True
    for record in data.values():
        # Missing predictions, so let's enter empty tables
        if not record.has_key('predictions'):
            record['predictions'] = {}
            record['P(Leave)'] = {}
        record['matches'] = {m for m in record['predictions'].keys() if record['predictions'][m] == record['Leave']}
    # What's the working set of data?
    if args['all']:
        working = data
    else:
        working = {key: record for key,record in data.items() if len(record['matches']) == 0}
    logging.info('|Working Set| = %d' % (len(working)))
    # Load/Create PsychSim scenario
    world = buildWorld()
#    if os.path.isfile('%s.psy' % (args['input'])):
#        world = World('%s.psy' % (args['input']))
#    else:
#        world = buildWorld()
#        world.save('%s.psy' % (args['input']))
    if generate:
        # Generate predictions
        try:
            generatePredictions(data.values(),models,variations,world)
        except KeyboardInterrupt:
            pass
        writePredictions(data.values(),variations,'%s-predictions.csv' % (args['input']))
#    choices = searchCover(remaining,reducedModels)
    # mapping = reduceModels(data,variations,models)
    # reducedModels = mapping.keys()
    # for model in reducedModels:
    #     print(model)
    #     if len(mapping[model]) > 1:
    #         print(mapping[model])
    #         exemplar = list(mapping[model])[0]
    #         for record in data.values():
    #             record[model] = record[exemplar]
    #     for record in data.values():
    #         print('\t',record[model])
    remaining,unmatchable = findImpossibles(data,models)
    if len(unmatchable) > 0 and args['correct']:
        # Analyze differences
        correctModels(working,models,variations,world)
        writePredictions(data.values(),variations,'%s-predictions.csv' % (args['input']))
        remaining,unmatchable = findImpossibles(data,models)
    choices = greedyCover(remaining)
    total = 0
    for index in range(len(choices)):
        model,num = choices[index]
        total += num
        logging.info('%2d: %s covers %3d (Total covered: %3d)' % (index+1,model,num,total))
    logging.info('%d/%d' % (len(data)-len(unmatchable),len(data)))
