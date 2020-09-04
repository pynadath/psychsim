"""
A robot that teams with a human to perform a task in a virtual environment.
@author: Santosh Shankar, modified by David V. Pynadath
@organization: USC ICT
@var DISTANCES: A table of travel times between waypoints (asymmetric)
@var TEMPLATES: Explanation templates
"""
from __future__ import print_function
import datetime
import fileinput
import os
import pickle
import pprint
pp = pprint.PrettyPrinter(indent=4)
import random
from string import Template
import sys
import tempfile
import time
import numpy as np
import re

from psychsim.pwl import *
from psychsim.world import *
from psychsim.agent import Agent
from psychsim.reward import *
from psychsim.action import *

import psychsim.probability

from psychsim.domains.hri.robotWaypoints import NEWWAYPOINTS as WAYPOINTS
from psychsim.domains.hri.robotWaypoints import DISTANCES
import psychsim.domains.hri.dtree as dtree
TEMPLATES = {
    # TODO: Positive/negative framing
    # TODO: Sensor model
    'positive': {
        # If a location is safe...
        True: 'There is a $B_danger_none% chance that the building is safe.',
        # If a location is not safe...
        False: 'There is a $B_danger_none% chance that the building is safe.'},
    'negative': {
        # If a location is safe...
        True: 'There is a $B_danger_not_none% chance that the building is dangerous.',
        # If a location is not safe...
        False: 'There is a $B_danger_not_none% chance that the building is dangerous.'},
    'general': { 'desc' : 'I have finished surveying the $B_waypoint.'},
    'decision': {
        # If a location is safe...
        True: ' I think the place is safe.',
        # If a location is not safe...
        False: ' I think the place is dangerous.'},
    'confidence': {
        # If a location is safe...
        True: ' I am$flag $B_danger_none% confident about this assessment.',
        # If a location is not safe...
        False: ' I am$flag $B_danger_not_none% confident about this assessment.'},
    'NBC': {
        # If I observe NBC...
        False: 'My sensors have not detected any nuclear, biological or chemical weapons in here.',
        # If I observe NBC...
        True: 'My NBC sensors have detected traces of dangerous chemicals.'},
    'armed': {
        # If I do not observe armed gunmen...
        False: 'From the image captured by my camera, I have not detected any armed gunmen in the $B_waypoint.',
        # If I observe armed gunmen...
        True: 'From the image captured by my camera, I have detected armed gunmen in the $B_waypoint.'},
    'microphone': {
        # If I do not hear anything...
        'nobody': 'My microphone did not pick up anyone talking.',
        # If I hear friendly conversation...
        'friendly': 'My microphone picked up a friendly conversation.',
        # If I hear suspicious conversation...
        'suspicious': 'My microphone picked up a suspicious conversation.'},
    'benevolence': {
        # If a location is safe...
        True: 'I don\'t think entering the $B_waypoint without protective gear will pose any danger to you. Without the protective gear, you will be able to search the building a little faster.',
        # If a location is unsafe...
        False: 'I think it will be dangerous for you to enter the $B_waypoint without protective gear. The protective gear will slow you down a little.'},
    'acknowledgment': {
        # Check if the person died 0 -- alive else 1 -- dead
        'correct': 'It seems that my estimate of the $waypoint was correct. ',
        'delay': 'It seems that my estimate of the $waypoint was incorrect. ',
        'died': 'It seems that my estimate of the $waypoint was incorrect. ',
        'required': 'I\'ve updated my algorithm accordingly. ',
        # False positive
        True: 'It seems that my assessment of the $B_waypoint was incorrect. I will update my algorithms when we return to base after the mission.',
        # False negative
        False: 'It seems that my assessment of the $B_waypoint was incorrect. I will update my algorithms when we return to base after the mission.',
        None: '',
        'always': 'In the future, I will be $compare likely to report a safe estimate when my sensors have the same readings.',
        },
    'ack_learning':{
        'always':'It seems that my assessment of the $B_waypoint was incorrect. ',
        'update_info_cam_neg':'I have changed my FNprob of the camera sensor from $old_val to $new_val. ',
        'update_info_micro_neg':'I have changed my FNprob of the microphone sensor from $old_val to $new_val. ',
        'update_info_nbc_neg':'I have changed my FNprob of the nbc sensor from $old_val to $new_val. ',
        'update_info_cam_pos':'I have changed my FPprob of the camera sensor from $old_val to $new_val. ',
        'update_info_micro_pos':'I have changed my FPprob of the microphone sensor from $old_val to $new_val. ',
        'update_info_nbc_pos':'I have changed my FPprob of the nbc sensor from $old_val to $new_val. ',
        'update_human_prob_prot': 'I have changed my humanProbProtected from $old_val to $new_val. ',
        'update_human_prob_unprot': 'I have changed my humanProbUnProtected from $old_val to $new_val. '
        },
    'decision_tree':{
        'false':'There has been no change in the Decision Tree.',
        'true':{
            'single':'There has been $num change in the Decision Tree, namely $names.',
            'multiple':'There have been $num changes in the Decision Tree, namely $names.'
        }
    },
    'decision_tree_explanation':{
        'start':"Because the robot's prediction for $sensor is that $explain",
        'middle':", for $sensor $explain",
        'not_visited':". The $sensor node is not visited for this partciular decision and robot's prediction for it is $explain",
        'not_present':". The $sensor node is not present in the decision tree and robot's prediction for it is $explain",
        'conclude':". Therefore, the recommendation as per Decision Tree is $recommendation.",
        'NBCsensor_False': "there's no presence of Nuclear or Biochemical weapon",
        "NBCsensor_True" : "there's a presence of Nuclear or Biochemical weapon",
        "camera_True" : "there's a presence of armed gunmen",
        "camera_False" : "there's no presence of armed gunmen",
        "microphone_friendly" : "there's a presence of friendly conversation",
        "microphone_nobody" : "there's no presence of conversation",
        "microphone_suspicious" : "there's a presence of suspicious conversation",
    },
    'why_not_explanation':{
        'header':'Why not $recommendation? Since',
        'reasoning1':"the robot's $sensor prediction is $value,",
        'reasoning2':'$sensor $danger,',
        'conclusion':'Hence, a $recommendation recommendation does not make sense.',
    'NBCsensor_False': "there's no presence of Nuclear or Biochemical weapon",
        "NBCsensor_True" : "there's a presence of Nuclear or Biochemical weapon",
        "camera_True" : "there's a presence of armed gunmen",
        "camera_False" : "there's no presence of armed gunmen",
        "microphone_friendly" : "there's a presence of friendly conversation",
        "microphone_nobody" : "there's no presence of conversation",
        "microphone_suspicious" : "there's a presence of suspicious conversation"
    },
    'human_compliance_model':{
        'unprotected':'I think the Human Probability of following my action of Unprotected is: $prob',
        'protected':'I think the Human Probability of following my action of Protected Gear is: $prob'
    },
   'convince':{
           'sensors':{
                'nobody':
                        {False:
                                {False: 'None of my sensors detected any threat. ',
                                 True: 'My microphone and camera did not pick up any threat but my NBC sensor has detected danger. '},
                        True:
                            {False: 'My microphone and NBC sensor did not pick up any threat but my camera has captured suspicious activity. ',
                             True: 'My microphone did not pick up any threat but my NBC sensor and camera have detected danger. '}
                                    },
                'friendly':
                        {False:
                                {False: 'My microphone has detected a friendly conversation inside. My Camera and NBC sensor did not detect any threat. ',
                                 True: 'My microphone has detected a friendly conversation inside. My Camera did not pick up any threat but my NBC sensor has detected danger. '},
                        True:
                            {False: 'My microphone has detected a friendly conversation inside. My NBC sensor did not pick up any threat but Camera has captured suspicious activity. ',
                             True: 'My microphone has detected a friendly conversation inside. My NBC sensor and camera have detected danger. '}
                                    },
                'suspicious':
                        {False:
                                {False: 'My microphone has detected a suspicious conversation inside. My Camera and NBC sensor did not detect any threat. ',
                                 True: 'My microphone has detected a suspicious conversation inside. My Camera did not pick up any threat but my NBC sensor has detected danger. '},
                        True:
                            {False: 'My microphone has detected a suspicious conversation inside. My NBC sensor did not pick up any threat but my Camera has captured suspicious activity. ',
                             True: 'My microphone has detected a suspicious conversation inside. My NBC sensor and camera have detected danger. '}
                                    },
                },
        'always':'The last time I had similar sensor readings was at the $waypoint. I estimated that the $waypoint was $Action with $Confidence% confidence. ',
        'delay':'Because my previous estimate was incorrect, I\'ve updated my algorithm to report safety with a $diff confidence in the future, given the same sensor readings. Thus after surveying the $waypoint,',
        'died':'Because my previous estimate was incorrect, I\'ve updated my algorithm to report safety with a $diff confidence in the future, given the same sensor readings. Thus after surveying the $waypoint,',
        'correct':'Because my previous estimate was correct, I updated my algorithm to report safety with a $diff confidence, given the same sensor readings. Thus after surveying the $waypoint,',
        'sensor reliability': '. It seems that my $sensor1 is more realible than $sensor2',

        },
    }
CREATE_TAG = 'Created:'
MESSAGE_TAG = 'Message:'
LOCATION_TAG = 'Location:'
USER_TAG = 'Protective:'
COMPLETE_TAG = 'Complete'
ACK_TAG = 'Acknowledged:'
RECOMMEND_TAG = 'Recommend protection:'
DTREE_TAG = "Decision Tree:"
DTREE_EXPLANATION = "Decision Tree Explanation:"
GRAPH_DIR = "Graph Directory:"
DTREE_UPDATES = "Decision Tree Updates:"
VALUE_TAG = 'Value'
WHY_NOT_TAG = "Why Not:"
ITERATION_TAG = "Iteration Number:"
PREV_TREE_TAG = "Previous Tree:"

CODES = {'ability': {'s': 'badSensor','g': 'good','m': 'badModel'},
         'explanation': {'n': 'none','a': 'ability','c': 'confidence','b': 'abilityconfidence'},
         'embodiment': {'r': 'robot','d': 'dog'},
         'acknowledgment': {'n': 'no','y': 'yes'},
         'learning': {'n': 'none','b': 'model-based', 'f': 'model-free'},
         }

def createWorld(username='anonymous',level=0,ability='good',explanation='none',
                embodiment='robot',acknowledgment='no',learning='none',sequence=False,root='.',ext='xml', reliability = 0.80,cam_fnProb=0.01,cam_fpProb=0.01,
                micro_fnProb=0.01,micro_fpProb=0.01,nbc_fnProb=0.01,nbc_fpProb=0.01,humanProbProt=0.5,humanProbUnprot=0.5):
    """
    Creates the initial PsychSim scenario and saves it
    @param username: name of user ID to use in filenames
    @param level: robot mission level to use as template
    @param ability: the level of the robot's ability
      - good or C{True}: perfect sensors and sensor model
      - badSensor or C{False}: noisy sensors, but perfect model of noisy sensors
      - badModel: perfect sensors, but imperfect model of sensors
    @type ability: bool
    @param explanation: the type of explanation to use
      - none: No explanations
      - ability: Explanation based on robot ability provided.
      - abilitybenevolence: Explanation based on both robot's ability and benevolence provided.
    @type explanation: str
    @param embodiment: the robot's embodiment
      - robot: The robot looks like a robot
      - dog: The robot looks like a dog
    @type embodiment: str
    @param acknowledgment: the robot's behavior regarding the acknowledgment of errors
      - no: The robot does not acknowledge its errors
      - yes: The robot acknowledges its errors
    @param learning: the robot performs model-based RL
      - no: The robot does not perform RL
      - yes: The robot performs RL
    @type acknowledgment: str
    @param root: the root directory to use for files (default is current working directory)
    @param ext: the file extension for the PsychSim scenario file
      - xml: Save as uncompressed XML
      - psy: Save as bzipped XML
    @type ext: str
    """

    print("**************************createWorld***********************")
    print('Username:\t%s\nLevel:\t\t%s' % (username,level+1))
    print('Ability\t\t%s\nExplanation:\t%s\nEmbodiment:\t%s\nAcknowledge:\t%s\nLearning:\t%s' % (ability,explanation,embodiment,acknowledgment,learning))

    # Pre-compute symbols for this level's waypoints
    for point in WAYPOINTS[level]:
        if not 'symbol' in point:
            point['symbol'] = point['name'].replace(' ','')

    world = World()

    world.defineState(WORLD,'level',int,lo=0,hi=len(WAYPOINTS)-1,
                      description='Static variable indicating what mission level')
    world.setState(WORLD,'level',level)

    world.defineState(WORLD,'time',float)
    world.setState(WORLD,'time',0.)

    world.defineState(WORLD, 'iteration', int)
    world.setState(WORLD, 'iteration',0)

    # world.defineState(WORLD, 'prev dtree',list)
    # world.setState(WORLD, 'prev dtree', [])


    key = world.defineState(WORLD,'phase',set,lo={'scan','move'},
                            description='What phase of the turn is it')
    world.setState(WORLD,'phase','move')
    # Alternate between phases
    tree = makeTree({'if': equalRow(key,'scan'),
                     True: setToConstantMatrix(key,'move'),
                     False: setToConstantMatrix(key,'scan')})
    world.setDynamics(key,True,tree)

    # Buildings
    threats = ['none','NBC','armed']
    for waypoint in WAYPOINTS[level]:
        if not 'symbol' in waypoint:
            waypoint['symbol'] = waypoint['name'].replace(' ','')
        building = world.addAgent(waypoint['symbol'])
        building.setAttribute('static',True)
        # Has the robot scanned this waypoint?
        key = world.defineState(waypoint['symbol'],'scanned',bool)
        world.setFeature(key,False)
        # Has the human teammate entered this waypoint?
        key = world.defineState(waypoint['symbol'],'entered',bool)
        world.setFeature(key,False)
        # Are there dangerous chemicals or armed people here?
        key = world.defineState(waypoint['symbol'],'danger',list,threats[:])
        if 'NBC' in waypoint and waypoint['NBC']:
            world.setFeature(key,'NBC')
        elif 'armed' in waypoint and waypoint['armed']:
            world.setFeature(key,'armed')
        else:
            world.setFeature(key,'none')
        key = world.defineState(waypoint['symbol'],'recommendation',list,
                                ['none','protected','unprotected'])
        world.setFeature(key,'none')

    # All done when every building has been visited by teammate
    row = andRow([makeFuture(stateKey(wp['symbol'],'entered'))
                  for wp in WAYPOINTS[level]])
    world.addTermination(makeTree({'if': row,
                                   True: setTrueMatrix(TERMINATED),
                                   False: setFalseMatrix(TERMINATED)}))
    # Human
    human = world.addAgent('human')
    human.setAttribute('static',True)

    world.defineState(human.name,'alive',bool)
    human.setState('alive',True)
