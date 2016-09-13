"""
Modeling the decision-making of Seattle residents after an anthrax release. Based on:
Heather Rosoff, Richard John, William J. Burns, and Robert Siko (2012). 
"Structuring Uncertainty and Conflicting Objectives for Life or Death
Decisions Following an Urban Biological Catastrophe". 
Journal of Integrated Disaster Risk Management.
"""
# TODO: SRA
# TODO: pull out relevant text from proposal and any other writeups.

import psychsim.probability
from psychsim.pwl import *
from psychsim.action import powerset
from psychsim.reward import *
from psychsim.world import *
from psychsim.agent import Agent

import psychsim.ui.diagram as diagram

# Statements about a resident's beliefs
beliefs = {
    'risk to Seattle': \
        {'statement': 'I believe the anthrax attack poses a serious risk to residents of the Seattle area.',
         'agent': False,
         'response': 4},
    'risk to me': \
        {'statement': 'I believe the anthrax attack  poses a serious risk to me.',
         'agent': True,
         'response': 1},
    'anxiety': \
        {'statement': 'The anthrax attack has created a great deal of anxiety for me. ',
         'agent': True,
         'response': 3},
    'paycheck one': \
        {'statement': 'If I miss ONE paycheck, I would not have enough money to buy food and pay bills. ',
         'agent': True,
         'response': 1},
    'paycheck several': \
        {'statement': 'If I miss SEVERAL paychecks, I would not have enough money to buy food and pay bills.',
         'agent': True,
         'response': 2},
    'government response': \
        {'statement': 'I believe the government will provide emergency response and health services I might need, for example antibiotics.',
         'agent': False,
         'response': 3},
    }
response2belief = [0., .1, .25, .5, .75, .9, 1.]

# Statements about a resident's hypothetical behaviors
behaviors = {
    'routine': \
        {'statement': 'I would change my daily routine to avoid exposure to anthrax.',
         'response': 3,
         'phase': 'how','location': 'Seattle'},
    'work': \
        {'statement': 'I would continue going to work or school if open.',
         'response': 3,
         'phase': 'how','location': 'Seattle'},
    'precautions': \
        {'statement': 'I would take necessary precautions to avoid anthrax exposure when outside.',
         'response': 3,
         'phase': 'how','location': 'Seattle'},
    'antibiotic': \
        {'statement': 'I would obtain the antibiotic and take it as directed.',
         'response': 3,
         'phase': 'how','location': 'Seattle'},
#    'children school': \
#        {'statement': 'I would continue to take my children to school if open.',
#         'response': 3,
#         'phase': 'how','location': 'Seattle'},
    'leave': \
        {'statement': 'I would LEAVE the Seattle area for at least a short time after watching the earlier news video.',
         'response': 3,
         'phase': 'where','location': 'Seattle'},
    'stay': \
        {'phase': 'where','location': 'Seattle'},
    'return': \
        {'phase': 'where','location': 'beyond'},
    'temporary': \
        {'statement': 'I would look for temporary work.',
         'response': 3,
         'phase': 'how','location': 'beyond'},
    'permanent': \
        {'statement': 'I would plan to move out of the Seattle area (e.g. look for permanent employment, school, housing).',
         'response': 3,
         'phase': 'how','location': 'beyond'},
    }
importance = {
    'risk':
        {'statement': 'Risk of anthrax exposure or infection.',
         'agent': False,
         'response': 3,
         'rank': 1},
    'healthcare':
        {'statement': 'Availability of health care services including antibiotics.',
         'agent': False,
         'response': 3,
         'rank': 2},
    'deaths':
        {'statement': 'The increasing number of deaths and new anthrax infections.',
         'agent': False,
         'response': 3,
         'rank': 3},
    'goods':
        {'statement': 'Availability of goods (e.g.  food, water, and other essentials).',
         'agent': False,
         'response': 3,
         'rank': 4},
    'employment':
        {'statement': 'Availability of employment in the Seattle area.',
         'agent': False,
         'response': 3,
         'rank': 5},
#    'finances':
#        {'statement': 'Being financially stable (e.g. having savings to cover your living expenses).',
#         'agent': True,
#         'response': 3,
#         'rank': 6},
    'antibiotics':
        {'statement': 'My willingness to take the antibiotics for 60 days.',
         'agent': True,
         'response': 3,
         'rank': 7},
    }
beliefs.update(importance)

objectives = {
    'safety': \
        {'objective': 'Personal safety (from crime)',
         # TODO: looting for basic needs (e.g., because truckers refuse to come in)
         # TODO: looting for treatments
         # TODO: looting to exploit chaos
         'actions': {'leave': False, None: True},
         'beliefs': {'goods': False,'employment': False}, # TODO: check this
         'rank': 1},
    'finances': \
        {'objective': 'Financial stability (being financially stable/secure, general affordability of necessities)',
         'actions': {'work': True,'permanent': True, 'temporary': True, None: False},
         'beliefs': {'paycheck one': False, 'paycheck several': False},
         'rank': 2},
    'survival': \
        {'objective': 'Health safety and personal anthrax survival (effectiveness and access to antibiotic)',
         'actions': {'routine': True, 'work': False, 'precautions': True, 'antibiotic': True, None: False},
         'beliefs': {'government response': True,'risk to me': False},
         'rank': 3},
#    'family': \
#        {'objective': 'Family or friend anthrax survival',
#         'actions': {None: True},
#         'rank': 4},
    }
                    
def incrementLeaves(tree,value):
    if tree.has_key('if'):
        return {'if': tree['if'],
                True: incrementLeaves(tree[True],value),
                False: incrementLeaves(tree[False],value)}
    elif value:
        return {True: tree[True]+1,False: tree[False]}
    else:
        return {True: tree[True],False: tree[False]+1}

