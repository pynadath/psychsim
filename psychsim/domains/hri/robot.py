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

from psychsim.pwl import *
from psychsim.world import *
from psychsim.agent import Agent
from psychsim.reward import *
from psychsim.action import *
import psychsim.probability

from psychsim.domains.hri.robotWaypoints import NEWWAYPOINTS as WAYPOINTS
from psychsim.domains.hri.robotWaypoints import DISTANCES

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
        'correct': 'It seems that my estimate of the $waypoint was correct',
        'delay': 'It seems that my estimate of the $waypoint was incorrect',
        'died': 'It seems that my estimate of the $waypoint was incorrect',
        'required': '. I\'ve updated my algorithm accordingly. ',
        # False positive
        True: 'It seems that my assessment of the $B_waypoint was incorrect. I will update my algorithms when we return to base after the mission.',
        # False negative
        False: 'It seems that my assessment of the $B_waypoint was incorrect. I will update my algorithms when we return to base after the mission.',
        None: '',
        'always': 'In the future, I will be $compare likely to report a safe estimate when my sensors have the same readings.',
        },
    'ack_learning':{
        'always':'It seems that my assessment of the $B_waypoint was incorrect. ',
        'update_info':'I have changed my FNprob of the camera sensor from $old_val to $new_val. '
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
VALUE_TAG = 'Value'

CODES = {'ability': {'s': 'badSensor','g': 'good','m': 'badModel'},
         'explanation': {'n': 'none','a': 'ability','c': 'confidence','b': 'abilityconfidence'},
         'embodiment': {'r': 'robot','d': 'dog'},
         'acknowledgment': {'n': 'no','y': 'yes'},
         'learning': {'n': 'none','b': 'model-based', 'f': 'model-free'},
         }

def createWorld(username='anonymous',level=0,ability='good',explanation='none',
                embodiment='robot',acknowledgment='no',learning='none',fnProb=0.01,
                sequence=False,root='.',ext='xml',reliability = 0.80):
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
    robot.setState('cameraFNProb',fnProb)

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
        robot.setO('microphone',action,makeTree(generateMicO(world,key)))
        omega = stateKey(robot.name,'NBCsensor')
        tree = makeTree(generateNBCO(world,key))
        robot.setO('NBCsensor',action,tree)
        omega = stateKey(robot.name,'camera')
        robot.setO('camera',action,makeTree(generateCameraO(world,key,falseNeg=fnProb)))

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

def generateMicO(world,key):
    omega = stateKey('robot','microphone')
    return {'if': equalRow(key,'armed'),
            True: {'distribution':
                   [(setToConstantMatrix(omega,'nobody'),0.04),
                    (setToConstantMatrix(omega,'friendly'),0.03),
                    (setToConstantMatrix(omega,'suspicious'),0.93)]},
            False: {'distribution':
                    [(setToConstantMatrix(omega,'nobody'),0.48),
                     (setToConstantMatrix(omega,'friendly'),0.49),
                     (setToConstantMatrix(omega,'suspicious'),0.03)]}}

def generateNBCO(world,key):
    """
    @return: a observation function specification of the robot's NBC sensor
    @rtype: dict
    """
    omega = stateKey('robot','NBCsensor')
    return {'if': equalRow(key,'NBC'),
            True: {'distribution':
                   [(setFalseMatrix(omega),0.1),
                    (setTrueMatrix(omega),0.9)]},
            False: {'distribution':
                   [(setFalseMatrix(omega),0.95),
                    (setTrueMatrix(omega),0.05)]},
            }

def generateCameraO(world,key,belief=False,falseNeg=0.05):
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
                            [(setToConstantMatrix(omega,False),0.95),
                             (setToConstantMatrix(omega,True),0.05)]},
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
                      world=None,ext='xml',root='.',learning_rate = 1.0):
    print("**********************Get Acknowledgment*******************")

    if world is None:
        # Get the world from the scenario file
        filename = getFilename(username,level,ext,root)
        world = World(filename)
    oldVector = world.state
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
                robot.table[omega2index(robot.prev_state)][0] = robot.table[omega2index(robot.prev_state)][0] + LR*(20-60*(0.25))
                robot.old_decision[omega2index(robot.prev_state)].append('correct')
            if danger == 'none':
                # Have to handle this case a better way
                robot.table[omega2index(robot.prev_state)][0] = max(dummy_placeholder,robot.table[omega2index(robot.prev_state)][0] + LR*(20-60*(0.25) - (10) )) # The -10 is for recommending protected when there is no danger
                robot.old_decision[omega2index(robot.prev_state)].append('delay')
        elif recommendation == 'unprotected' and danger != 'none':
            enter_flag = 1
            robot.table[omega2index(robot.prev_state)][1] = max(dummy_placeholder,robot.table[omega2index(robot.prev_state)][1] + LR*(-12))
            robot.old_decision[omega2index(robot.prev_state)].append('died')
        elif recommendation == 'unprotected' and danger == 'none':
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
            action = Action({'subject': 'robot',
                             'verb': 'recommend %s' % (recommendation),
                             'object': location})
        else:
            if user:
                action = Action({'subject': 'robot',
                                 'verb': 'recommend %s' % ('protected'),
                                 'object': location})
            else:
                action = Action({'subject': 'robot',
                                 'verb': 'recommend %s' % ('unprotected'),
                                 'object': location})
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
            if world.getFeature('%s\'s danger' % (location),oldVector).get('armed') > 0.5:
                # Armed gunman was there
                ack += Template(TEMPLATES['ack_learning']['always']).substitute({'B_waypoint':WAYPOINTS[level][robotIndex]['name']})
                fnProb = world.getFeature('robot\'s cameraFNProb',oldVector)
                assert len(fnProb) == 1
                fnProb = fnProb.first()
                old = fnProb
                alpha = 0.1
                if world.getFeature('robot\'s camera',oldVector).get(False) > 0.5:
                    # False negative!
                    fnProb = (1.-alpha)*fnProb + alpha
                else:
                    fnProb = (1.-alpha)*fnProb
                ack += Template(TEMPLATES['ack_learning']['update_info']).substitute({'old_val':old,'new_val':fnProb,})
                world.setFeature('robot\'s cameraFNProb',fnProb)
                for waypoint in WAYPOINTS[level][robotIndex+1:]:
                    symbol = waypoint['symbol']
                    action = ActionSet(Action({'subject': 'robot','verb': 'moveto',
                                               'object': symbol}))
                    tree = makeTree(generateCameraO(world,stateKey(symbol,'danger'),
                                                    falseNeg=fnProb))
                    world.agents['robot'].setO('camera',action,tree)
        if user is None:
            action = Action({'subject': 'robot',
                             'verb': 'recommend %s' % (recommendation),
                             'object': location})
        else:
            print ('User action is not None')
            if user:
                action = Action({'subject': 'robot',
                                 'verb': 'recommend %s' % ('protected'),
                                 'object': location})
            else:
                action = Action({'subject': 'robot',
                                 'verb': 'recommend %s' % ('unprotected'),
                                 'object': location})
        assert len(world.getModel('robot')) == 1
        world.step(action,select=True)
        assert len(world.getModel('robot')) == 1
        beliefState = list(world.agents['robot'].getBelief().values())[0]
        belief = world.getState(location,'danger',beliefState)

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
                omega[sensor] = robotWaypoint[sensor][sensorCorrect]
            else:
                omega[sensor] = nullReading[sensor]
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
        POMDP['A'] = 'recommend unprotected'
        safety = True
        world.setState(robotWaypoint['symbol'],'recommendation','unprotected')
        WriteLogData('%s: no' % (RECOMMEND_TAG),username,level,root=root)
    else:
        POMDP['A'] = 'recommend protected'
        safety = False
        world.setState(robotWaypoint['symbol'],'recommendation','protected')
        WriteLogData('%s: yes' % (RECOMMEND_TAG),username,level,root=root)
    if learning == 'model-free':
        POMDP['B_waypoint'] = WAYPOINTS[level][symbol2index(world.getState('robot','waypoint').first(),level)]['name']
        if action_predicted == 0:
            # Unsafe! TODO: This is really confidence, not a belif, so should be renamed
            POMDP['B_danger_not_none'] = int(100.*values_predicted[action_predicted]/sum(values_predicted))
        else:
            POMDP['B_danger_none'] = int(100.*values_predicted[action_predicted]/sum(values_predicted))
    else:
        # Add B_t, my current beliefs
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
#    pp.pprint(POMDP)
    WriteLogData('%s %s' % (MESSAGE_TAG,explanation),username,level,root=root)

    with open(filename,'wb') as scenarioFile:
        pickle.dump(world,scenarioFile)
    return explanation

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
        if len(elements) <= 1:
            # print (elements)
            continue
        if '%s %s' % (elements[2],elements[3]) == RECOMMEND_TAG:
            now = datetime.datetime.strptime('%s %s' % (elements[0][1:],elements[1][:-1]),'%Y-%m-%d %H:%M:%S')
            log.insert(0,{'type': 'message','recommendation': elements[4],
                          'time': now-start})
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