#    world.defineState(human.name,'deaths',int)
#    human.setState('deaths',0)

    # Robot
    robot = world.addAgent('robot')

    # Robot states
    world.defineState(robot.name,'waypoint',list,[point['symbol'] for point in WAYPOINTS[level]])
    robot.setState('waypoint',WAYPOINTS[level][getStart(level)]['symbol'])

    world.defineState(robot.name,'explanation',list,['none','ability','abilitybenevolence','abilityconfidence','confidence'])
    robot.setState('explanation',explanation)

    world.defineState(robot.name,'embodiment',list,['robot','dog'])
    robot.setState('embodiment',embodiment)

    world.defineState(robot.name,'acknowledgment',list,['no','yes'])
    robot.setState('acknowledgment',acknowledgment)

    world.defineState(robot.name,'learning',list,['none','model-free','model-based'])
    robot.setState('learning',learning)

    world.defineState(robot.name,'cameraFNProb',
                      description='Probability of false negative from camera')
    robot.setState('cameraFNProb',cam_fnProb)

    world.defineState(robot.name, 'cameraFPProb',
                      description='Probability of false positive from camera')
    robot.setState('cameraFPProb', cam_fpProb)

    world.defineState(robot.name, 'microFNProb',
                      description='Probability of false negative from microphone')
    robot.setState('microFNProb', micro_fnProb)

    world.defineState(robot.name, 'microFPProb',
                      description='Probability of false positive from microphone')
    robot.setState('microFPProb', micro_fpProb)

    world.defineState(robot.name, 'nbcFNProb',
                      description='Probability of false negative from nbc')
    robot.setState('nbcFNProb', nbc_fnProb)

    world.defineState(robot.name, 'nbcFPProb',
                      description='Probability of false positive from nbc')
    robot.setState('nbcFPProb', nbc_fpProb)

    world.defineState(robot.name, 'humanProbProtected',
                      description='Probability of human following the protected recommendation')
    robot.setState('humanProbProtected', humanProbProt)
    world.defineState(robot.name, 'humanProbUnprotected',
                      description='Probability of human following the unprotected recommendation')
    robot.setState('humanProbUnprotected', humanProbUnprot)

    world.defineState(robot.name,'ability',list,['badSensor','badModel','good'])
    if ability is True:
        # Backward compatibility with boolean ability
        ability = 'good'
    elif ability is False:
        ability = 'badSensor'
    robot.setState('ability',ability)

    # Commands from teammate
    world.defineState(robot.name,'command',list,['none']+[point['symbol'] for point in WAYPOINTS[level]])
    robot.setState('command','none')

    # Robot's sensor observations
    omega = robot.defineObservation('microphone',domain=list,
                                    lo=['nobody','friendly','suspicious'])
    world.setFeature(omega,'nobody')
#    robot.setO('microphone',None,makeTree(setToConstantMatrix(omega,'nobody')))
    omega = robot.defineObservation('NBCsensor',domain=bool)
    world.setFeature(omega,False)
#    robot.setO('NBCsensor',None,makeTree(setFalseMatrix(omega)))
    omega = robot.defineObservation('camera',domain=bool)
    world.setFeature(omega,False)
#    robot.setO('camera',None,makeTree(setFalseMatrix(omega)))

    # Actions
    for end in range(len(WAYPOINTS[level])):
        symbol = WAYPOINTS[level][end]['symbol']
        # Robot movement
        action = robot.addAction({'verb': 'moveto','object': symbol})
        # Legal if no contradictory command
        tree = makeTree({'if': equalRow(stateKey(WORLD,'phase'),'move'),
                         True: {'if': equalRow(stateKey(robot.name,'command'),'none'),
                                True: {'if': trueRow(stateKey(symbol,'scanned')),
                                                     True: False, False: True},
                                False: {'if': equalRow(stateKey(robot.name,'command'),
                                                       symbol),
                                        True: True, False: False}},
                         False: False})
        robot.setLegal(action,tree)
        # Dynamics of robot's location
        key = stateKey(action['subject'],'waypoint')
        tree = makeTree(setToConstantMatrix(key,symbol))
        world.setDynamics(key,action,tree)
        # Dynamics of scanned flag
        key = stateKey(symbol,'scanned')
        tree = makeTree(setTrueMatrix(key))
        world.setDynamics(key,action,tree)
        # He has risen!
        key = stateKey(human.name,'alive')
        tree = makeTree(setTrueMatrix(key))
        world.setDynamics(key,action,tree)
        # Dynamics of time
        key = stateKey(WORLD,'time')
        tree = setToConstantMatrix(key,0.)
        for start in range(len(WAYPOINTS[level])):
            if start != end:
                startsymbol = WAYPOINTS[level][start]['symbol']
                if sequence:
                    # Distance is measured by level sequence
                    distance = abs(start-end)*50
                else:
                    try:
                        distance = DISTANCES[WAYPOINTS[level][start]['name']][WAYPOINTS[level][end]['name']]
                    except KeyError:
                        try:
                            distance = DISTANCES[WAYPOINTS[level][end]['name']][WAYPOINTS[level][start]['name']]
                        except KeyError:
                            distance = 250
                tree = {'if': equalRow(stateKey(action['subject'],'waypoint'),startsymbol),
                        True: setToConstantMatrix(key,float(distance)/1000.),
                        False: tree}
        world.setDynamics(key,action,makeTree(tree))

        # Observations from scanning this waypoint
        key = stateKey(symbol,'danger')
        omega = stateKey(robot.name,'microphone')
        robot.setO('microphone',action,makeTree(generateMicO(world,key,falseNeg=micro_fnProb,falsePos = micro_fpProb)))
        omega = stateKey(robot.name,'NBCsensor')
        tree = makeTree(generateNBCO(world,key,falseNeg=nbc_fnProb,falsePos = nbc_fpProb))
        robot.setO('NBCsensor',action,tree)
        omega = stateKey(robot.name,'camera')
        robot.setO('camera',action,makeTree(generateCameraO(world,key,falseNeg=cam_fnProb,falsePos = cam_fpProb)))

        # Human entry: Dead or alive if unprotected?
        key = stateKey(human.name,'alive')
        action = robot.addAction({'verb': 'recommend unprotected','object': symbol})
        tree = makeTree({'if': equalRow(stateKey(symbol,'danger'),'none'),
                         True: setTrueMatrix(key), False: setFalseMatrix(key)})
        world.setDynamics(key,action,tree)
#        key = stateKey(human.name,'deaths')
#        tree = makeTree({'if': equalRow(stateKey(symbol,'danger'),'none'),
#                         True: noChangeMatrix(key), False: incrementMatrix(key,1.)})
#        world.setDynamics(key,action,tree)

        # Going in without protection takes no time
        key = stateKey(WORLD,'time')
        world.setDynamics(key,action,makeTree(setToConstantMatrix(key,0.)))
        tree = makeTree({'if': equalRow(stateKey(WORLD,'phase'),'scan'),
                         True: {'if': equalRow(stateKey(action['subject'],'waypoint'),
                                               symbol),
                                True: True,
                                False: False},
                         False: False})
        robot.setLegal(action,tree)
        # Dynamics of entered flag
        key = stateKey(symbol,'entered')
        tree = makeTree(setTrueMatrix(key))
        world.setDynamics(key,action,tree)
        # Observation upon entering
        danger = stateKey(symbol,'danger')
        omega = stateKey(robot.name,'microphone')
        robot.setO('microphone',action,
                   makeTree({'if': equalRow(danger,'armed'),
                             True: setToConstantMatrix(omega,'suspicious'),
                             False: setToConstantMatrix(omega,'friendly')}))
        omega = stateKey(robot.name,'NBCsensor')
        robot.setO('NBCsensor',action,
                   makeTree({'if': equalRow(danger,'NBC'),
                             True: setTrueMatrix(omega),
                             False: setFalseMatrix(omega)}))
        omega = stateKey(robot.name,'camera')
        robot.setO('camera',action,
                   makeTree({'if': equalRow(danger,'armed'),
                             True: setTrueMatrix(omega),
                             False: setFalseMatrix(omega)}))
        # Human entry: How much "time" if protected?
        action = robot.addAction({'verb': 'recommend protected','object': symbol})
        key = stateKey(WORLD,'time')
        world.setDynamics(key,action,makeTree(setToConstantMatrix(key,0.25)))
        tree = makeTree({'if': equalRow(stateKey(WORLD,'phase'),'scan'),
                         True: {'if': equalRow(stateKey(action['subject'],'waypoint'),
                                               symbol),
                                True: True,
                                False: False},
                         False: False})
        robot.setLegal(action,tree)
        # Dynamics of entered flag
        key = stateKey(symbol,'entered')
        tree = makeTree(setTrueMatrix(key))
        world.setDynamics(key,action,tree)
        # Observation upon entering
        danger = stateKey(symbol,'danger')
        omega = stateKey(robot.name,'microphone')
        robot.setO('microphone',action,
                   makeTree({'if': equalRow(danger,'armed'),
                             True: setToConstantMatrix(omega,'suspicious'),
                             False: setToConstantMatrix(omega,'friendly')}))
        omega = stateKey(robot.name,'NBCsensor')
        robot.setO('NBCsensor',action,
                   makeTree({'if': equalRow(danger,'NBC'),
                             True: setTrueMatrix(omega),
                             False: setFalseMatrix(omega)}))
        omega = stateKey(robot.name,'camera')
        robot.setO('camera',action,
                   makeTree({'if': equalRow(danger,'armed'),
                             True: setTrueMatrix(omega),
                             False: setFalseMatrix(omega)}))

    assert len(robot.models) == 1
    model = next(iter(robot.models.keys()))

    # Robot goals
    goal = makeTree(setToFeatureMatrix(stateKey(robot.name,REWARD),
                                       stateKey(WORLD,'time'),-1.))
#    goal = minimizeFeature(stateKey(WORLD,'time'))
    robot.setReward(goal,60.,model)

    goal = makeTree(setToFeatureMatrix(stateKey(robot.name,REWARD),
                                       stateKey(human.name,'alive')))
#    goal = achieveGoal(stateKey(human.name,'alive'))
    robot.setReward(goal,20.,model)

#    for point in WAYPOINTS[level]:
#        robot.setReward(maximizeFeature(stateKey(point['symbol'],'scanned')),2.)
    world.setOrder([robot.name])

    # Robot beliefs
    robot.resetBelief(ignore=[modelKey(robot.name)])
#    world.setModel(robot.name,model)
    value = 10./float(len(WAYPOINTS[level]))
    for index in range(len(WAYPOINTS[level])):
        waypoint = WAYPOINTS[level][index]
        key = stateKey(waypoint['symbol'],'danger')
        dist = psychsim.probability.Distribution({'NBC': value/2.,
                                                  'armed': value/2.,
                                                  'none': 1.-value})
        robot.setBelief(key,dist,model)

    robot.setAttribute('horizon',1)

    robot.random_indices = random.sample(range(0, len(WAYPOINTS[level])) , int(len(WAYPOINTS[level])*(1-reliability)))
    if learning == 'model-free':
        robot.table = {}
        populateTable(world,0,level)
        robot.old_decision = {}

    filename = getFilename(username,level,ext,root)
    os.makedirs(os.path.dirname(filename),exist_ok=True)
    with open(filename,'wb') as scenarioFile:
        pickle.dump(world,scenarioFile)
#    world.save(filename,ext=='psy')
    WriteLogData('%s user %s, level %d, ability %s, explanation %s, embodiment %s' % \
                     (CREATE_TAG,username,level,ability,explanation,embodiment),
                 username,level,root=root)
    return world

def generateMicO(world,key,falseNeg=0.05,falsePos = 0.05):
    omega = stateKey('robot','microphone')
    return {'if': equalRow(stateKey('robot', 'ability'), 'badModel'),
            # Robot's O doesn't match up with its good observations
            True: {'if': equalRow(key, 'armed'),
                   True: {'distribution':
                              [(setToConstantMatrix(omega, 'nobody'), 0.04),
                               (setToConstantMatrix(omega, 'friendly'), 0.03),
                               (setToConstantMatrix(omega, 'suspicious'), 0.93)]},
                   False: {'distribution':
                               [(setToConstantMatrix(omega, 'nobody'), 0.48),
                                (setToConstantMatrix(omega, 'friendly'), 0.49),
                                (setToConstantMatrix(omega, 'suspicious'), 0.03)]},
                   },
            False: {'if': equalRow(key, 'armed'),
                   True: {'distribution':
                              [(setToConstantMatrix(omega, 'nobody'), falseNeg),
                               (setToConstantMatrix(omega, 'friendly'), falseNeg),
                               (setToConstantMatrix(omega, 'suspicious'), 1. - 2*falseNeg)]},
                   False: {'distribution':
                               [(setToConstantMatrix(omega, 'nobody'), (1.-falsePos)/2),
                                (setToConstantMatrix(omega, 'friendly'), (1.-falsePos)/2),
                                (setToConstantMatrix(omega, 'suspicious'), falsePos)]},
                   }}