def leaf2matrix(tree,key):
    if tree.has_key('if'):
        return {'if': tree['if'],
                True: leaf2matrix(tree[True],key),
                False: leaf2matrix(tree[False],key)}
    else:
        prob = noisyOr(tree[True],.75,.1)
        return {'distribution': [(setTrueMatrix(key),prob),(setFalseMatrix(key),1.-prob)]}

def noisyOr(onCount,onProb,leak=0.):
    return 1.- (1.-leak)*pow(1.-onProb,onCount)

if __name__ == '__main__':
    world = World()
    world.diagram = diagram.Diagram()
    world.diagram.setColor(None,'ivory')

    resident = Agent('resident')
    world.diagram.setColor(resident.name,'palegreen')
    world.addAgent(resident)
#    family = Agent('family')
#    world.diagram.setColor(family.name,'mediumseagreen')
#    world.addAgent(family)
    gov = Agent('government')
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
    joints = [name for name in behaviors.keys() if behaviors[name]['phase'] == 'how' and \
                     behaviors[name]['location'] == 'Seattle']
    for joint in powerset(joints):
        action = ActionSet([behaviors[name]['action'] for name in joint])
        label = ' '.join(joint)
        options[label] = resident.addAction(action)
        # Only legal during "how" phase and if living in Seattle
        resident.setLegal(options[label],makeTree({'if': equalRow('phase','how'),
                                                   True: {'if': equalRow(location,'Seattle'),
                                                          True: True, False: False},
                                                   False: False}))
    # Lifestyle choices outside Seattle
    for joint in [name for name in behaviors.keys() if behaviors[name]['phase'] == 'how' and \
                     behaviors[name]['location'] == 'beyond']:
        options[joint] = resident.addAction(behaviors[joint]['action'])
        # Only legal during "how" phase and if *not* living in Seattle
        resident.setLegal(options[joint],makeTree({'if': equalRow('phase','how'),
                                                   True: {'if': equalRow(location,'beyond'),
                                                          True: True, False: False},
                                                   False: False}))
    # Choices of where to live
    for joint in [name for name in behaviors.keys() if behaviors[name]['phase'] == 'where']:
        options[joint] = resident.addAction(behaviors[joint]['action'])
        # Only legal during "where" phase
        resident.setLegal(options[joint],makeTree({'if': equalRow('phase','where'),
                                                   True: {'if': equalRow(location,behaviors[name]['location']),
                                                          True: True, False: False},
                                                   False: False}))

    # Objectives
    ranks = [objective['rank'] for objective in objectives.values()]
    ceiling = max(ranks) + 1
    total = float(sum(ranks))
    for name,objective in objectives.items():
        objective['key'] = world.defineState(resident.name,name,bool)
        world.setFeature(objective['key'],True)
        resident.setReward(maximizeFeature(objective['key']),float(ceiling-objective['rank'])/total)

    # Beliefs
    for name,belief in beliefs.items():
        if belief['agent']:
            agent = resident.name
        else:
            agent = None
        belief['key'] = world.defineState(agent,name,bool,description=belief['statement'])
        distribution = {True: response2belief[belief['response']]}
        distribution[False] = 1. - distribution[True]
#        world.setFeature(belief['key'],psychsim.probability.Distribution(distribution))
        world.setFeature(belief['key'],round(distribution[True]) == 1)

    # Dynamics of objectives
    for name,objective in objectives.items():
        # Consider possible "how" behaviors
        for option in [o for o in resident.actions if o != options['leave']]:
            # How many actions contribute to this objective?
            count = {True: 0, False: 0, None: 0}
            total = len(objective['actions'])
            if len(option) == 0:
                count[None] += 1
            else:
                for action in option:
                    try:
                        count[objective['actions'][action['verb']]] += 1
                    except KeyError:
                        count[None] += 1
            if count[None] > 0:
                count[objective['actions'][None]] += 1
            # How many beliefs contribute to this objective?
            try:
                causes = objective['beliefs']
            except KeyError:
                causes = {}
            tree = count
            for feature,value in causes.items():
                tree = {'if': trueRow(beliefs[feature]['key']),
                        True: incrementLeaves(tree,value),
                        False: incrementLeaves(tree,not value)}
            tree = leaf2matrix(tree,objective['key'])
            if name == 'survival':
                tree = {'if': equalRow(stateKey(resident.name,'location',True),'Seattle'),
                        True: tree, False: setTrueMatrix(objective['key'])}
            world.setDynamics(objective['key'],option,makeTree(tree))
    
    # Movement dynamics
    world.setDynamics(location,behaviors['leave']['action'],makeTree(setToConstantMatrix(location,'beyond')))
    world.setDynamics(location,behaviors['return']['action'],makeTree(setToConstantMatrix(location,'Seattle')))

    # Phase dynamics
    world.setDynamics('phase',True,makeTree({'if': equalRow('phase','where'),
                                             True: setToConstantMatrix('phase','how'),
                                             False: setToConstantMatrix('phase','where')}))

    # Decision-making parameters
    resident.setAttribute('horizon',2)
    resident.setAttribute('selection','distribution')
    
    world.save('anthrax.psy')

    #    world.printState()

    for tree,weight in resident.getAttribute('R').items():
        print weight,tree
    decision = Distribution()
    for vector in world.state[None].domain():
        world.printVector(vector)
        result = resident.decide(vector,selection='distribution')
        for action in result['action'].domain():
            decision.addProb(action,world.state[None][vector]*result['action'][action])
            print 'Choice:',action
            outcome = world.stepFromState(vector,action)
            world.printState(outcome['new'])
    print decision