def runMission(username,level,ability='good',explanation='none',embodiment='robot',
               acknowledgment='no',learning='none',learning_rate=1,obs_condition='scripted',reliable=0.8):
    # Remove any existing log file
    print ('observation_condition:',obs_condition)
    try:
        os.remove(getFilename(username,level,extension='log'))
    except OSError:
        # Probably didn't exist to begin with
        pass
    # Create initial scenario
    world = createWorld(username,level,ability,explanation,embodiment,
                        acknowledgment,learning,reliability=reliable)
    location = world.getState('robot','waypoint').first()
    waypoint = symbol2index(location,level)
    # Go through all the waypoints
    while not world.terminated():
        parameters = {'robotWaypoint': waypoint,
                      'level': level}
        print(GetRecommendation(username,level,parameters,world,observation_condition=obs_condition))
        # Was the robot right?
        location = world.getState('robot','waypoint').first()
        recommendation = world.getState(location,'recommendation').first()
        danger = world.getState(index2symbol(waypoint,level),'danger').first()
        print(GetAcknowledgment(None,recommendation,location,danger,username,level,
                                parameters,world,learning_rate=learning_rate))
        if not world.terminated():
            # Continue onward
            waypoint = GetDecision(username,level,parameters,world)
            print(index2symbol(waypoint,level))

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-s','--seed',action='store_true',
                        help='reuse seed for random numbers [default: %(default)s]')
    parser.add_argument('--all',action='store_true',
                        help='run all conditions [default: %(default)s]')
    parser.add_argument('-k','--acknowledgment',action='store_const',
                        const='yes',default='no',
                        help='robot acknowledges mistakes [default: %(default)s]')
    parser.add_argument('-l','--learning',choices=['none','model-based','model-free'],
                        type=str,default='none',
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