def generateNBCO(world,key,falseNeg=0.05,falsePos = 0.05):
    """
    @return: a observation function specification of the robot's NBC sensor
    @rtype: dict
    """
    omega = stateKey('robot','NBCsensor')
    return {'if': equalRow(stateKey('robot', 'ability'), 'badModel'),
            # Robot's O doesn't match up with its good observations
            True: {'if': equalRow(key,'NBC'),
                   True: {'distribution':
                              [(setFalseMatrix(omega),0.1),
                               (setTrueMatrix(omega),0.9)]},
                   False: {'distribution':
                               [(setFalseMatrix(omega),0.95),
                                (setTrueMatrix(omega),0.05)]},
                   },
            False: {'if': equalRow(key,'NBC'),
                   True: {'distribution':
                              [(setFalseMatrix(omega),falseNeg),
                               (setTrueMatrix(omega),1.-falseNeg)]},
                   False: {'distribution':
                               [(setFalseMatrix(omega),1.-falsePos),
                                (setTrueMatrix(omega),falsePos)]},
                   }}


def generateCameraO(world,key,belief=False,falseNeg=0.05,falsePos = 0.05):
    """
    @return: a observation function specification for use in a PWL function
    @rtype: dict
    """
    omega = stateKey('robot','camera')
    return {'if': equalRow(stateKey('robot','ability'),'badModel'),
            # Robot's O doesn't match up with its good observations
            True: {'if': equalRow(key,'armed'),
                    True: {'distribution':
                           [(setToConstantMatrix(omega,False),0.02),
                            (setToConstantMatrix(omega,True),0.98)]},
                    False: {'distribution':
                            [(setToConstantMatrix(omega,False),0.72),
                             (setToConstantMatrix(omega,True),0.28)]},
                   },
            False: {'if': equalRow(key,'armed'),
                    True: {'distribution':
                           [(setToConstantMatrix(omega,False),falseNeg),
                            (setToConstantMatrix(omega,True),1.-falseNeg)]},
                    False: {'distribution':
                            [(setToConstantMatrix(omega,False),1.-falsePos),
                             (setToConstantMatrix(omega,True),falsePos)]},
                    }}

def getStart(level):
    """
    @return: the index of the starting waypoint for the given level
    @rtype: int
    """
    for index in range(len(WAYPOINTS[level])):
        if 'start' in WAYPOINTS[level][index]:
            return index
    else:
        return 0

def symbol2index(symbol,level=0):
    """
    @return: the waypoint index corresponding to the given symbol (not full) name in the given level
    @rtype: int
    """
    for index in range(len(WAYPOINTS[level])):
        if 'symbol' in WAYPOINTS[level][index]:
            if WAYPOINTS[level][index]['symbol'] == symbol:
                return index
        elif WAYPOINTS[level][index]['name'].replace(' ','') == symbol:
            return index
    else:
        raise NameError('Unknown waypoint %s for level %d' % (symbol,level))

def index2symbol(index,level=0):
    """
    @return: the symbol (not full) name corresponding to the given waypoint index
    @rtype: str
    """
    try:
        return WAYPOINTS[level][index]['symbol']
    except KeyError:
        return WAYPOINTS[level][index]['name'].replace(' ','')

def getFilename(session=0,level=0,extension='xml',root='.'):
    """
    @return: the scenario file name for the given session ID and level
    @rtype: str
    """
    return os.path.join(root,'%s_%d.%s' % (session,level,extension))

def maxLevels():
    """
    @return: the number of levels defined
    @rtype: int
    """
    return len(WAYPOINTS)

def GetDecision(username,level,parameters,world=None,ext='xml',root='.',sleep=None,
                autonomous=False):
    """
    @param parameters: ignored if request is provided
    """
    print("***********************GetDecision********************")

    if sleep:
        time.sleep(sleep)
    filename = getFilename(username,level,ext,root)
    if world is None:
        # Get the world from the scenario file
        world = World(filename)
    oldVector = world.state

    robot = world.agents['robot']

    if 'robotWaypoint' in parameters:
        # Project world state
        robotIndex = int(parameters['robotWaypoint'])
        robotWaypoint = WAYPOINTS[level][robotIndex]
        if not 'symbol' in robotWaypoint:
            robotWaypoint['symbol'] = robotWaypoint['name'].replace(' ','')
        world.setState(robot.name,'waypoint',robotWaypoint['symbol'])
    else:
        # Read world state
        robotIndex = symbol2index(world.getState(robot.name,'waypoint').first(),
                                  level)
        robotWaypoint = WAYPOINTS[level][robotIndex]
        if not 'symbol' in robotWaypoint:
            robotWaypoint['symbol'] = robotWaypoint['name'].replace(' ','')

    # Process command
    try:
        command = int(parameters['commandWaypoint'])
        if command >= 0:
            world.setState(robot.name,'command',WAYPOINTS[level][int(command)]['symbol'])
        else:
            command = None
    except KeyError:
        command = None
    except TypeError:
        comand = None
    if command is None:
        world.setState(robot.name,'command','none')
    WriteLogData('Received command: %s' % (command),username,level,root=root)

    if autonomous:
        # Find the best action
        values = []
        model = world.getModel(robot.name).first()
        result = robot.decide(oldVector,horizon=1,model=model)
        destination = result['action']['object']
        WriteLogData('%s %s' % (LOCATION_TAG,destination),username,level,root=root)
        index = symbol2index(destination,level)
        destination = WAYPOINTS[level][index]
    elif command is None:
        # Move to next building in sequence
        index = robotIndex + 1
        destination = index2symbol(index,level)
        WriteLogData('%s %s' % (LOCATION_TAG,destination),username,level,root=root)
    else:
        # Commanded to move to specific building
        index = int(command)
        destination = index2symbol(index,level)
        WriteLogData('%s %s' % (LOCATION_TAG,destination),username,level,root=root)
    return index

def GetAcknowledgment(user,recommendation,location,danger,username,level,parameters,
                      world=None,ext='xml',root='.',learning_rate = 1.0,observation_condition='randomize'):
    print("**********************Get Acknowledgment*******************")
            #For Q-Value CSV File
    outputFile="./media/qvalue/"+str(username)+"/qvalue.csv"
    if world is None:
        # Get the world from the scenario file
        filename = getFilename(username,level,ext,root)
        world = World(filename)
    oldVector = world.state
    # print(oldVector)

    robotIndex = symbol2index(location,level)
    beliefs = {'B_waypoint': WAYPOINTS[level][robotIndex]['name']}
    if recommendation == 'unprotected' and danger != 'none':
        # Robot mistakenly thought it was safe
        error = False
    elif recommendation == 'protected' and danger == 'none':
        # Robot mistakenly thought it was dangerous
        error = True
    elif recommendation != 'none':
        # Robot was right
        error = None
    else:
        # Robot didn't say anything, so not it's problem
        error = None
    learning = world.getFeature('robot\'s learning')
    assert len(learning) == 1,'Unable to have uncertain setting for learning'
    learning = learning.first()
    ack = ''
    robot = world.agents['robot']
    move = Action({'subject': robot.name,
                   'verb': 'moveto',
                   'object': location})
    if learning == 'model-free':
        robot = world.agents['robot']
        # Q Learning
        # Gamma not used
        #Learning rate
        LR = learning_rate
        copy_old_table = copy.deepcopy(robot.table)
        enter_flag = 0
        dummy_placeholder = 0.2
        global file
        if recommendation == 'protected':
            if danger != 'none':
                with open(outputFile, 'a+') as file:
                    file.write("Robot recommended Protected Gear and danger was present. Hence recommendation is correct.\n")
                robot.table[omega2index(robot.prev_state)][0] = robot.table[omega2index(robot.prev_state)][0] + LR*(20-60*(0.25))
                robot.old_decision[omega2index(robot.prev_state)].append('correct')
            if danger == 'none':
                with open(outputFile, 'a+') as file:
                    file.write("Robot recommended Protected Gear and danger was none. Hence recommendation is incorrect.\n")
                # Have to handle this case a better way
                robot.table[omega2index(robot.prev_state)][0] = max(dummy_placeholder,robot.table[omega2index(robot.prev_state)][0] + LR*(20-60*(0.25) - (10) )) # The -10 is for recommending protected when there is no danger
                robot.old_decision[omega2index(robot.prev_state)].append('delay')
        elif recommendation == 'unprotected' and danger != 'none':
            with open(outputFile, 'a+') as file:
                file.write("Robot recommended Unprotected and danger was present. Hence recommendation is incorrect.\n")
            enter_flag = 1
            robot.table[omega2index(robot.prev_state)][1] = max(dummy_placeholder,robot.table[omega2index(robot.prev_state)][1] + LR*(-12))
            robot.old_decision[omega2index(robot.prev_state)].append('died')
        elif recommendation == 'unprotected' and danger == 'none':
            with open(outputFile, 'a+') as file:
                file.write("Robot recommended Unprotected and danger was none. Hence recommendation is correct.\n")
            robot.table[omega2index(robot.prev_state)][1] = robot.table[omega2index(robot.prev_state)][1] + LR*(20)
            robot.old_decision[omega2index(robot.prev_state)].append('correct')
        robot.old_decision[omega2index(robot.prev_state)].append(list(robot.table[omega2index(robot.prev_state)]))

        Vold = copy_old_table[omega2index(robot.prev_state)]
        Vtotal = sum(Vold)
        probs_old = [V/Vtotal for V in Vold]
        Vnew = robot.table[omega2index(robot.prev_state)]
        Vtotal = sum(Vnew)
        probs_new = [V/Vtotal for V in Vnew]
