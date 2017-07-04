"""
A robot that teams with a human to perform a task in a virtual environment.
@author: Santosh Shankar, modified by David V. Pynadath
@organization: USC ICT
@var DISTANCES: A table of travel times between waypoints (asymmetric)
@var TEMPLATES: Explanation templates
"""
import datetime
import fileinput
import os
import random
from string import Template
import sys
import tempfile
import time

from psychsim.pwl import *
from psychsim.world import *
from psychsim.agent import Agent
from psychsim.reward import *
from psychsim.action import *
import psychsim.probability

from robotWaypoints import WAYPOINTS

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
    'decision': {
        # If a location is safe...
        True: 'I have finished surveying the $B_waypoint. I think the place is safe.',
        # If a location is not safe...
        False: 'I have finished surveying the $B_waypoint. I think the place is dangerous.'},
    'confidence': {
        # If a location is safe...
        True: 'I am $B_danger_none% confident about this assessment.',
        # If a location is not safe...
        False: 'I am $B_danger_not_none% confident about this assessment.'},
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
        # False positive
        True: 'It seems that my assessment of the $B_waypoint was incorrect. I will update my algorithms when we return to base after the mission.',
        # False negative
        False: 'It seems that my assessment of the $B_waypoint was incorrect. I will update my algorithms when we return to base after the mission.',
        None: '',
        },
    }

DISTANCES = {'Yellow Mosque': {'Auto Parts Store': 160,
                               'Furniture Store': 440,
                               'Suspected Safe House': 600,
                               'Blue Mosque': 865,
                               'Potential Sniper Spot': 365,
                               'Informant\'s House': 240,
                               'Repair Shop': 290,
                               'Cafe': 390,
                               'City Office': 640,
                               'Farm Supply Store': 535,
                               'Doctor\'s Office': 575,
                               },
             'Auto Parts Store': {'Furniture Store': 280,
                                  'Suspected Safe House': 440,
                                  'Blue Mosque': 705,
                                  'Potential Sniper Spot': 240,
                                  'Informant\'s House': 400,
                                  'Repair Shop': 450,
                                  'Cafe': 550,
                                  'City Office': 800,
                                  'Farm Supply Store': 340,
                                  'Doctor\'s Office': 405,
                                  },
             'Furniture Store': {'Suspected Safe House': 160,
                                 'Blue Mosque': 425,
                                 'Potential Sniper Spot': 135,
                                 'Informant\'s House': 410,
                                 'Repair Shop': 360,
                                 'Cafe': 260,
                                 'City Office': 370,
                                 'Farm Supply Store': 235,
                                 'Doctor\'s Office': 300,
                                 },
             'Suspected Safe House': {'Blue Mosque': 265,
                                      'Potential Sniper Spot': 295,
                                      'Informant\'s House': 570,
                                      'Repair Shop': 520,
                                      'Cafe': 420,
                                      'City Office': 370,
                                      'Farm Supply Store': 120,
                                      'Doctor\'s Office': 460,
                                      },
             'Blue Mosque': {'Potential Sniper Spot': 490,
                             'Informant\'s House': 610,
                             'Repair Shop': 560,
                             'Cafe': 460,
                             'City Office': 235,
                             'Farm Supply Store': 320,
                             'Doctor\'s Office': 405,
                             },
             'Informant\'s House': {'Repair Shop': 40,
                                 'Cafe': 145,
                                 'City Office': 400,
                                 'Potential Sniper Spot': 425,
                                 'Farm Supply Store': 525,
                                 'Doctor\'s Office': 330,
                                 },
             'Repair Shop': {'Cafe': 105,
                             'City Office': 360,
                             'Potential Sniper Spot': 385,
                             'Farm Supply Store': 485,
                             'Doctor\'s Office': 290,
                             },
             'Cafe': {'City Office': 255,
                      'Potential Sniper Spot': 270,
                      'Farm Supply Store': 280,
                      'Doctor\'s Office': 185,
                      },
             'City Office': {'Potential Sniper Spot': 370,
                             'Farm Supply Store': 380,
                             'Doctor\'s Office': 285,
                             },
             'Potential Sniper Spot': {'Farm Supply Store': 170,
                                       'Doctor\'s Office': 300,
                                       },
             'Farm Supply Store': {'Doctor\'s Office': 400,
                                   },
             }