#        probs_old = np.array(np.array(copy_old_table[omega2index(robot.prev_state)])/sum(np.array(copy_old_table[omega2index(robot.prev_state)])))
#        probs_new = np.array(np.array(robot.table[omega2index(robot.prev_state)])/sum(np.array(robot.table[omega2index(robot.prev_state)])))
        if user is None:
            with open(outputFile, 'a+') as file:
                file.write("Human chose action "+recommendation)
            action = Action({'subject': 'robot',
                             'verb': 'recommend %s' % (recommendation),
                             'object': location})
        else:
            if user:
                action = Action({'subject': 'robot',
                                 'verb': 'recommend %s' % ('protected'),
                                 'object': location})
                if recommendation=='protected':
                    with open(outputFile, 'a+') as file:
                        file.write("Human follwed robot's recommendation")
                else:
                    with open(outputFile, 'a+') as file:
                        file.write("Human did not follow robot's recommendation")
                with open(outputFile, 'a+') as file:
                    file.write(" and chose action protected")
            else:
                action = Action({'subject': 'robot',
                                 'verb': 'recommend %s' % ('unprotected'),
                                 'object': location})
                if recommendation=='unprotected':
                    with open(outputFile, 'a+') as file:
                        file.write("Human followed robot's recommendation")
                else:
                    with open(outputFile, 'a+') as file:
                        file.write("Human did not follow robot's recommendation")
                with open(outputFile, 'a+') as file:
                    file.write(" and chose action unprotected")
        print (action)
        world.step(action,select=True)
        ack += Template(TEMPLATES['acknowledgment'][robot.old_decision[omega2index(robot.prev_state)][3]]).safe_substitute({'waypoint':robot.old_decision[omega2index(robot.prev_state)][2]})
        if len(WAYPOINTS[level])-1 == robotIndex:
            t = robot.table
            for key in t:
                omega = dict(key)
                if omega['microphone'] == 'suspicious' and omega['camera'] == False:
                    if t[key][0] > t[key][1]:
                        sensor1 = 'microphone'
                        sensor2 = 'camera'
                    else:
                        sensor2 = 'microphone'
                        sensor1 = 'camera'
            ack += Template(TEMPLATES['convince']['sensor reliability']).substitute({'sensor1':sensor1,'sensor2':sensor2})
        ack += Template(TEMPLATES['acknowledgment']['required']).safe_substitute()
        dec = {True:'more',False:'less'}
        ack += Template(TEMPLATES['acknowledgment']['always']).substitute({'compare': dec[probs_new[1] - probs_old[1] > 0]})

        # if enter_flag == 0:
        #     ack += 'I have reinforced my action probabilities\n'
        #     # print ('I have reinforced my action probabilities')
        # else:
        #     ack += 'I have changed my action probabilities drastically to avoid error\n'
            # print ('I have changed my action probabilities drastically to avoid error')
        # ack += 'The old decision probabilities were: '+str(probs_old)+'\n'
        # ack += 'The update/new decision probabilities are: '+str(probs_new) +'\n'
        # print ('The old decision probabilities were:',probs_old)
        # print ('The update/new decision probabilities are:',probs_new)
    else:
        if learning == 'model-based':         # Let's learn!
            model = world.getModel(robot.name)
            assert len(model) == 1
            model = model.first()
            danger_dict = {}
            print(location + "'s old danger readings")
            for i in iter(robot.getBelief(world.state, model)[location + "'s danger"]._domain):
                print(world.symbolList[int(float(i) + 0.1)],(robot.getBelief(world.state, model)[location + "'s danger"][i]))
                danger_dict[world.symbolList[int(float(i) + 0.1)]] = robot.getBelief(world.state, model)[location + "'s danger"][i]
            # print(danger_dict)
            WriteLogData('Old_Danger Prob: %s' % str(danger_dict), username, level, root=root)
            alpha = 0.1
            # print(robot.getO())
            print("\nRobot's old observation probabilities")
            obs_prob = show_O(world, robot, move)
            WriteLogData('Old_Observation Prob: %s' % str(obs_prob), username, level, root=root)
            cam_fnProb = world.getFeature('robot\'s cameraFNProb', oldVector)
            assert len(cam_fnProb) == 1
            micro_fnProb = world.getFeature('robot\'s microFNProb', oldVector)
            assert len(micro_fnProb) == 1
            nbc_fnProb = world.getFeature('robot\'s nbcFNProb', oldVector)
            assert len(nbc_fnProb) == 1
            cam_fpProb = world.getFeature('robot\'s cameraFPProb', oldVector)
            assert len(cam_fpProb) == 1
            micro_fpProb = world.getFeature('robot\'s microFPProb', oldVector)
            assert len(micro_fpProb) == 1
            nbc_fpProb = world.getFeature('robot\'s nbcFPProb', oldVector)
            assert len(nbc_fpProb) == 1
            cam_fnProb = cam_fnProb.first()
            cam_fpProb = cam_fpProb.first()
            micro_fnProb = micro_fnProb.first()
            micro_fpProb = micro_fpProb.first()
            nbc_fnProb = nbc_fnProb.first()
            nbc_fpProb = nbc_fpProb.first()
            if recommendation == 'protected':
                if danger != 'none':
                    with open(outputFile, 'a+') as file:
                        file.write("Robot recommended Protected Gear and danger was present. Hence recommendation is correct.\n")
                    ack += Template(TEMPLATES['acknowledgment']['correct']).substitute(
                        {'waypoint': WAYPOINTS[level][robotIndex]['name']})
                elif danger == 'none':
                    with open(outputFile, 'a+') as file:
                        file.write("Robot recommended Protected Gear and danger was none. Hence recommendation is incorrect.\n")
                    # Have to handle this case a better way
                    ack += Template(TEMPLATES['ack_learning']['always']).substitute(
                        {'B_waypoint': WAYPOINTS[level][robotIndex]['name']})
            elif recommendation == 'unprotected' and danger != 'none':
                with open(outputFile, 'a+') as file:
                    file.write("Robot recommended Unprotected and danger was present. Hence recommendation is incorrect.\n")
                ack += Template(TEMPLATES['ack_learning']['always']).substitute(
                    {'B_waypoint': WAYPOINTS[level][robotIndex]['name']})
            elif recommendation == 'unprotected' and danger == 'none':
                with open(outputFile, 'a+') as file:
                    file.write("Robot recommended Unprotected and danger was none. Hence recommendation is correct.\n")
                ack += Template(TEMPLATES['acknowledgment']['correct']).substitute(
                    {'waypoint': WAYPOINTS[level][robotIndex]['name']})
            ack += Template(TEMPLATES['acknowledgment']['required']).safe_substitute()
            if world.getFeature('%s\'s danger' % (location),oldVector).get('armed') > 0.5:
                # Armed gunman was there
                old = cam_fnProb
                if world.getFeature('robot\'s camera',oldVector).get(False) > 0.5:
                    # False negative!
                    cam_fnProb = min((1. - alpha) * cam_fnProb + alpha,1.0)
                else:
                    cam_fnProb = max((1. - alpha) * cam_fnProb,0.)
                ack += Template(TEMPLATES['ack_learning']['update_info_cam_neg']).substitute({'old_val':old,'new_val':cam_fnProb, })
                world.setFeature('robot\'s cameraFNProb', cam_fnProb)

                old = micro_fnProb
                if world.getFeature('robot\'s microphone',oldVector).get('suspicious') < 0.5:
                    # False negative!
                    micro_fnProb = min((1. - alpha) * micro_fnProb + alpha,1.0)
                else:
                    micro_fnProb = max((1. - alpha) * micro_fnProb,0.)
                ack += Template(TEMPLATES['ack_learning']['update_info_micro_neg']).substitute({'old_val':old,'new_val':micro_fnProb, })
                world.setFeature('robot\'s microFNProb', micro_fnProb)

                old = nbc_fpProb
                if world.getFeature('robot\'s NBCsensor', oldVector).get(False) < 0.5:
                    # False positive!
                    nbc_fpProb = min((1. - alpha) * nbc_fpProb + alpha, 1.0)
                else:
                    nbc_fpProb = max((1. - alpha) * nbc_fpProb, 0.)
                ack += Template(TEMPLATES['ack_learning']['update_info_nbc_pos']).substitute(
                    {'old_val': old, 'new_val': nbc_fpProb, })
                world.setFeature('robot\'s nbcFPProb', nbc_fpProb)

                for waypoint in WAYPOINTS[level][robotIndex+1:]:
                    symbol = waypoint['symbol']
                    action = ActionSet(Action({'subject': 'robot','verb': 'moveto',
                                               'object': symbol}))
                    tree = makeTree(generateCameraO(world, stateKey(symbol,'danger'),
                                                    falseNeg=cam_fnProb,falsePos=cam_fpProb))
                    world.agents['robot'].setO('camera',action,tree)
                    tree = makeTree(generateMicO(world, stateKey(symbol, 'danger'),
                                                    falseNeg=micro_fnProb, falsePos=micro_fpProb))
                    world.agents['robot'].setO('microphone', action, tree)
                    tree = makeTree(generateNBCO(world, stateKey(symbol, 'danger'),
                                                    falseNeg=nbc_fnProb, falsePos=nbc_fpProb))
                    world.agents['robot'].setO('NBCsensor', action, tree)
            elif world.getFeature('%s\'s danger' % (location),oldVector).get('NBC') > 0.5:
                # Armed gunman was there
                old = cam_fpProb
                if world.getFeature('robot\'s camera', oldVector).get(False) < 0.5:
                    # False positive!
                    cam_fpProb = min((1. - alpha) * cam_fpProb + alpha, 1.0)
                else:
                    cam_fpProb = max((1. - alpha) * cam_fpProb, 0.)
                ack += Template(TEMPLATES['ack_learning']['update_info_cam_pos']).substitute(
                    {'old_val': old, 'new_val': cam_fpProb, })
                world.setFeature('robot\'s cameraFPProb', cam_fpProb)

                old = micro_fpProb
                if world.getFeature('robot\'s microphone', oldVector).get('suspicious') > 0.5:
                    # False positive!
                    micro_fpProb = min((1. - alpha) * micro_fpProb + alpha, 1.0)
                else:
                    micro_fpProb = max((1. - alpha) * micro_fpProb, 0.)
                ack += Template(TEMPLATES['ack_learning']['update_info_micro_pos']).substitute(
                    {'old_val': old, 'new_val': micro_fpProb, })
                world.setFeature('robot\'s microFPProb', micro_fpProb)

                old = nbc_fnProb
                if world.getFeature('robot\'s NBCsensor',oldVector).get(False) > 0.5:
                    # False negative!
                    nbc_fnProb = min((1. - alpha) * nbc_fnProb + alpha,1.0)
                else:
                    nbc_fnProb = max((1. - alpha) * nbc_fnProb,0.)
                ack += Template(TEMPLATES['ack_learning']['update_info_nbc_neg']).substitute({'old_val':old,'new_val':nbc_fnProb, })
                world.setFeature('robot\'s nbcFNProb', nbc_fnProb)

                for waypoint in WAYPOINTS[level][robotIndex+1:]:
                    symbol = waypoint['symbol']
                    action = ActionSet(Action({'subject': 'robot','verb': 'moveto',
                                               'object': symbol}))
                    tree = makeTree(generateCameraO(world, stateKey(symbol,'danger'),
                                                    falseNeg=cam_fnProb,falsePos=cam_fpProb))
                    world.agents['robot'].setO('camera',action,tree)
                    tree = makeTree(generateMicO(world, stateKey(symbol, 'danger'),
                                                    falseNeg=micro_fnProb, falsePos=micro_fpProb))
                    world.agents['robot'].setO('microphone', action, tree)
                    tree = makeTree(generateNBCO(world, stateKey(symbol, 'danger'),
                                                    falseNeg=nbc_fnProb, falsePos=nbc_fpProb))
                    world.agents['robot'].setO('NBCsensor', action, tree)

            else:
                # No armed gunman was there
                old = cam_fpProb
                if world.getFeature('robot\'s camera', oldVector).get(False) < 0.5:
                    # False positive!
                    cam_fpProb = min((1. - alpha) * cam_fpProb + alpha,1.0)
                else:
                    cam_fpProb = max((1. - alpha) * cam_fpProb,0.)
                ack += Template(TEMPLATES['ack_learning']['update_info_cam_pos']).substitute(
                    {'old_val': old, 'new_val': cam_fpProb, })
                world.setFeature('robot\'s cameraFPProb', cam_fpProb)

                old = micro_fpProb
                if world.getFeature('robot\'s microphone', oldVector).get('suspicious') > 0.5:
                    # False positive!
                    micro_fpProb = min((1. - alpha) * micro_fpProb + alpha,1.0)
                else:
                    micro_fpProb = max((1. - alpha) * micro_fpProb,0.)
                ack += Template(TEMPLATES['ack_learning']['update_info_micro_pos']).substitute(
                    {'old_val': old, 'new_val': micro_fpProb, })
                world.setFeature('robot\'s microFPProb', micro_fpProb)

                old = nbc_fpProb
                if world.getFeature('robot\'s NBCsensor', oldVector).get(False) < 0.5:
                    # False positive!
                    nbc_fpProb = min((1. - alpha) * nbc_fpProb + alpha,1.0)
                else:
                    nbc_fpProb = max((1. - alpha) * nbc_fpProb,0.)
                ack += Template(TEMPLATES['ack_learning']['update_info_nbc_pos']).substitute(
                    {'old_val': old, 'new_val': nbc_fpProb, })
                world.setFeature('robot\'s nbcFPProb', nbc_fpProb)

                for waypoint in WAYPOINTS[level][robotIndex:]:
                    if not 'symbol' in waypoint:
                        waypoint['symbol'] = waypoint['name'].replace(' ', '')
                    symbol = waypoint['symbol']
                    action = ActionSet(Action({'subject': 'robot', 'verb': 'moveto',
                                               'object': symbol}))
                    tree = makeTree(generateCameraO(world, stateKey(symbol, 'danger'),
                                                    falseNeg=cam_fnProb, falsePos=cam_fpProb))
                    world.agents['robot'].setO('camera', action, tree)
                    # print(tree)
                    tree = makeTree(generateMicO(world, stateKey(symbol, 'danger'),
                                                 falseNeg=micro_fnProb, falsePos=micro_fpProb))
                    world.agents['robot'].setO('microphone', action, tree)
                    # print(tree)
                    tree = makeTree(generateNBCO(world, stateKey(symbol, 'danger'),
                                                 falseNeg=nbc_fnProb, falsePos=nbc_fpProb))
                    world.agents['robot'].setO('NBCsensor', action, tree)
                    # print(tree)
            print("\nRobot's new observation probabilities")
            obs_prob = show_O(world, robot, move)
            WriteLogData('New_Observation Prob: %s' % str(obs_prob), username, level, root=root)
            # exit()
        if user is None:
            with open(outputFile, 'a+') as file:
                file.write("Human chose action "+recommendation)
            action = Action({'subject': 'robot',
                             'verb': 'recommend %s' % (recommendation),
                             'object': location})
        else:
            print ('User action is not None')
            alpha = 0.1
            humanProbUnprot = world.getFeature('robot\'s humanProbUnprotected', oldVector)
            assert len(humanProbUnprot) == 1
            humanProbUnprot = humanProbUnprot.first()
            old_unprot = humanProbUnprot
            humanProbProt = world.getFeature('robot\'s humanProbProtected', oldVector)
            assert len(humanProbProt) == 1
            humanProbProt = humanProbProt.first()
            old_prot = humanProbProt
            if user:
                action = Action({'subject': 'robot',
                                 'verb': 'recommend %s' % ('protected'),
                                 'object': location})
                if recommendation=='protected':
                    with open(outputFile, 'a+') as file:
                        file.write("Human follwed robot's recommendation")
                    humanProbProt = min((1. - alpha) * humanProbProt + alpha,1.0)
                    ack += Template(TEMPLATES['ack_learning']['update_human_prob_prot']).substitute(
                        {'old_val': old_unprot, 'new_val': humanProbProt, })
                    world.setFeature('robot\'s humanProbProtected', humanProbProt)
                else:
                    with open(outputFile, 'a+') as file:
                        file.write("Human did not follow robot's recommendation")
                    humanProbUnprot = max((1. - alpha) * humanProbUnprot,0.)
                    ack += Template(TEMPLATES['ack_learning']['update_human_prob_unprot']).substitute(
                        {'old_val': old_prot, 'new_val': humanProbUnprot, })
                    world.setFeature('robot\'s humanProbUnprotected', humanProbUnprot)
                with open(outputFile, 'a+') as file:
                    file.write(" and chose action protected")
            else:

                action = Action({'subject': 'robot',
                                 'verb': 'recommend %s' % ('unprotected'),
                                 'object': location})
                if recommendation=='unprotected':
                    with open(outputFile, 'a+') as file:
                        file.write("Human followed robot's recommendation")
                    humanProbUnprot = min((1. - alpha) * humanProbUnprot + alpha,1.0)
                    ack += Template(TEMPLATES['ack_learning']['update_human_prob_unprot']).substitute(
                        {'old_val': old_prot, 'new_val': humanProbUnprot, })
                    world.setFeature('robot\'s humanProbUnprotected', humanProbUnprot)
                else:
                    with open(outputFile, 'a+') as file:
                        file.write("Human did not follow robot's recommendation")
                    humanProbProt = max((1. - alpha) * humanProbProt,0.)
                    ack += Template(TEMPLATES['ack_learning']['update_human_prob_prot']).substitute(
                        {'old_val': old_unprot, 'new_val': humanProbProt, })
                    world.setFeature('robot\'s humanProbProtected', humanProbProt)
                with open(outputFile, 'a+') as file:
                    file.write(" and chose action unprotected")



        assert len(world.getModel('robot')) == 1
        world.step(action,select=True)
        assert len(world.getModel('robot')) == 1
        beliefState = list(world.agents['robot'].getBelief().values())[0]
        belief = world.getState(location,'danger',beliefState)
        # print(belief)
        # exit()
        real = world.getState(location,'danger')
        assert len(real) == 1
        assert len(belief) == 1
        assert real.first() == belief.first()
#    if world.getState('robot','acknowledgment').first() == 'yes':
#        ack = Template(TEMPLATES['acknowledgment'][error]).substitute(beliefs)
#    else:
#        ack = ''
    # Did the user die?
    death = not world.getState('human','alive').first()
    if death:
        with open(outputFile, 'a+') as file:
            file.write(". Human died.\n")
    else:
        with open(outputFile, 'a+') as file:
            file.write(". Human survived.\n")

    # if death:
    #     key = stateKey('human','deaths')
    #     old = world.getValue(key)
    #     world.setFeature(key,old+1)
    # world.setState('human','alive',True)
    if world.getState(robot.name,'acknowledgment').first() == 'no':
        ack = ''
    WriteLogData('%s %s %s %s %s %s (%s) (%s)' % \
                 (USER_TAG,user,location,danger,death,
                  WAYPOINTS[level][robotIndex]['image'],
                  WAYPOINTS[level][robotIndex]['comment'],ack),
                 username,level,root)
    filename = getFilename(username,level,ext,root)
    with open(filename,'wb') as scenarioFile:
        pickle.dump(world,scenarioFile)
#    world.save(filename,ext=='psy')
    if learning == "model-based":
        state = pickle.loads(pickle.dumps(world.state))
        new_robotIndex = symbol2index(location, level)
        new_robotWaypoint = WAYPOINTS[level][new_robotIndex]
        move = Action({'subject': robot.name,
                       'verb': 'moveto',
                       'object': location})
        world.step(move)
        key = stateKey(new_robotWaypoint['symbol'], 'danger')
        ability = robot.getState('ability').domain()[0]
        if ability == 'badSensor':
            sensorCorrect = False
        else:
            sensorCorrect = True
        # Generate individual sensor readings
        omega = {}
        nullReading = {'camera': False, 'microphone': 'nobody', 'NBCsensor': False}
        readings = {'camera': [True, False], 'microphone': ['suspicious', 'friendly', 'nobody'],
                    'NBCsensor': [True, False]}

        if new_robotIndex in robot.random_indices:
            randomizing_flag = True
            pick_sensor = np.random.choice(['microphone', 'camera'], p=[0.5, 0.5])
        else:
            randomizing_flag = False
        danger = world.getFeature(key, world.state)
        for sensor in robot.omega:
            if observation_condition == 'scripted':
                # print('Using scripted readings')
                if sensor in new_robotWaypoint:
                    # print("in")
                    omega[sensor] = new_robotWaypoint[sensor][sensorCorrect]
                    # print(sensor, robotWaypoint[sensor][sensorCorrect])
                else:
                    omega[sensor] = nullReading[sensor]
                    # print(sensor, nullReading[sensor])
            else:
                # if randomize then sample a value from readings with given distribution
                if sensor in new_robotWaypoint:
                    actual = new_robotWaypoint[sensor][True]
                else:
                    actual = nullReading[sensor]

                if randomizing_flag:
                    # print('Using randomized readings', pick_sensor)
                    if sensor == 'microphone' and sensor == pick_sensor:
                        if actual == 'suspicious':
                            omega[sensor] = np.random.choice(['friendly', 'nobody'], p=[0.5, 0.5])
                        else:
                            omega[sensor] = 'suspicious'
                    elif sensor == 'camera' and sensor == pick_sensor:
                        assert isinstance(actual, bool)
                        omega[sensor] = not actual
                    else:
                        omega[sensor] = actual
                else:
                    # print('Using actual readings')
                    omega[sensor] = actual
            omegaKey = stateKey(robot.name, sensor)
            world.getFeature(omegaKey)
            world.state[omegaKey] = world.value2float(omegaKey, omega[sensor])
        new_model = world.getModel(robot.name)
        assert len(new_model) == 1
        new_model = new_model.first()
        # print(new_robot.getBelief(new_world.state, new_model).keyMap)
        # for obs in new_robot.omega:
        #     print(obs)
        #     for i in iter(new_robot.getBelief(new_world.state, new_model)["robot's "+str(obs)]._domain):
        #         print(new_world.symbolList[int(float(i) + 0.1)],
        #               (new_robot.getBelief(new_world.state, new_model)["robot's "+str(obs)][i]))
        # exit()
        print(location + "'s new danger readings")
        danger_dict = {}
        for i in iter(robot.getBelief(world.state, new_model)[location + "'s danger"]._domain):
            print(world.symbolList[int(float(i) + 0.1)],
                  (robot.getBelief(world.state, new_model)[location + "'s danger"][i]))
            danger_dict[world.symbolList[int(float(i) + 0.1)]] = \
            robot.getBelief(world.state, new_model)[location + "'s danger"][i]
        # print(danger_dict)
        WriteLogData('New_Danger Prob: %s' % str(danger_dict), username, level, root=root)
        # decision = new_robot.decide(new_world.state, model=new_model)
        # print(decision)
        world.state = state

    return ack

def GetRecommendation(username,level,parameters,world=None,ext='xml',root='.',sleep=None,observation_condition='randomize'):
    """
    Processes incoming observation and makes an assessment
    """

    print("**********************Get Recommendation********************")
    temp_flag = ''
    if sleep:
        time.sleep(sleep)
    filename = getFilename(username,level,ext,root)
    if world is None:
        # Get the world from the scenario file
        world = World(filename)
    oldVector = world.state
    learning = world.getFeature('robot\'s learning')
    assert len(learning) == 1,'Unable to have uncertain setting for learning'
    learning = learning.first()

    robot = world.agents['robot']

    if 'robotWaypoint' in parameters:
        # Project world state
        robotIndex = int(parameters['robotWaypoint'])
        robotWaypoint = WAYPOINTS[level][robotIndex]
        if not 'symbol' in robotWaypoint:
            robotWaypoint['symbol'] = robotWaypoint['name'].replace(' ','')
        world.setState(robot.name,'waypoint',robotWaypoint['symbol'])
    else:
        # Read world state
        robotIndex = symbol2index(world.getState(robot.name,'waypoint').domain()[0],level)
        robotWaypoint = WAYPOINTS[level][robotIndex]
        if not 'symbol'in robotWaypoint:
            robotWaypoint['symbol'] = robotWaypoint['name'].replace(' ','')
    move = Action({'subject': robot.name,
                     'verb': 'moveto',
                     'object': robotWaypoint['symbol']})
    # # print(move)
    # # print(ActionSet(move))
    # # print(robot.O)
    # mtree = robot.O["robot's microphone"][ActionSet(move)]
    # # print(mtree)
    # # print(mtree.getKeysIn())
    # # print(mtree.getKeysOut())
    # expressed_tree =tree_decode(mtree)
    # # print(expressed_tree)
    # # print(world.variables)
    # # print(mtree._string)
    # # print(world.symbolList[int(float(5)+0.1)])
    # # # exit()
    # # print(world.float2value("robot's microphone",263))
    # words = re.split(' |\*',expressed_tree)
    # for word in range(len(words)):
    #     if '\n' in words[word]:
    #         new_words = words[word].split('\n')
    #         if new_words[0].isdigit():
    #             if '.' not in new_words[0]:
    #                 words[word] = str(world.symbolList[int(float(new_words[0])+0.1)]) + words[word][len(new_words[0]):]
    #     elif words[word].isdigit():
    #         if '.' not in words[word]:
    #             words[word] = world.symbolList[int(float(words[word])+0.1)]
    # print(" ".join(words))

    # print(robot.omega)

    # mtree = robot.O["robot's microphone"][ActionSet(move)]
    # print(tree_decode(mtree))
    # exit()
    world.step(move)
    # Process scripted observations
    key = stateKey(robotWaypoint['symbol'],'danger')
    ability = robot.getState('ability').domain()[0]
    if ability == 'badSensor':
        sensorCorrect = False
    else:
        sensorCorrect = True
    # Generate individual sensor readings
    omega = {}
    nullReading = {'camera': False,'microphone': 'nobody','NBCsensor': False}
    readings = {'camera':[True,False],'microphone':['suspicious','friendly','nobody'],'NBCsensor':[True,False]}

    if robotIndex in robot.random_indices:
        randomizing_flag = True
        pick_sensor = np.random.choice(['microphone','camera'],p=[0.5,0.5])
    else:
        randomizing_flag = False
    # distrib = {'camera':[0.85,0.15],'microphone':[0.9,0.05,0.05],'NBCsensor':[0.95,0.05]}
    danger = world.getFeature(key,world.state)
    for sensor in robot.omega:
        if observation_condition == 'scripted':
            print('Using scripted readings')
            if sensor in robotWaypoint:
                # print("in")
                omega[sensor] = robotWaypoint[sensor][sensorCorrect]
                # print(sensor, robotWaypoint[sensor][sensorCorrect])
            else:
                omega[sensor] = nullReading[sensor]
                # print(sensor, nullReading[sensor])
        else:
            # if randomize then sample a value from readings with given distribution
            if sensor in robotWaypoint:
                actual = robotWaypoint[sensor][True]
            else:
                actual = nullReading[sensor]

            if randomizing_flag:
                print('Using randomized readings', pick_sensor)
                if sensor == 'microphone' and sensor == pick_sensor:
                    if actual == 'suspicious':
                        omega[sensor] = np.random.choice(['friendly','nobody'],p=[0.5,0.5])
                    else:
                        omega[sensor] = 'suspicious'
                elif sensor == 'camera' and sensor == pick_sensor:
                    assert isinstance(actual,bool)
                    omega[sensor] = not actual
                else:
                    omega[sensor] = actual
                # actual_ind = readings[sensor].index(actual)
                # lis = []
                # len_val = len(readings[sensor])
                # for _ in range(len_val):
                #     lis.append(readings[sensor][(actual_ind+_)%len_val])
                # omega[sensor] = np.random.choice(lis,p=distrib[sensor])
                # print('actual:',actual,'randomized:',omega[sensor],'list:',lis)
            else:
                print ('Using actual readings')
                omega[sensor] = actual


        # except KeyError:
        #     if observation_condition == 'scripted':
        #         # By default, don't sense anything
        #         if sensor == 'microphone':
        #             omega[sensor] = 'nobody'
        #         else:
        #             omega[sensor] = False
        #     else:
        #         print('Using randomized readings2')
        #         # if randomize then sample a value from readings with given distribution
        #         if sensor == 'microphone':
        #             actual = 'nobody'
        #         else:
        #             actual = False
        #         actual_ind = readings[sensor].index(actual)
        #         lis = []
        #         len_val = len(readings[sensor])
        #         for _ in range(len_val):
        #             lis.append(readings[sensor][(actual_ind+_)%len_val])
        #         omega[sensor] = np.random.choice(lis,p=distrib[sensor])
        #         print('actual:',actual,'randomized:',omega[sensor],'list:',lis)

        omegaKey = stateKey(robot.name,sensor)
        world.state[omegaKey] = world.value2float(omegaKey,omega[sensor])
    model = world.getModel(robot.name)
    assert len(model) == 1
    model = model.first()
    WriteLogData('NBC sensor: %s' % (omega['NBCsensor']),username,level,root=root)
    WriteLogData('Camera: %s' % (omega['camera']),username,level,root=root)
    WriteLogData('Microphone: %s' % (omega['microphone']),username,level,root=root)

    #For Q-Value CSV File
    outputFile = "./media/qvalue/"+str(username)+"/qvalue.csv"
    with open(outputFile, 'a+') as f:
        f.write("\nThe sensor readings are Microphone-> "+str(omega['microphone'])+" NBC Sensor-> "+str(omega['NBCsensor'])+" camera-> "+str(omega['camera'])+"\n")

    # Get robot's beliefs
    loc = stateKey(robot.name,'waypoint')
    # Use explicit beliefs
    beliefs = robot.getBelief(world.state)
    assert len(beliefs) == 1
    model = world.getModel(robot.name)
    assert len(model) == 1
    model = model.first()

    assessment = world.getFeature(key,beliefs[model])
    for danger in assessment.domain():
        WriteLogData('Posterior belief in %s: %d%%' % (danger,assessment[danger]*100.),
                     username,level,root=root)
    # Which recommendation is better? 
    decision = robot.decide(world.state,model=model)
    # print((robot.getBelief(world.state,model)[robotWaypoint['symbol']+"'s danger"]))
    # print(world.symbolList[int(float(260) + 0.1)])
    # exit()
    # print(decision['action']['verb'])
    # R = robot.getReward(model)
    # subset = set(R.getKeysIn()) - {CONSTANT}
    # R.children[None].makeFuture()
    explanation = ''
    projection = {}
    if learning == 'model-free':
        global file
        dict_temps = {}
        robot.prev_state = omega
        values_predicted = robot.table[omega2index(omega)]
        print(values_predicted)
        action_predicted = argmax(values_predicted)
        act_verbs = ['unsafe','safe']
        diff_dict = {False:'higher',True:'lower'}

        # print (action_predicted)
        if omega2index(omega) in robot.old_decision:
            temp_dict = {'waypoint':robot.old_decision[omega2index(omega)][2],
                         'Action':act_verbs[argmax(robot.old_decision[omega2index(omega)][0])],
                         'Confidence':int(round(100*robot.old_decision[omega2index(omega)][1]))}
            copy_omega = dict(omega)
            for key_ in copy_omega:
                temp_dict[key_] = copy_omega[key_]
            explanation += Template(TEMPLATES['convince']['sensors'][temp_dict['microphone']][temp_dict['camera']][temp_dict['NBCsensor']]).safe_substitute()
            explanation += Template(TEMPLATES['convince']['always']).safe_substitute(temp_dict)
            temp_flag = ' now'
            # print (omega)
            # print (robotWaypoint['symbol'])
            # print ('I predicted', act_verbs[argmax(robot.old_decision[str(omega)][0])] ,'the last time.')
            # if robot.old_decision[str(omega)][1] == 'delay':
            #     print ('The actual state had no danger but caused delay. I updated my belief and also reliability of sensors.')
            # elif robot.old_decision[str(omega)][1] == 'died':
            #     print ('The actual state had danger and you were killed . I updated my belief drastically.')
            # else:
            #     print ('The previous action chosen was optimal. Hence, I became more confident with my prediction.')
            # print ('Assertion',robot.table[omega2index(omega)] == robot.old_decision[omega2index(omega)][4])
            upd_dict = {'diff':diff_dict[(robot.old_decision[omega2index(omega)][0][1]-robot.table[omega2index(omega)][1])>0],'waypoint':robotWaypoint['name']}
            explanation += Template(TEMPLATES['convince'][robot.old_decision[omega2index(omega)][3]]).safe_substitute(upd_dict)
        conf = values_predicted[action_predicted]/sum(values_predicted)
        robot.old_decision[omega2index(omega)] = [list(values_predicted),conf,str(robotWaypoint['name'])]


        # print ('confidence of decision:',values_predicted[action_predicted]/sum(values_predicted))
        dict_temps['Confidence'] = int(round(100*conf))
        dict_temps['waypoint'] = robotWaypoint['symbol']
        # return action_predicted
        actions_values = {}
        actions_values['recommend protected'] = values_predicted[0]
        actions_values['recommend unprotected'] = values_predicted[1]

        if action_predicted == 0:
            WriteLogData('Decision_MFree: recommend protected\n'+'Values: '+str(values_predicted)+',Confidence: '+str(values_predicted[action_predicted]/sum(values_predicted))+'\n',username,level,root=root)
            act = {}
            act['subject'] = decision['action']['subject']
            act['object'] = decision['action']['object']
            act['verb'] = 'recommend protected'
            decision['action'] = Action(act)

        else:
            WriteLogData('Decision_MFree: recommend unprotected\n'+'Values: '+str(values_predicted)+',Confidence: '+str(values_predicted[action_predicted]/sum(values_predicted))+'\n',username,level,root=root)
            act = {}
            act['subject'] = decision['action']['subject']
            act['object'] = decision['action']['object']
            act['verb'] = 'recommend unprotected'
            decision['action'] = Action(act)


        #Some code for integration of model based and model free
        decision['V*'] = max(values_predicted)
        for action in decision['V']:
            decision['V'][action]['__EV__'] = actions_values[action['verb']]
            decision['V'][action]['__S__'] = None
            decision['V'][action]['__beliefs__'] = None
    for action in sorted(decision['V']):
    #     effect = world.deltaState(action,beliefs[model],subset)
    #     assert len(effect) == 1,'Unable to multiply trees right now'
    #     for dynamics in effect:
    #         total = None
    #         remaining = set(subset)
    #         for key,tree in dynamics.items():
    #             if tree:
    #                 assert len(tree) == 1
    #                 remaining.remove(key)
    #                 if total is None:
    #                     total = tree[0]
    #                 else:
    #                     total += tree[0]
    #         for key in remaining:
    #             tree = makeTree(noChangeMatrix(key))
    #             total += tree
    #         cumulative = total
    #     projection[action] =  R*cumulative
        WriteLogData('%s of %s: %4.2f' % (VALUE_TAG,action['verb'],
                                          decision['V'][action]['__EV__']),
                     username,level,root=root)