CREATE_TAG = 'Created:'
MESSAGE_TAG = 'Message:'
LOCATION_TAG = 'Location:'
USER_TAG = 'Protective:'
COMPLETE_TAG = 'Complete'
ACK_TAG = 'Acknowledged:'
RECOMMEND_TAG = 'Recommend protection:'

CODES = {'ability': {'s': 'badSensor','g': 'good','m': 'badModel'},
         'explanation': {'n': 'none','a': 'ability','c': 'confidence'},
         'embodiment': {'r': 'robot','d': 'dog'},
         'acknowledgment': {'n': 'no','y': 'yes'},
         }

def createWorld(username='anonymous',level=0,ability='good',explanation='none',
                embodiment='robot',acknowledgment='no',sequence=False,
                root='.',ext='xml',beliefs=True):
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
    @type acknowledgment: str
    @param root: the root directory to use for files (default is current working directory)
    @param ext: the file extension for the PsychSim scenario file
      - xml: Save as uncompressed XML
      - psy: Save as bzipped XML
    @type ext: str
    @param beliefs: if C{True}, store robot's uncertain beliefs in scenario file, rather than compute them on the fly. Storing in scenario file makes the scenario a more complete model, but greatly increases file sixe. Default is C{True}
    @type beliefs: bool
    """

    print "**************************createWorld***********************"
    print 'Username:\t%s\nLevel:\t\t%s' % (username,level+1)
    print 'Ability\t\t%s\nExplanation:\t%s\nEmbodiment:\t%s\nAcknowledge:\t%s' % \
        (ability,explanation,embodiment,acknowledgment)

    # Pre-compute symbols for this level's waypoints
    for point in WAYPOINTS[level]:
        if not point.has_key('symbol'):
            point['symbol'] = point['name'].replace(' ','')

    world = World()

    world.defineState(None,'level',int,lo=0,hi=len(WAYPOINTS)-1,
                      description='Static variable indicating what mission level')
    world.setState(None,'level',level)

    world.defineState(None,'time',float)
    world.setState(None,'time',0.)

    world.defineState(None,'complete',bool)
    world.setState(None,'complete',False)
    world.addTermination(makeTree({'if': trueRow('complete'), True: True, False: False}))

    # Buildings
    threats = ['none','NBC','armed']
    for waypoint in WAYPOINTS[level]:
        if not waypoint.has_key('symbol'):
            waypoint['symbol'] = waypoint['name'].replace(' ','')
        world.addAgent(Agent(waypoint['symbol']))
        # Have we visited this waypoint?
        key = world.defineState(waypoint['symbol'],'visited',bool)
        world.setFeature(key,False)
        # Are there dangerous chemicals or armed people here?
        key = world.defineState(waypoint['symbol'],'danger',list,threats[:])
        if waypoint.has_key('NBC') and waypoint['NBC']:
            world.setFeature(key,'NBC')
        elif waypoint.has_key('armed') and waypoint['armed']:
            world.setFeature(key,'armed')
        else:
            world.setFeature(key,'none')
        key = world.defineState(waypoint['symbol'],'recommendation',list,
                                ['none','protected','unprotected'])
        world.setFeature(key,'none')

    # Human
    human = Agent('human')
    world.addAgent(human)

    world.defineState(human.name,'alive',bool)
    human.setState('alive',True)
    world.defineState(human.name,'deaths',int)
    human.setState('deaths',0)

    # Robot
    robot = Agent('robot')
    world.addAgent(robot)

    # Robot states
    world.defineState(robot.name,'waypoint',list,[point['symbol'] for point in WAYPOINTS[level]])
    robot.setState('waypoint',WAYPOINTS[level][getStart(level)]['symbol'])

    world.defineState(robot.name,'explanation',list,['none','ability','abilitybenevolence','abilityconfidence','confidence'])
    robot.setState('explanation',explanation)

    world.defineState(robot.name,'embodiment',list,['robot','dog'])
    robot.setState('embodiment',embodiment)

    world.defineState(robot.name,'acknowledgment',list,['no','yes'])
    robot.setState('acknowledgment',acknowledgment)

    world.defineState(robot.name,'ability',list,['badSensor','badModel','good'])
    if ability is True:
        # Backward compatibility with boolean ability
        ability = 'good'
    elif ability is False:
        ability = 'badSensor'
    robot.setState('ability',ability)

    # State of the robot's sensors
    world.defineState(robot.name,'sensorModel',list,['good','bad'])
    robot.setState('sensorModel','good')
    
    world.defineState(robot.name,'command',list,['none']+[point['symbol'] for point in WAYPOINTS[level]])
    robot.setState('command','none')

    # Actions
    for end in range(len(WAYPOINTS[level])):
        symbol = WAYPOINTS[level][end]['symbol']
        # Robot movement
        action = robot.addAction({'verb': 'moveto','object': symbol})
        # Legal if no contradictory command
        tree = makeTree({'if': equalRow(stateKey(robot.name,'command'),'none'),
                         True: True,
                         False: {'if': equalRow(stateKey(robot.name,'command'),symbol),
                                 True: True, False: False}})
        robot.setLegal(action,tree)
        # Dynamics of robot's location
        tree = makeTree(setToConstantMatrix(stateKey(action['subject'],'waypoint'),symbol))
        world.setDynamics(stateKey(action['subject'],'waypoint'),action,tree)
        # Dynamics of visited flag
        key = stateKey(symbol,'visited')
        tree = makeTree(setTrueMatrix(key))
        world.setDynamics(key,action,tree)
        # Dynamics of time
        key = stateKey(None,'time')
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
        # Human entry: Dead or alive if unprotected?
        key = stateKey(human.name,'alive')
        action = robot.addAction({'verb': 'recommend unprotected','object': symbol})
        tree = makeTree({'if': equalRow(stateKey(symbol,'danger'),'none'),
                         True: setTrueMatrix(key), False: setFalseMatrix(key)})
        world.setDynamics(key,action,tree)
        robot.setLegal(action,makeTree(False))
        # Human entry: How much "time" if protected?
        action = robot.addAction({'verb': 'recommend protected','object': symbol})
        key = stateKey(None,'time')
        world.setDynamics(key,action,makeTree(setToConstantMatrix(key,0.25)))
        robot.setLegal(action,makeTree(False))

    # Robot goals
    goal = minimizeFeature(stateKey(None,'time'))
    robot.setReward(goal,2.)

    goal = maximizeFeature(stateKey(human.name,'alive'))
    robot.setReward(goal,1.)

    for point in WAYPOINTS[level]:
        robot.setReward(maximizeFeature(stateKey(point['symbol'],'visited')),1.)

    if beliefs:
#        omega = 'danger'
        world.defineVariable(robot.name,ActionSet)
        # Robot beliefs
        world.setModel(robot.name,True)
        value = 1./float(len(WAYPOINTS[level]))
#        tree = KeyedVector({CONSTANT: world.value2float(omega,'none')})
        for index in range(len(WAYPOINTS[level])):
            waypoint = WAYPOINTS[level][index]
            key = stateKey(waypoint['symbol'],'danger')
    #        if index > 0:
                # Starting state is safe
            robot.setBelief(key,psychsim.probability.Distribution({'NBC': value/2., 'armed': value/2.,'none': 1.-value}))
            # Observation function
#            tree = {'if': equalRow(stateKey(robot.name,'waypoint'),waypoint['symbol']),
#                    True: generateO(world,key),
#                    False: tree}
#        robot.defineObservation(omega,makeTree(tree),domain=list,lo=['none','NBC','armed'])
        robot.defineObservation('microphone',makeTree(None),None,domain=list,
                                lo=['nobody','friendly','suspicious'])
        robot.defineObservation('NBCsensor',makeTree(None),None,domain=bool)
        robot.defineObservation('camera',makeTree(None),None,domain=bool)
    else:
        robot.defineObservation('microphone',makeTree(None),None,domain=list,
                                lo=['nobody','friendly','suspicious'])
        robot.defineObservation('NBCsensor',makeTree(None),None,domain=bool)
        robot.defineObservation('camera',makeTree(None),None,domain=bool)
    robot.setAttribute('horizon',1)

    world.setOrder([robot.name])

    filename = getFilename(username,level,ext,root)

    world.save(filename,ext=='psy')
    WriteLogData('%s user %s, level %d, ability %s, explanation %s, embodiment %s' % \
                     (CREATE_TAG,username,level,ability,explanation,embodiment),
                 username,level,root=root)
    return world

def generateMicO(world,key):
    return {'if': equalRow(key,'armed'),
            True: {'distribution':
                   [(KeyedVector({CONSTANT: world.value2float('microphone','nobody')}),0.04),
                    (KeyedVector({CONSTANT: world.value2float('microphone','friendly')}),0.03),
                    (KeyedVector({CONSTANT: world.value2float('microphone','suspicious')}),0.93)]},
            False: {'distribution':
                    [(KeyedVector({CONSTANT: world.value2float('microphone','nobody')}),0.48),
                     (KeyedVector({CONSTANT: world.value2float('microphone','friendly')}),0.49),
                     (KeyedVector({CONSTANT: world.value2float('microphone','suspicious')}),0.03)]}}

def generateNBCO(world,key):
    """
    @return: a observation function specification of the robot's NBC sensor
    @rtype: dict
    """
    return {'if': equalRow(key,'NBC'),
            True: {'distribution':
                   [(KeyedVector({CONSTANT: world.value2float('NBCsensor',False)}),0.1),
                    (KeyedVector({CONSTANT: world.value2float('NBCsensor',True)}),0.9)]},
            False: {'distribution':
                   [(KeyedVector({CONSTANT: world.value2float('NBCsensor',False)}),0.95),
                    (KeyedVector({CONSTANT: world.value2float('NBCsensor',True)}),0.05)]},
            }
    
def generateCameraO(world,key,belief=False):
    """
    @return: a observation function specification for use in a PWL function
    @rtype: dict
    """
    return {'if': equalRow(stateKey('robot','ability'),'badModel'),
            # Robot's O doesn't match up with its good observations
            True: {'if': equalRow(key,'armed'),
                    True: {'distribution':
                           [(KeyedVector({CONSTANT: world.value2float('camera',False)}),0.02),
                            (KeyedVector({CONSTANT: world.value2float('camera',True)}),0.98)]},
                    False: {'distribution':
                            [(KeyedVector({CONSTANT: world.value2float('camera',False)}),0.72),
                             (KeyedVector({CONSTANT: world.value2float('camera',True)}),0.28)]},
                   },
            False: {'if': equalRow(key,'armed'),
                    True: {'distribution':
                           [(KeyedVector({CONSTANT: world.value2float('camera',False)}),0.05),
                            (KeyedVector({CONSTANT: world.value2float('camera',True)}),0.95)]},
                    False: {'distribution':
                            [(KeyedVector({CONSTANT: world.value2float('camera',False)}),0.95),
                             (KeyedVector({CONSTANT: world.value2float('camera',True)}),0.05)]},
                    }}
    
def getStart(level):
    """
    @return: the index of the starting waypoint for the given level
    @rtype: int
    """
    for index in range(len(WAYPOINTS[level])):
        if WAYPOINTS[level][index].has_key('start'):
            return index
    else:
        return 0
        
def symbol2index(symbol,level=0):
    """
    @return: the waypoint index corresponding to the given symbol (not full) name in the given level
    @rtype: int
    """
    for index in range(len(WAYPOINTS[level])):
        if WAYPOINTS[level][index].has_key('symbol'):
            if WAYPOINTS[level][index]['symbol'] == symbol:
                return index
        elif WAYPOINTS[level][index]['name'].replace(' ','') == symbol:
            return index
    else:
        raise NameError,'Unknown waypoint %s for level %d' % (symbol,level)

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

def GetDecision(username,level,parameters,world=None,ext='xml',root='.',sleep=None):
    """
    @param parameters: ignored if request is provided
    """ 
    print "***********************GetDecision********************";

    if sleep:
        time.sleep(sleep)
    filename = getFilename(username,level,ext,root)
    if world is None:
        # Get the world from the scenario file
        world = World(filename)
    oldVector = world.state[None].domain()[0]
    
    robot = world.agents['robot']

    if 'robotWaypoint' in parameters:
        # Project world state
        robotIndex = int(parameters['robotWaypoint'])
        robotWaypoint = WAYPOINTS[level][robotIndex]
        if not robotWaypoint.has_key('symbol'):
            robotWaypoint['symbol'] = robotWaypoint['name'].replace(' ','')
        world.setState(robot.name,'waypoint',robotWaypoint['symbol'])
    else:
        # Read world state
        robotIndex = symbol2index(world.getState(robot.name,'waypoint').domain()[0],level)
        robotWaypoint = WAYPOINTS[level][robotIndex]
        if not robotWaypoint.has_key('symbol'):
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

    # Find the best action
    values = []
    actions = robot.getActions(oldVector)
    for action in actions:
        vector = KeyedVector({CONSTANT: 1.})
        key = stateKey(robot.name,'waypoint')
        vector[key] = world.value2float(key,robotWaypoint['symbol'])
        vector['time'] = 0.
        key = stateKey(action['object'],'visited')
        vector[key] = oldVector[key]
        key = turnKey(robot.name)
        vector[key] = oldVector[key]
        outcome = world.stepFromState(vector,action)
        ER = robot.reward(outcome['new']) - robot.reward(vector)
        WriteLogData('ER(%s) = %4.2f' % (action,ER),username,level,root=root)
        values.append((ER,action,outcome['delta']))
    best = max(values)
    decision = list(best[1])[0]
    destination = decision['object']
    WriteLogData('%s %s' % (LOCATION_TAG,destination),username,level,root=root)
    index = symbol2index(destination,level)
    destination = WAYPOINTS[level][index]

    return index

def GetAcknowledgment(user,recommendation,location,danger,username,level,parameters,
                      world=None,ext='xml',root='.'):
    print "**********************Get Acknowledgment*******************"

    if world is None:
        # Get the world from the scenario file
        filename = getFilename(username,level,ext,root)
        world = World(filename)
    oldVector = world.state[None].domain()[0]
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

    if world.getState('robot','acknowledgment').domain()[0] == 'yes':
        ack = Template(TEMPLATES['acknowledgment'][error]).substitute(beliefs)
    else:
        ack = ''
    # Did the user die?
    death = not user and danger != 'none'
    if death:
        key = stateKey('human','deaths')
        old = world.getValue(key)
        world.setFeature(key,old+1)
    WriteLogData('%s %s %s %s %s %s (%s) (%s)' % \
                 (USER_TAG,user,location,danger,death,
                  WAYPOINTS[level][robotIndex]['image'],
                  WAYPOINTS[level][robotIndex]['comment'],ack),
                 username,level,root)
    filename = getFilename(username,level,ext,root)
    world.save(filename,ext=='psy')
    return ack

def GetRecommendation(username,level,parameters,world=None,ext='xml',root='.',sleep=None):
    """
    Processes incoming observation and makes an assessment
    """

    print "**********************Get Recommendation********************"

    if sleep:
        time.sleep(sleep)
    filename = getFilename(username,level,ext,root)
    if world is None:
        # Get the world from the scenario file
        world = World(filename)
    oldVector = world.state[None].domain()[0]
    
    robot = world.agents['robot']

    if 'robotWaypoint' in parameters:
        # Project world state
        robotIndex = int(parameters['robotWaypoint'])
        robotWaypoint = WAYPOINTS[level][robotIndex]
        if not robotWaypoint.has_key('symbol'):
            robotWaypoint['symbol'] = robotWaypoint['name'].replace(' ','')
        world.setState(robot.name,'waypoint',robotWaypoint['symbol'])
    else:
        # Read world state
        robotIndex = symbol2index(world.getState(robot.name,'waypoint').domain()[0],level)
        robotWaypoint = WAYPOINTS[level][robotIndex]
        if not robotWaypoint.has_key('symbol'):
            robotWaypoint['symbol'] = robotWaypoint['name'].replace(' ','')

    world.setState(robotWaypoint['symbol'],'visited',True)
#    print robotWaypoint['name']

    # Process scripted observations 
    key = stateKey(robotWaypoint['symbol'],'danger')
    ability = robot.getState('ability').domain()[0]
    if ability == 'badSensor':
        sensorCorrect = False
    else:
        sensorCorrect = True
    # Generate individual sensor readings
    omega = {}
    danger = world.float2value(key,oldVector[key])
    for sensor in robot.omega:
        try:
            omega[sensor] = robotWaypoint[sensor][sensorCorrect]
        except KeyError:
            # By default, don't sense anything
            if sensor == 'microphone':
                omega[sensor] = 'nobody'
            else:
                omega[sensor] = False
#    try:
#        omega = KeyedVector({'danger': robotWaypoint['observe'][sensorCorrect]})
#    except KeyError:
#        # By default observe true value
#        omega = KeyedVector({'danger': world.float2value(key,oldVector[key])})
#    try:
#        omega['microphone'] = robotWaypoint['microphone'][sensorCorrect]
#    except KeyError:
#        # By default observe nothing
#        omega['microphone'] = False
#    omega['NBCsensor'] =  (omega['danger'] == 'NBC')
#    omega['camera'] =  (omega['danger'] == 'armed')
    WriteLogData('NBC sensor: %s' % (omega['NBCsensor']),username,level,root=root)
    WriteLogData('Camera: %s' % (omega['camera']),username,level,root=root)
    WriteLogData('Microphone: %s' % (omega['microphone']),username,level,root=root)
    # Get robot's beliefs
    loc = stateKey(robot.name,'waypoint')
    if robot.models[True]['beliefs'] is True:
        # No explicit beliefs
        # value = 1./float(len(WAYPOINTS[level]))
        # oldBeliefs = psychsim.probability.Distribution({'NBC': value/2., 'armed': value/2.,
        #                                                 'none': 1.-value})
        oldBeliefs = psychsim.probability.Distribution({'NBC': .2, 'armed': .2,
                                                        'none': .6})
#        O = VectorDistribution(generateO(world,key))
#        O = makeTree(generateO(world,key)).desymbolize(world.symbols)
        Omic = makeTree(generateMicO(world,key)).desymbolize(world.symbols)
        ONBC = makeTree(generateNBCO(world,key)).desymbolize(world.symbols)
        Ocamera = makeTree(generateCameraO(world,key)).desymbolize(world.symbols)
        assessment = Distribution()
        for belief in oldBeliefs.domain():
            prob = oldBeliefs[belief]
            
            vector = KeyedVector({CONSTANT: 1., 
                                  key: world.value2float(key,belief)})
#            joint = world.float2value(key,O*vector)
#            joint = world.float2value(key,O[vector]*vector)
            probMic = world.float2value('microphone',Omic[vector]*vector)
            prob *= probMic[omega['microphone']]
            probNBC = world.float2value('NBCsensor',ONBC[vector]*vector)
            prob *= probNBC[omega['NBCsensor']]
            probCamera = world.float2value('camera',Ocamera[vector]*vector)
            prob *= probCamera[omega['camera']]
            assessment.addProb(belief,prob)
    else:
        # Use explicit beliefs
        oldBeliefs = world.getFeature(key,robot.models[True]['beliefs'])
        assessment = Distribution()
        for belief in oldBeliefs.domain():
            vector = KeyedVector({CONSTANT: 1., 
                                  key: world.value2float(key,belief),
                                  loc: world.value2float(key,robotWaypoint['symbol'])})
            joint = robot.observe(vector,ActionSet())
            assessment.addProb(belief,oldBeliefs[belief]*joint[omega])
    assessment.normalize()
    for danger in assessment.domain():
        WriteLogData('Posterior belief in %s: %d%%' % (danger,assessment[danger]*100.),
                     username,level,root=root)

#    print assessment
    with tempfile.NamedTemporaryFile('w',dir=os.path.dirname(filename), delete=False) as tf:
        tf.write(world.__xml__().toprettyxml())
        tempname = tf.name
    done = False
    while not done:
        try:
            os.remove(filename)
            os.rename(tempname, filename)
            done = True
        except WindowsError:
            time.sleep(1)
    # world.save(filename,ext=='psy') 

    # What are my new beliefs?
    value = {}
    key = stateKey(robot.name,'waypoint')
    subBeliefs = VectorDistribution({KeyedVector({CONSTANT: 1.,key: world.value2float(key,robotWaypoint['symbol'])}): 1.})
    key = stateKey(robotWaypoint['symbol'],'danger')
    subBeliefs.join(key,world.value2float(key,assessment))
    key = stateKey('human','alive')
    subBeliefs.join(key,world.state[None].marginal(key))
    key = stateKey(robot.name,'embodiment')
    subBeliefs.join(key,world.state[None].marginal(key))
    subBeliefs.join('time',world.state[None].marginal('time'))
    key = turnKey(robot.name)
    subBeliefs.join(key,world.state[None].marginal(key))
    keyList = subBeliefs.domain()[0].keys()
    keyList.remove(CONSTANT)
    # Which recommendation is better?
    for verb in ['recommend protected','recommend unprotected']:
        value[verb] = 0.
        action = Action({'subject': robot.name,
                         'verb': verb,
                         'object': robotWaypoint['symbol']})
        for newVector in subBeliefs.domain():
            result = world.stepFromState(newVector,action)
            assert len(result['new']) == 1
            outcome = result['new'].domain()[0]
            reward = subBeliefs[newVector]*robot.reward(outcome)
            value[verb] += reward
        WriteLogData('Value of %s: %4.2f' % (verb,value[verb]),username,level,root=root)
    # Package up the separate components of my current model
    POMDP = {}
    # Add Omega_t, my latest observation
    for key,observation in omega.items():
        POMDP['omega_%s' % (key)] = observation
    # Add A_t, my chosen action
    if value['recommend unprotected'] > value['recommend protected']:
        POMDP['A'] = 'recommend unprotected'
        safety = True
        world.setState(robotWaypoint['symbol'],'recommendation','unprotected')
        WriteLogData('%s: no' % (RECOMMEND_TAG),username,level,root=root)
    else:
        POMDP['A'] = 'recommend protected'
        safety = False
        world.setState(robotWaypoint['symbol'],'recommendation','protected')
        WriteLogData('%s: yes' % (RECOMMEND_TAG),username,level,root=root)
    # Add B_t, my current beliefs
    for key in keyList:
        belief = subBeliefs.marginal(key)
        feature = state2feature(key)
        best = belief.max()
        POMDP['B_%s' % (feature)] = world.float2value(key,best)
        if feature == 'waypoint':
            POMDP['B_%s' % (feature)] = WAYPOINTS[level][symbol2index(POMDP['B_%s' % (feature)],level)]['name']
        POMDP['B_maxprob'] = belief[best]
        for value in belief.domain():
            pct = round(100.*belief[value])
            POMDP['B_%s_%s' % (feature,world.float2value(key,value))] = pct
            POMDP['B_%s_not_%s' % (feature,world.float2value(key,value))] = 100-pct
    # Use fixed explanation
    # TODO: make this a dynamic decision by the robot
    mode = world.getState(robot.name,'explanation').max()
    if mode == 'none':
        mode = ''
    explanation = ' '.join(explainDecision(safety,POMDP,mode))

    WriteLogData('%s %s' % (MESSAGE_TAG,explanation),username,level,root=root)
    return explanation

def explainDecision(decision,beliefs,mode):
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
    result.append(Template(TEMPLATES['decision'][decision]).substitute(beliefs))
    if 'confidence' in mode:
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
    print >> f,'[%s] %s' % (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            content)
    f.close()

def WriteLogData(content="",username=None,level=None,root='.'):
    """
    (U) Creating logs
    """
    filename = getFilename(username,level,extension='log',root=root)
    f = open(filename,'a')
    print >> f,'[%s] %s' % (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),content)
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
        if '%s %s' % (elements[2],elements[3]) == RECOMMEND_TAG:
            now = datetime.datetime.strptime('%s %s' % (elements[0][1:],elements[1][:-1]),'%Y-%m-%d %H:%M:%S')
            log.insert(0,{'type': 'message','recommendation': elements[4],
                          'time': now-start})
        elif elements[2] == MESSAGE_TAG:
            log[0]['content'] = ' '.join(elements[3:])
        elif elements[2] == LOCATION_TAG:
            now = datetime.datetime.strptime('%s %s' % (elements[0][1:],elements[1][:-1]),'%Y-%m-%d %H:%M:%S')
            index = symbol2index(elements[3],level)
            waypoint = WAYPOINTS[level][index]
            log.insert(0,{'type': 'location','destination': waypoint['name'],
                          'buildingNo': index+1,'buildingTotal': len(WAYPOINTS[level]),
                          'time': now-start})
        elif elements[2] == CREATE_TAG:
            start = datetime.datetime.strptime('%s %s' % (elements[0][1:],elements[1][:-1]),'%Y-%m-%d %H:%M:%S')
            log.insert(0,{'type': 'create',
                          'time': 'Start','start': start,
                          'ability': elements[8], 'explanation': elements[10]})
        elif elements[2] == COMPLETE_TAG:
            now = datetime.datetime.strptime('%s %s' % (elements[0][1:],elements[1][:-1]),'%Y-%m-%d %H:%M:%S')
            log.insert(0,{'type': 'complete','success': elements[3] == 'success',
                          'time': now-start})
        elif elements[2] == USER_TAG:
            log[0]['choice'] = elements[3]
            log[0]['location'] = WAYPOINTS[level][symbol2index(elements[4],level)]['name']
            log[0]['danger'] = elements[5]
            log[0]['dead'] = elements[6]
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
        visited = world.getState(waypoint,'visited').domain()[0]
        if not visited:
            return False
    else:
        return True

def runMission(username,level,ability='good',explanation='none',embodiment='robot',
               acknowledgment='no',beliefs=False):
    # Remove any existing log file
    try:
        os.remove(getFilename(username,level,extension='log'))
    except OSError:
        # Probably didn't exist to begin with
        pass
    # Create initial scenario
    world = createWorld(username,level,ability,explanation,embodiment,acknowledgment,
                        beliefs=beliefs)
    location = world.getState('robot','waypoint').domain()[0]
    waypoint = symbol2index(location,level)
    # Go through all the waypoints
    while not world.terminated():
        parameters = {'robotWaypoint': waypoint,
                      'level': level}
        print GetRecommendation(username,level,parameters,world)
        # Was the robot right?
        recommendation = world.getState(index2symbol(waypoint,level),'recommendation').domain()[0]
        danger = world.getState(index2symbol(waypoint,level),'danger').domain()[0]
        print GetAcknowledgment(None,recommendation,location,danger,username,level,parameters,world)
        
        if allVisited(world,level):
            world.setFeature('complete',True)
            world.save(getFilename(username,level),False)
        else:
            # Continue onward
            waypoint = GetDecision(username,level,parameters,world)
            print index2symbol(waypoint,level)
    
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-b','--beliefs',action='store_true',
                      help='store robot beliefs in scenario file [default: %(default)s]')
    parser.add_argument('-s','--seed',action='store_true',
                      help='reuse seed for random number generator [default: %(default)s]')
    args = vars(parser.parse_args())

    username = 'autotest'
    sequence = ['scrn','snrn','snry','scry','scdn','sndn','sndy','scdy']
    if args['seed']:
        random.seed(0)
    random.shuffle(sequence)
    start = time.time()
    for level in range(len(sequence)):
        config = sequence[level]
        ability = CODES['ability'][config[0]]
        explanation = CODES['explanation'][config[1]]
        embodiment = CODES['embodiment'][config[2]]
        acknowledgment = CODES['acknowledgment'][config[3]]
        runMission(username,level,ability,explanation,embodiment,acknowledgment,args['beliefs'])
    print time.time()-start