#    action1,action2 = projection.keys()
#    difference = projection[action1]+(projection[action2]*-1.)
    # Package up the separate components of my current model
    humanProbUnprot = world.getFeature('robot\'s humanProbUnprotected', oldVector)
    assert len(humanProbUnprot) == 1
    humanProbUnprot = humanProbUnprot.first()
    humanProbProt = world.getFeature('robot\'s humanProbProtected', oldVector)
    assert len(humanProbProt) == 1
    humanProbProt = humanProbProt.first()

    POMDP = {}
    # Add Omega_t, my latest observation
    for Omega,observation in omega.items():
        POMDP['omega_%s' % (Omega)] = observation
        O = robot.O[stateKey(robot.name,Omega)][ActionSet(move)]
        omegaKey = stateKey(robot.name,Omega)
        for danger in assessment.domain():
            hypothetical = KeyedVector({key: world.value2float(key,danger),
                                        CONSTANT: 1.})
            distribution = O[hypothetical]*hypothetical
            for vector in distribution.domain():
                if vector[makeFuture(omegaKey)] == world.value2float(omegaKey,observation):
                    prob = distribution[vector]
                    break
            else:
                prob = 0.
            POMDP['O_%s_%s_%s' % (Omega,observation,danger)] = prob
    # Add A_t, my chosen action
    if decision['action']['verb'] == 'recommend unprotected':
        if learning == 'model-based':
            hcm=Template(TEMPLATES['human_compliance_model']['unprotected']).substitute({'prob': str(humanProbUnprot)})
            # "I think the Human Probability of following my action of Unprotected is: "+str(humanProbUnprot)
            print("Human Compliance Model: "+hcm )
            WriteLogData('Human Compliance Model: %s' % hcm, username, level, root=root)    
        POMDP['A'] = 'recommend unprotected'
        safety = True
        world.setState(robotWaypoint['symbol'],'recommendation','unprotected')
        WriteLogData('%s no' % (RECOMMEND_TAG),username,level,root=root)
    else:
        if learning == 'model-based':
            hcm=Template(TEMPLATES['human_compliance_model']['protected']).substitute({'prob': str(humanProbProt)})
            # "I think the Human Probability of following my action of protected gear is: "+str(humanProbProt)
            print("Human Compliance Model: "+hcm)
            WriteLogData('Human Compliance Model: %s' % hcm, username, level, root=root)   
        POMDP['A'] = 'recommend protected'
        safety = False
        world.setState(robotWaypoint['symbol'],'recommendation','protected')
        WriteLogData('%s yes' % (RECOMMEND_TAG),username,level,root=root)
    if learning == 'model-free':
        POMDP['B_waypoint'] = WAYPOINTS[level][symbol2index(world.getState('robot','waypoint').first(),level)]['name']
        if action_predicted == 0:
            # Unsafe! TODO: This is really confidence, not a belif, so should be renamed
            POMDP['B_danger_not_none'] = int(100.*values_predicted[action_predicted]/sum(values_predicted))
        else:
            POMDP['B_danger_none'] = int(100.*values_predicted[action_predicted]/sum(values_predicted))
    else:
        # Add B_t, my current beliefs
        # print(beliefs[model].keys())
        for key in beliefs[model].keys():
            if key != keys.CONSTANT:
                entity = state2agent(key)
                if entity != 'robot' and entity != robotWaypoint['symbol']:
                    continue
                belief = beliefs[model].marginal(key)
                feature = state2feature(key)
                best = belief.max()
                POMDP['B_%s' % (feature)] = world.float2value(key,best)
                if feature == 'waypoint':
                    POMDP['B_%s' % (feature)] = WAYPOINTS[level][symbol2index(POMDP['B_%s' % (feature)],level)]['name']
                POMDP['B_maxprob'] = belief[best]
                for value in belief.domain():
                    pct = int(round(100.*belief[value]))
                    POMDP['B_%s_%s' % (feature,world.float2value(key,value))] = pct
                    POMDP['B_%s_not_%s' % (feature,world.float2value(key,value))] = 100-pct


    # Use fixed explanation
    # TODO: make this a dynamic decision by the robot
    mode = world.getState(robot.name,'explanation').max()
    if mode == 'none':
        mode = ''
    # explanation = explanation.join(explainDecision(safety,POMDP,mode))
    cnt_temp = 0
    for line in explainDecision(safety,POMDP,mode,flag_check=temp_flag):
        if cnt_temp == 0:
            explanation = line+' '+explanation
        else:
            explanation += ' '+line
        cnt_temp+=1
    #pp.pprint(POMDP)
    WriteLogData('%s %s' % (MESSAGE_TAG,explanation),username,level,root=root)

    with open(filename,'wb') as scenarioFile:
        pickle.dump(world,scenarioFile)

    #Why-Not? Explanations
    robotCamera = world.getFeature('robot\'s camera', oldVector).max()
    robotMicrophone = world.getFeature('robot\'s microphone', oldVector).max()
    robotNBC = world.getFeature('robot\'s NBCsensor', oldVector).max()
    recommendation = world.getState(robotWaypoint['symbol'], 'recommendation').first()

    not_recommended = "unprotected" if recommendation == "protected" else "protected"
    why_not = ""
    why_not+=Template(TEMPLATES['why_not_explanation']['header']).substitute({'recommendation': not_recommended})
    
    why_not += " "+Template(TEMPLATES['why_not_explanation']['reasoning1']).substitute({'sensor': "camera",'value':TEMPLATES["why_not_explanation"]["camera_"+str(robotCamera)]})
    why_not += " "+Template(TEMPLATES['why_not_explanation']['reasoning1']).substitute({'sensor': "NBCsensor",'value':TEMPLATES["why_not_explanation"]["NBCsensor_"+str(robotNBC)]})
    why_not += " "+Template(TEMPLATES['why_not_explanation']['reasoning1']).substitute({'sensor': "microphone",'value':TEMPLATES["why_not_explanation"]["microphone_"+str(robotMicrophone)]})
    why_not=why_not[0:len(why_not)-1]

    why_not+=". Also, The robot's danger predictions are as follows:"
    for i in iter(robot.getBelief(world.state, model)[robotWaypoint['symbol'] + "'s danger"]._domain):
        why_not+= " "+Template(TEMPLATES['why_not_explanation']['reasoning2']).substitute({
            'sensor':world.symbolList[int(float(i) + 0.1)],'danger':robot.getBelief(world.state, model)[robotWaypoint['symbol'] + "'s danger"][i]})

    why_not=why_not[0:len(why_not)-1]
    why_not += ". "+Template(TEMPLATES['why_not_explanation']['conclusion']).substitute({
        'recommendation':not_recommended})+"\n"

    print("\nThe recommendation is: {}".format(recommendation))
    print(why_not)
    WriteLogData('{} {}'.format(WHY_NOT_TAG,why_not), username, level, root=root)
    return explanation

def show_O(world,robot,move):
    dic = {}
    for obs in robot.omega:
        print(obs)
        mtree = robot.O["robot's "+ obs][ActionSet(move)]
        expressed_tree = tree_decode(mtree)
        words = re.split(' |\*', expressed_tree)
        for word in range(len(words)):
            if obs == "NBCsensor":
                if len(words[word]) == 3:
                    if words[word] == '1.0':
                        words[word] = "True"
                    elif words[word] == '0.0':
                        words[word] = "False"
            if '\n' in words[word]:
                new_words = words[word].split('\n')
                if new_words[0].isdigit():
                    # if '.' not in new_words[0]:
                    words[word] = str(world.symbolList[int(float(new_words[0]) + 0.1)]) + words[word][
                                                                                          len(new_words[0]):]
            elif words[word].isdigit():
                # if '.' not in words[word]:
                words[word] = world.symbolList[int(float(words[word]) + 0.1)]
        print(" ".join(words))
        dic[obs] = " ".join(words)
        print()
    return dic
def tree_decode(tree):
    new_str = None
    if new_str is None:
        if tree.isLeaf():
            # print("leaf ",str(tree.children[None]))
            new_str = str(tree.children[None])
        elif tree.isProbabilistic():
            # Probabilistic branch
            # print("prob")
            new_str = '\n'.join(
                map(lambda el: '%d%%: %s' % (100. * tree.children[el], tree_decode(el)), tree.children.domain()))
        else:
            # Deterministic branch
            # print("Deterministic")
            if len(tree.branch.planes) == 1 and isinstance(tree.branch.planes[0][1], list):
                thresholds = tree.branch.planes[0][1][:]
                if tree.branch.planes[0][2] < 0:
                    thresholds.append(1.)
                elif tree.branch.planes[0][2] > 0:
                    thresholds.insert(0, 0.)
                children = '\n'.join(['%s\t%s' % (thresholds[value] if isinstance(value, int) else 'Otherwise',
                                                  tree_decode(tree.children[value]).replace('\n', '\n\t'))
                                      for value in tree.children])
            else:
                children = '\n'.join(
                    ['%s\t%s' % (value, tree_decode(tree.children[value]).replace('\n', '\n\t')) for value in tree.children])
            new_str = 'if %s\n%s' % (str(tree.branch), children)

    return new_str

def explainDecision(decision,beliefs,mode,flag_check=''):
    """
    @param decision: the assessment of the safety of the given location (C{True} if safe, C{False} if dangerous)
    @type decision: bool
    @param location: the label of the location to which this recommendation applies
    @type location: str
    @param beliefs: a table of probabilities for the presence of different features at this location
    @type beliefs: strS{->}float
    @param mode: the type of explanation to give
    @type mode: str
    @return: a list of sentences
    @rtype: str[]
    """
    result = []
    result.append(Template(TEMPLATES['general']['desc']).substitute(beliefs))
    result.append(Template(TEMPLATES['decision'][decision]).substitute(beliefs))
    if 'confidence' in mode:
        beliefs['flag'] = flag_check
        result.append(Template(TEMPLATES['confidence'][decision]).substitute(beliefs))
    if 'ability' in mode:
        result.append(Template(TEMPLATES['NBC'][beliefs['omega_NBCsensor']]).substitute(beliefs))
        result.append(Template(TEMPLATES['armed'][beliefs['omega_camera']]).substitute(beliefs))
        result.append(Template(TEMPLATES['microphone'][beliefs['omega_microphone']]).substitute(beliefs))
#        for sensor in ['NBC','armed','microphone']:
#            result.append(Template(TEMPLATES[sensor][beliefs[sensor]]).substitute(beliefs))
    if 'benevolence' in mode:
        result.append(Template(TEMPLATES['benevolence'][decision]).substitute(beliefs))
    return result

def WriteErrorLog(content="",root='.'):
    f = open(os.path.join(root,'ErrorLog.txt'),'a')
    print('[%s] %s' % (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                       content),file=f)
    f.close()

def WriteLogData(content="",username=None,level=None,root='.'):
    """
    (U) Creating logs
    """
    filename = getFilename(username,level,extension='log',root=root)
    # print(filename)
    # exit()
    f = open(filename,'a')
    print('[%s] %s' % (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                       content),file=f)
    f.close()

def readLogData(username,level,root='.'):
    """
    Extracts key events from a log
    """
    filename = getFilename(username,level,extension='log',root=root)
    log = []
    start = None
    for line in fileinput.input(filename):
        elements = line.split()
        # print(elements)
        if len(elements) <= 2:
            # print (elements)
            continue
        if '%s %s' % (elements[2],elements[3]) == RECOMMEND_TAG:
            now = datetime.datetime.strptime('%s %s' % (elements[0][1:],elements[1][:-1]),'%Y-%m-%d %H:%M:%S')
            log.insert(0,{'type': 'message','recommendation': elements[4],
                          'time': now-start})
        elif '%s %s' % (elements[2],elements[3]) == DTREE_TAG:
            now = datetime.datetime.strptime('%s %s' % (elements[0][1:], elements[1][:-1]), '%Y-%m-%d %H:%M:%S')
            log.insert(1, {'type': 'Decision Tree', 'dtree': eval("".join(elements[4:])),
                           'time': now - start})
        elif '%s %s' % (elements[2],elements[3]) == PREV_TREE_TAG:
            log[0]['previous_dtree'] = ' '.join(elements[4:])
        elif '%s %s' % (elements[2],elements[3]) == ITERATION_TAG:
            log[0]['iteration_number'] =(str(elements[4]))
        elif len(elements)>4 and '%s %s %s' % (elements[2],elements[3],elements[4]) == DTREE_UPDATES:
            log[0]['dtree_updates'] = ' '.join(elements[5:])
        elif '%s %s' % (elements[2],elements[3]) == GRAPH_DIR:
            log[0]['graph_dir'] = ' '.join(elements[4:])
        elif len(elements)>4 and '%s %s %s' % (elements[2],elements[3],elements[4]) == DTREE_EXPLANATION:
            log[0]['dtree_explanation'] = ' '.join(elements[5:])
        elif '%s %s' % (elements[2],elements[3]) == WHY_NOT_TAG:
            log[0]['why_not'] = ' '.join(elements[4:])
        elif elements[2] == VALUE_TAG:
            value = float(elements[-1])
            if elements[5] == 'unprotected:':
                recommendation = 'no'
            elif elements[5] == 'protected:':
                recommendation = 'yes'
            else:
                raise ValueError('Unknown recommendation: %s' % (elements[5]))
            if log[0]['type'] == 'message':
                if value > log[0]['value']:
                    log[0]['value'] = value
                    log[0]['recommendation'] = recommendation
            else:
                now = datetime.datetime.strptime('%s %s' % (elements[0][1:],elements[1][:-1]),'%Y-%m-%d %H:%M:%S')
                log.insert(0,{'type': 'message','recommendation': recommendation,'value': value,
                              'time': now-start})
        elif elements[2] == MESSAGE_TAG:
            log[0]['content'] = ' '.join(elements[3:])
        elif elements[2] == LOCATION_TAG:
            now = datetime.datetime.strptime('%s %s' % (elements[0][1:],elements[1][:-1]),'%Y-%m-%d %H:%M:%S')
            index = symbol2index(elements[3],level)
            waypoint = WAYPOINTS[level][index]
            previous = sum([len(WAYPOINTS[prevLevel]) for prevLevel in range(level)])
            log.insert(0,{'type': 'location','destination': waypoint['name'],
                          'buildingNo': index+1,'buildingTotal': len(WAYPOINTS[level]),
                          'cumBuilding': previous+index+1, 'cumTotal': sum([len(wp) for wp in WAYPOINTS]),
                          'time': now-start})
        elif elements[2] == CREATE_TAG:
            start = datetime.datetime.strptime('%s %s' % (elements[0][1:],elements[1][:-1]),'%Y-%m-%d %H:%M:%S')
            log.insert(0,{'type': 'create',
                          'time': 'Start','start': start,
                          'ability': elements[8][:-1], 'explanation': elements[10]})
        elif elements[2] == COMPLETE_TAG:
            if log[0]['type'] != 'complete':
                now = datetime.datetime.strptime('%s %s' % (elements[0][1:],elements[1][:-1]),'%Y-%m-%d %H:%M:%S')
                log.insert(0,{'type': 'complete','success': elements[3] == 'success',
                              'time': now-start})
        elif elements[2] == USER_TAG:
            log[0]['choice'] = elements[3]
            log[0]['location'] = WAYPOINTS[level][symbol2index(elements[4],level)]['name']
            log[0]['danger'] = elements[5]
            log[0]['dead'] = elements[6]
            if elements[7][0] == '(':
                log[0]['image'] = None
                log[0]['content'] = ' '.join(elements[7:])[1:-1]
            else:
                log[0]['image'] = elements[7]
                log[0]['content'] = ' '.join(elements[8:])[1:-1]
            if ') (' in log[0]['content']:
                log[0]['content'],log[0]['ack'] = log[0]['content'].split(') (')
            else:
                log[0]['ack'] = ''
    fileinput.close()
    return log

def allVisited(world,level):
    for index in range(len(WAYPOINTS[level])):
        waypoint = index2symbol(index,level)
        visited = world.getState(waypoint,'scanned').first()
        if not visited:
            return False
    else:
        return True

def populateTable(world,waypoint,level):
    s = copy.deepcopy(world.state)
    sensor_values = {'NBCsensor':[True,False],'camera':[True,False],'microphone':['friendly','suspicious','nobody']}
    pos_sensor = {'NBCsensor':2,'camera':3,'microphone':4}
    for i  in range(12):
        s = copy.deepcopy(world.state)
        omega = {}
        robot = world.agents['robot']
        robotWaypoint = WAYPOINTS[level][waypoint]
        move = Action({'subject': robot.name,
                         'verb': 'moveto',
                         'object': robotWaypoint['symbol']})
        st = world.step(actions=move,state=world.state)
        omega['NBCsensor'] = sensor_values['NBCsensor'][i%2]
        omega['camera'] = sensor_values['camera'][(i%4)//2]
        omega['microphone'] = sensor_values['microphone'][i//4]
        for sensor in robot.omega:
            omegaKey = stateKey(robot.name,sensor)
            world.state[omegaKey] = world.value2float(omegaKey,omega[sensor])

        model = world.getModel(robot.name).first()
        decision = robot.decide(vector=world.state,model=model)
        omega = omega2index(omega)
        if omega not in robot.table:
            robot.table[omega] = []
        print ('creating for:',omega)
        lis_temp = [0,0]
        for action in decision['V']:
            print (action['verb'],decision['V'][action]['__EV__'])
            if action['verb']== 'recommend unprotected':
                lis_temp[1] = decision['V'][action]['__EV__']
            else:
                lis_temp[0] = decision['V'][action]['__EV__']
        robot.table[omega] = lis_temp
        print ('\n\n')
        world.state = s

def argmax(items):
    return max(range(len(items)),key=lambda i: items[i])

def omega2index(omega):
    return tuple(sorted(omega.items()))

def create_dict(inp):
    rel, nbc = inp['reliability'], inp['NBC']
    rel_mc = rel/nbc
    rel_m = rel_c = round(np.sqrt(rel_mc),2)
    feed_dict = {'camera':[rel_c,(1-rel_c),],'microphone':[rel_m,(1-rel_m)/2,(1-rel_m)/2],'NBCsensor':[nbc,1-nbc]}
    for dist in feed_dict.values():
        assert min(dist) > -1e-8,'Negative probability in observation distribution'
    return feed_dict


############################ For Computing Difference Between Successive Trees################## 
def compareTrees(ptr1, ptr2,diff_node,level_diff_node,level):
    temp1=dtree.dtree()
    temp1=ptr1
    temp2=dtree.dtree()
    temp2=ptr2
    l_vals=["Protected","Unprotected"]
    if(ptr1==None or ptr2==None):
        return diff_node,level_diff_node
    if(ptr1.name!=ptr2.name):
        diff_node.append(ptr1)
        level_diff_node.append({ptr1.name:level})
        return diff_node,level_diff_node
    for c in ptr1.child:
        if ptr1.child[c] in l_vals:
            if ptr1.child[c]!=ptr2.child[c]:
                diff_node.append(ptr1)
                level_diff_node.append({ptr1.name:level})
                return diff_node,level_diff_node
        else:
            if ptr2.child[c] in l_vals:
                diff_node.append(ptr1.child[c])
                level_diff_node.append({ptr1.child[c].name:level+1})
                return diff_node,level_diff_node
            else:
                ptr1=ptr1.child[c]
                ptr2=ptr2.child[c]
                diff_node,level_diff_node=compareTrees(ptr1, ptr2, diff_node,level_diff_node,level+1)
                ptr1=temp1
                ptr2=temp2
    return diff_node,level_diff_node

def hasCameraNode(root):
    if(root.name=='camera'):
        return True
    l_vals=["Protected","Unprotected"]
    for c in root.child:
        if root.child[c] in l_vals:
            continue
        else:
            if(hasCameraNode(root.child[c])):
                return True
    return False

def decisionTreeUpdate(arr1,arr2):
    result=""
    if len(arr1)==0:
        result=Template(TEMPLATES['decision_tree']['false']).substitute()
    elif len(arr1)==1:
        s=""
        level=arr2[0][arr1[0].name]
        s=arr1[0].name+" at level "+str(level)
        result=Template(TEMPLATES['decision_tree']['true']['single']).substitute({'num': "1",'names' :s})
    else:
        s=""
        i=0
        for x in arr1:
            s_name=x.name
            s_level=arr2[i][s_name]
            s+=s_name+" at level "+str(s_level)+", "
            i=i+1
        result=Template(TEMPLATES['decision_tree']['true']['multiple']).substitute({'num': str(len(arr1)),'names':s[:-2]})
    return result

def modelFreeQTable(username,level,root,world,outputFile,dtreelabels,previous_dec_tree_root,iteration,WAYPOINTS,waypoint,parameters):
    robot = world.agents['robot']
    dec_tree_root = dtree.create_dtree(copy.deepcopy(robot.table))

    if (hasCameraNode(dec_tree_root)):
        qTable = ""
        for qRow in robot.table:
            qTable += "\n"
            qTable += str(qRow) + " :" + str(robot.table[qRow])
        with open(outputFile, 'a+') as file:
            for item in robot.table:
                file.write(str(item[0][1]) + "," + str(item[1][1]) + "," + item[2][1] + "," + str(
                    round(robot.table[item][0], 2)) + "," + str(round(robot.table[item][1], 2)) + "\n")
        print("Q Table: " + qTable)
        WriteLogData('Q Table: %s' % qTable, username, level, root=root)
    else:
        print("Q Table: Not being displayed as no camera node in Decision Tree")
        WriteLogData('Q Table: %s' % "Not being displayed as no camera node in Decision Tree", username, level,
                     root=root)

    dec_dic = dtree.represent(dec_tree_root, dtreelabels)
    # if previous_dec_tree_root:
    #     print("Old", dtree.represent(previous_dec_tree_root,dtreelabels))
    # else:
    #     print("Old None")
    changed_nodes_array, level_changed_nodes_array = compareTrees(dec_tree_root, previous_dec_tree_root, [], [], 1)

    tree_with_changes = dtree.representChanges(dec_tree_root, dtreelabels, changed_nodes_array)
    # print("New",dec_dic)
    # print("Old",tree_with_changes)
    if (iteration == 0):
        decision_tree_update = "This is the first iteration of the Decision Tree."
    else:
        decision_tree_update = decisionTreeUpdate(changed_nodes_array, level_changed_nodes_array)

    ##If a tree changes from the previous iteration, the changed node is represented in Upper Case
    # print(tree_with_changes)
    # dtree.visualizeTree(dec_dic, name=str(iteration) + '_' +WAYPOINTS[level][waypoint]['name'], type= "model-free")
    graph_dir = dtree.visualizeTree(tree_with_changes, name=str(iteration) + '_' + WAYPOINTS[level][waypoint]['name'],
                        type="model-free", changed=(tree_with_changes != dec_dic),username= username)
    previous_dec_tree_root = dec_tree_root
    WriteLogData('%s %s' % (DTREE_TAG,tree_with_changes), username, level, root=root)
    WriteLogData('%s %s' % (DTREE_UPDATES,decision_tree_update), username, level, root=root)
    # log = readLogData(username, level, root)
    # print(log)
    return previous_dec_tree_root,graph_dir

def modelBasedQTable(username,level,root,old_world,outputFile,dtreelabels,previous_dec_tree_root,iteration,WAYPOINTS,waypoint,parameters):
    table = {}
    f = 0
    # state = pickle.loads(pickle.dumps(old_world.state))
    robot = old_world.agents['robot']
    for i in [True, False]:
        for j in [True, False]:
            for k in ['nobody', 'suspicious', 'friendly']:
                # for robotIndex in range(len(WAYPOINTS[level])):
                state = pickle.loads(pickle.dumps(old_world.state))
                omega = {}
                # print(i,j,k)
                # robotIndex = [int(parameters['robotWaypoint'])][0]
                # print(robotIndex)
                # if 'robotWaypoint' in parameters:
                #     # Project world state
                #     robotIndex = int(parameters['robotWaypoint'])
                # else:
                #     # Read world state
                #     robotIndex = symbol2index(old_world.getState(robot.name, 'waypoint').domain()[0], level)

                robotWaypoint = WAYPOINTS[level][waypoint]
                if not 'symbol' in robotWaypoint:
                    robotWaypoint['symbol'] = robotWaypoint['name'].replace(' ', '')
                move = Action({'subject': robot.name,
                               'verb': 'moveto',
                               'object': robotWaypoint['symbol']})
                st = old_world.step(actions=move, state=old_world.state)
                omega['NBCsensor'] = j
                omega['camera'] = i
                omega['microphone'] = k
                for sensor in robot.omega:
                    omegaKey = stateKey(robot.name, sensor)
                    old_world.state[omegaKey] = old_world.value2float(omegaKey, omega[sensor])
                model = old_world.getModel(robot.name)
                assert len(model) == 1
                model = model.first()
                decision = robot.decide(vector=old_world.state, model=model)
                # omega = omega2index(omega)
                old_world.state = state
                # print(decision)
                # print(decision['action']['verb'])
                # for action in decision['V']:
                #     print(action['verb'], decision['V'][action]['__EV__'])

                # print(decision['action']['verb'])
                # print(j,omega['camera'],i,omega['NBCsensor'],k,omega['microphone'])
                if decision['action']['verb'] == 'recommend unprotected':
                    table[(('NBCsensor', omega['NBCsensor']), ('camera', omega['camera']),
                           ('microphone', omega['microphone']))] = [0, 1]
                else:
                    table[(('NBCsensor', omega['NBCsensor']), ('camera', omega['camera']),
                           ('microphone', omega['microphone']))] = [1, 0]
                # print((('NBCsensor', omega['NBCsensor']), ('camera', omega['camera']),
                #            ('microphone', omega['microphone'])),decision['action']['verb'])
                # if decision['action']['verb'] == 'recommend unprotected':
                #     table[(('NBCsensor', i), ('camera', j), ('microphone', k),('location',robotWaypoint['symbol']))] = [0, 1]
                # else:
                #     table[(('NBCsensor', i), ('camera', j), ('microphone', k),('location',robotWaypoint['symbol']))] = [1, 0]
                # del new_world
    # print(table)
    # dec_tree_root = dtree.create_dtree(table)
    # exit()
    dec_tree_root = dtree.create_dtree(table)

    if (hasCameraNode(dec_tree_root)):
        qTable = ""
        for qRow in table:
            qTable += "\n"
            qTable += str(qRow) + " :" + str(table[qRow])
        with open(outputFile, 'a+') as file:
            for item in table:
                file.write(str(item[0][1]) + "," + str(item[1][1]) + "," + item[2][1] + "," + str(
                    round(table[item][0], 2)) + "," + str(round(table[item][1], 2)) + "\n")
        print("Q Table: " + qTable)
        WriteLogData('Q Table: %s' % qTable, username, level, root=root)
    else:
        print("Q Table: Not being displayed as no camera node in Decision Tree")
        WriteLogData('Q Table: %s' % "Not being displayed as no camera node in Decision Tree", username, level,
                     root=root)

    dec_dic = dtree.represent(dec_tree_root, dtreelabels)
    changed_nodes_array, level_changed_nodes_array = compareTrees(dec_tree_root, previous_dec_tree_root, [], [], 1)
    # print("Changed Nodes: "+str(changed_nodes_array))
    tree_with_changes = dtree.representChanges(dec_tree_root, dtreelabels, changed_nodes_array)

    if (iteration == 0):
        decision_tree_update = "This is the first iteration of the Decision Tree."
    else:
        decision_tree_update = decisionTreeUpdate(changed_nodes_array, level_changed_nodes_array)

    ##If a tree changes from the previous iteration, the changed node is represented in Upper Case
    # print(tree_with_changes)

    # dtree.visualizeTree(dec_dic, name=str(iteration) + '_' + WAYPOINTS[level][waypoint]['name'],
    #                     type="model-based")
    graph_dir = dtree.visualizeTree(tree_with_changes, name=str(iteration) + '_' + WAYPOINTS[level][waypoint]['name'],
                        type="model-based", changed=(tree_with_changes != dec_dic),username=username)
    previous_dec_tree_root = dec_tree_root
    WriteLogData('%s %s' % (DTREE_TAG,tree_with_changes), username, level, root=root)
    WriteLogData('%s %s' % (DTREE_UPDATES,decision_tree_update), username, level, root=root)
    # pprint(dec_tree_root)
    # del new_world
    # exit()
    return previous_dec_tree_root,graph_dir

def generateDecisionTreeExplanation(res,decisionTree,rCamera,rMicrophone,rNBC,recommendation,notVisitedSet,treeNodeSet):
    labels=["Unprotected","Protected"]
    sensorDict = {"NBCsensor":rNBC,"camera":rCamera,"microphone":rMicrophone}
    root=list(decisionTree.keys())[0]
    notVisitedSet.discard(root)
    if(res==""):
        res+=Template(TEMPLATES['decision_tree_explanation']['start']).substitute({
            'sensor': root,
        'explain':TEMPLATES['decision_tree_explanation'][root+"_"+str(sensorDict[root])]})
    else:
        res += Template(TEMPLATES['decision_tree_explanation']['middle']).substitute({
            'sensor': root,
            'explain': TEMPLATES['decision_tree_explanation'][root + "_" + str(sensorDict[root])]})
    if decisionTree.get(root).get(sensorDict[root]) in labels:
        for notVisitedSensor in notVisitedSet:
            if notVisitedSensor in treeNodeSet:
                res+=Template(TEMPLATES['decision_tree_explanation']['not_visited']).substitute({
                'sensor':notVisitedSensor, 'explain':TEMPLATES['decision_tree_explanation'][notVisitedSensor+"_"+str(sensorDict[notVisitedSensor])]})
            else:
                res+=Template(TEMPLATES['decision_tree_explanation']['not_present']).substitute({
                'sensor':notVisitedSensor, 'explain':TEMPLATES['decision_tree_explanation'][notVisitedSensor+"_"+str(sensorDict[notVisitedSensor])]})

        res+=Template(TEMPLATES['decision_tree_explanation']['conclude']).substitute({
        'recommendation':decisionTree.get(root).get(rNBC)})
    else:
        res=generateDecisionTreeExplanation(res,decisionTree.get(root).get(sensorDict[root]),rCamera,rMicrophone,rNBC,recommendation,notVisitedSet,treeNodeSet)
    return res


def runMission(username,level,ability='good',explanation='none',embodiment='robot',
               acknowledgment='no',learning='none',learning_rate=1,obs_condition='scripted',reliable=0.8):
    # Remove any existing log file
    print ('observation_condition:',obs_condition)
    if not os.path.isdir('.' + '\\' + 'media'):
        os.mkdir('.' + '\\' + 'media')
    if not os.path.isdir('.' + '\\' + 'media' + '\\' + 'qvalue'):
        os.mkdir('.' + '\\' + 'media' + '\\' + 'qvalue')
    if not os.path.isdir('.' + '\\' + 'media' + '\\' + 'qvalue' + '\\' + str(username)):
        os.mkdir('.' + '\\' + 'media' + '\\' + 'qvalue' + '\\' + str(username))
    outputFile="./media/qvalue/"+str(username)+"/qvalue.csv"
    with open(outputFile, 'w') as file:
        file.write("NBC, Microphone, Camera, Q(Recommend Protected Gear), Q(Recommend No Protected Gear)\n")
    try:
        os.remove(getFilename(username,level,extension='log'))
    except OSError:
        # Probably didn't exist to begin with
        pass
    # Create initial scenario
    world = createWorld(username,level,ability,explanation,embodiment,
                        acknowledgment,learning,reliability=reliable)
    oldVector=world.state
    # with open('prevtree.pickle', 'wb') as f:
    #     pickle.dump(None, f)
    # exit()
    location = world.getState('robot','waypoint').first()
    waypoint = symbol2index(location,level)
    # Go through all the waypoints

    dtreelabels=["Unprotected","Protected"]

    # dectreectr=0
    iteration = 0

    while not world.terminated():
        if world.getState(WORLD,'iteration').first() > 0:
            # if not os.pathh.isdir('media' + '\\' + str(username) ):
            #     os.mkdir('media' + '\\' + str(username))
            with open(root + '\\' +'media' + '\\' + 'prevtree' +'\\'+ str(username) + '\\' +'prevtree.pickle','rb') as f:
                previous_dec_tree_root = pickle.load(f)
        else:
            previous_dec_tree_root = None
        root = '.'
        parameters = {'robotWaypoint': waypoint,
                      'level': level}
        old_world = pickle.loads(pickle.dumps(world))
        print(GetRecommendation(username,level,parameters,world,observation_condition=obs_condition))
        print(world.getState(WORLD, 'iteration').first())
        # exit()

        if learning == 'model-free':
            previous_dec_tree_root,graph_dir = modelFreeQTable(username, level, root, old_world, outputFile, dtreelabels,
                                                     previous_dec_tree_root, world.getState(WORLD,'iteration').first(), WAYPOINTS, waypoint,
                                                     parameters)
        if learning == 'model-based':
            previous_dec_tree_root,graph_dir = modelBasedQTable(username, level, root, old_world, outputFile, dtreelabels,
                                                     previous_dec_tree_root, world.getState(WORLD,'iteration').first(), WAYPOINTS, waypoint,
                                                     parameters)

        robotCamera = world.getFeature('robot\'s camera', oldVector).max()
        robotMicrophone = world.getFeature('robot\'s microphone', oldVector).max()
        robotNBC = world.getFeature('robot\'s NBCsensor', oldVector).max()
        location = world.getState('robot','waypoint').first()
        recommendation = world.getState(location,'recommendation').first()

        
        print(location)
        print(str(robotCamera)+" "+robotMicrophone+" "+str(robotNBC)+" "+recommendation)
        treeNodeSet=dtree.nodesDTree(set(),previous_dec_tree_root,dtreelabels)
        decisionTreeExplanation=generateDecisionTreeExplanation("",dtree.represent(previous_dec_tree_root,dtreelabels),robotCamera,robotMicrophone,robotNBC,recommendation,{'camera','NBCsensor','microphone'},treeNodeSet)
        WriteLogData('%s %s' % (DTREE_EXPLANATION, decisionTreeExplanation), username, level, root=root)
        print(DTREE_EXPLANATION+" "+decisionTreeExplanation)

        if not os.path.isdir(root+'\\' + 'media' ):
            os.mkdir(root+'\\' +'media' )
        if not os.path.isdir(root +'\\' + 'media' + '\\' + 'prevtree' ):
            os.mkdir(root+'\\' +'media' + '\\' + 'prevtree' )
        if not os.path.isdir(root + '\\' + 'media' + '\\' + 'prevtree' +'\\'+ str(username)):
            os.mkdir(root+'\\' +'media' + '\\' + 'prevtree' +'\\'+ str(username))
        with open(root+'\\' +'media' + '\\' + 'prevtree' +'\\'+ str(username)+ '\\'+'prevtree.pickle', 'wb') as f:
            pickle.dump(previous_dec_tree_root, f)
        WriteLogData('%s %s' % (ITERATION_TAG, str(iteration)), username, level, root=root)
        WriteLogData('{} {}'.format(PREV_TREE_TAG, dtree.represent(previous_dec_tree_root,dtreelabels)), username, level, root=root)
        world.setState(WORLD,'iteration',world.getState(WORLD,'iteration').first()+1)
        # dectreectr=dectreectr+1
        # Was the robot right?
        # exit()
        danger = world.getState(index2symbol(waypoint,level),'danger').first()        
        print(GetAcknowledgment(None,recommendation,location,danger,username,level,
                                parameters,world,learning_rate=learning_rate,observation_condition = obs_condition))
        print("READ LOG DATA")
        print(str(readLogData(username,level)))
        readLogData(username,level,root)
        # exit()
        if not world.terminated():
            # Continue onward
            waypoint = GetDecision(username,level,parameters,world)
            print(index2symbol(waypoint,level))
        iteration+=1

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-s','--seed',action='store_true',
                        help='reuse seed for random numbers [default: %(default)s]')
    parser.add_argument('--all',action='store_true',
                        help='run all conditions [default: %(default)s]')
    parser.add_argument('-k','--acknowledgment',action='store_const',
                        const='yes',default='yes',
                        help='robot acknowledges mistakes [default: %(default)s]')
    parser.add_argument('-l','--learning',choices=['none','model-based','model-free'],
                        type=str,default='model-based',
                        help='robot learns from mistakes [default: %(default)s]')
    parser.add_argument('-lr','--learning_rate', type=int, default=1)
    parser.add_argument('-o','--observation_condition',choices=['scripted','randomize'],
                        type=str,default='scripted')
    parser.add_argument('-d','--distribution', type=dict,default={'reliability':0.7,'NBC':0.95})
    parser.add_argument('-a','--ability',choices=['badSensor','good','badModel'],
                        default='badSensor',
                        help='robot ability [default: %(default)s]')
    parser.add_argument('-b','--embodiment',choices=['robot','dog'],default='robot',
                      help='robot embodiment [default: %(default)s]')
    parser.add_argument('-x','--explanation',choices=['none','ability','confidence'],
                        default='confidence',
                        help='robot explanation [default: %(default)s]')
    args = vars(parser.parse_args())

    username = 'autotest'
    if args['all']:
        sequence = ['scryn','scryf','scryb']
        if args['seed']:
            random.seed(0)
        random.shuffle(sequence)
        for level in range(len(sequence)):
            config = sequence[level]
            ability = CODES['ability'][config[0]]
            explanation = CODES['explanation'][config[1]]
            embodiment = CODES['embodiment'][config[2]]
            acknowledgment = CODES['acknowledgment'][config[3]]
            learning = CODES['learning'][config[4]]
            runMission(username,level,ability,explanation,embodiment,acknowledgment,learning)
    else:
        for level in range(len(WAYPOINTS)):
            feed_dict = create_dict(args['distribution'])
            runMission(username,level,args['ability'],args['explanation'],
                       args['embodiment'],args['acknowledgment'],args['learning'],args['learning_rate'],args['observation_condition'])
