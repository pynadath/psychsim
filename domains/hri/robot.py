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

from robotWaypoints import WAYPOINTS,DISTANCES

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
                root='.',ext='xml'):
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

    key = world.defineState(None,'phase',set,lo={'scan','move'},
                            description='What phase of the turn is it')
    world.setState(None,'phase','move')
    # Alternate between phases
    tree = makeTree({'if': equalRow(key,'scan'),
                     True: setToConstantMatrix(key,'move'),
                     False: setToConstantMatrix(key,'scan')})
    world.setDynamics(key,True,tree)
                     
    # Buildings
    threats = ['none','NBC','armed']
    for waypoint in WAYPOINTS[level]:
        if not waypoint.has_key('symbol'):
            waypoint['symbol'] = waypoint['name'].replace(' ','')
        world.addAgent(waypoint['symbol'])
        # Has the robot scanned this waypoint?
        key = world.defineState(waypoint['symbol'],'scanned',bool)
        world.setFeature(key,False)
        # Has the human teammate entered this waypoint?
        key = world.defineState(waypoint['symbol'],'entered',bool)
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

    # All done when every building has been visited by teammate
    row = andRow([makeFuture(stateKey(wp['symbol'],'entered'))
                  for wp in WAYPOINTS[level]])
    world.addTermination(makeTree({'if': row,
                                   True: setTrueMatrix(TERMINATED),
                                   False: setFalseMatrix(TERMINATED)}))
    # Human
    human = world.addAgent('human')

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
        tree = makeTree({'if': equalRow('phase','move'),
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
        
        # Observations from scanning this waypoint
        key = stateKey(symbol,'danger')
        omega = stateKey(robot.name,'microphone')
        robot.setO('microphone',action,makeTree(generateMicO(world,key)))
        omega = stateKey(robot.name,'NBCsensor')
        robot.setO('NBCsensor',action,makeTree(generateNBCO(world,key)))
        omega = stateKey(robot.name,'camera')
        robot.setO('camera',action,makeTree(generateCameraO(world,key)))

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
        key = stateKey(None,'time')
        world.setDynamics(key,action,makeTree(setToConstantMatrix(key,0.)))
        tree = makeTree({'if': equalRow('phase','scan'),
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
        key = stateKey(None,'time')
        world.setDynamics(key,action,makeTree(setToConstantMatrix(key,0.25)))
        tree = makeTree({'if': equalRow('phase','scan'),
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

    # Robot goals
    goal = minimizeFeature(stateKey(None,'time'))
    robot.setReward(goal,100.)

    goal = achieveGoal(stateKey(human.name,'alive'))
    robot.setReward(goal,20.)

    for point in WAYPOINTS[level]:
        robot.setReward(maximizeFeature(stateKey(point['symbol'],'scanned')),2.)

    world.setOrder([robot.name])

    # Robot beliefs
    model = '%s0' % (robot.name)
    world.setModel(robot.name,model)
    value = 10./float(len(WAYPOINTS[level]))
    for index in range(len(WAYPOINTS[level])):
        waypoint = WAYPOINTS[level][index]
        key = stateKey(waypoint['symbol'],'danger')
        dist = psychsim.probability.Distribution({'NBC': value/2.,
                                                  'armed': value/2.,
                                                  'none': 1.-value})
        robot.setBelief(key,dist,model)
            
    robot.setAttribute('horizon',1)

    filename = getFilename(username,level,ext,root)
    world.save(filename,ext=='psy')
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
    
def generateCameraO(world,key,belief=False):
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
                           [(setToConstantMatrix(omega,False),0.05),
                            (setToConstantMatrix(omega,True),0.95)]},
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
    oldVector = world.state
    
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
        robotIndex = symbol2index(world.getState(robot.name,'waypoint').first(),
                                  level)
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
    model = world.getModel(robot.name).first()
    result = robot.decide(oldVector,model=model)
    destination = result['action']['object']
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
    action = Action({'subject': 'robot',
                     'verb': 'recommend %s' % (recommendation),
                     'object': location})
    assert len(world.getModel('robot')) == 1
    world.step(action)
    assert len(world.getModel('robot')) == 1
    belief = world.getState(location,'danger',
                            world.agents['robot'].getBelief().values()[0])
    real = world.getState(location,'danger')
    assert len(real) == 1
    assert len(belief) == 1
    assert real.first() == belief.first()
    if world.getState('robot','acknowledgment').first() == 'yes':
        ack = Template(TEMPLATES['acknowledgment'][error]).substitute(beliefs)
    else:
        ack = ''
    # Did the user die?
    death = not world.getState('human','alive').first()
    # if death:
    #     key = stateKey('human','deaths')
    #     old = world.getValue(key)
    #     world.setFeature(key,old+1)
    # world.setState('human','alive',True)
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

    action = Action({'subject': robot.name,
                     'verb': 'moveto',
                     'object': robotWaypoint['symbol']})
    world.step(action)

    # Process scripted observations 
    key = stateKey(robotWaypoint['symbol'],'danger')
    ability = robot.getState('ability').domain()[0]
    if ability == 'badSensor':
        sensorCorrect = False
    else:
        sensorCorrect = True
    # Generate individual sensor readings
    omega = {}
    danger = world.getFeature(key,world.state)
    for sensor in robot.omega:
        try:
            omega[sensor] = robotWaypoint[sensor][sensorCorrect]
        except KeyError:
            # By default, don't sense anything
            if sensor == 'microphone':
                omega[sensor] = 'nobody'
            else:
                omega[sensor] = False
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
    result = robot.decide(world.state)
    policy = result['policy']
    del result['policy']
    value = {a['verb']: V['__EV__'] for a,V in result.values()[0]['V'].items()}
    subBeliefs = {a['verb']: V['__beliefs__'] \
                  for a,V in result.values()[0]['V'].items()}
    for verb in ['recommend unprotected','recommend protected']:
        WriteLogData('Value of %s: %4.2f' % (verb,value[verb]),username,level,
                     root=root)
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
        if assessment['none'] > 0.5:
            print assessment
            print value
            for a,V in result.values()[0]['V'].items():
                print a
            for action,bel in subBeliefs.items():
                for key in ['human\'s alive','time']:
                    print action,key
                    print world.float2value(key,bel.marginal(key))
        assert assessment['none'] < 0.5
        POMDP['A'] = 'recommend protected'
        safety = False
        world.setState(robotWaypoint['symbol'],'recommendation','protected')
        WriteLogData('%s: yes' % (RECOMMEND_TAG),username,level,root=root)
    # Add B_t, my current beliefs
    for key in subBeliefs[POMDP['A']].keys():
        if key != keys.CONSTANT:
            entity = state2agent(key)
            if entity != 'robot' and entity != robotWaypoint['symbol']:
                continue
            belief = subBeliefs[POMDP['A']].marginal(key)
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
    explanation = ' '.join(explainDecision(safety,POMDP,mode))

    WriteLogData('%s %s' % (MESSAGE_TAG,explanation),username,level,root=root)

    # Save file in as synchronized a fashion as we can
    with tempfile.NamedTemporaryFile('w',dir=os.path.dirname(filename),
                                     delete=False) as tf:
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
        visited = world.getState(waypoint,'entered').first()
        if not visited:
            return False
    else:
        return True

def runMission(username,level,ability='good',explanation='none',embodiment='robot',
               acknowledgment='no'):
    # Remove any existing log file
    try:
        os.remove(getFilename(username,level,extension='log'))
    except OSError:
        # Probably didn't exist to begin with
        pass
    # Create initial scenario
    world = createWorld(username,level,ability,explanation,embodiment,acknowledgment)
    location = world.getState('robot','waypoint').first()
    waypoint = symbol2index(location,level)
    # Go through all the waypoints
    while not world.terminated():
        parameters = {'robotWaypoint': waypoint,
                      'level': level}
        print GetRecommendation(username,level,parameters,world)
        # Was the robot right?
        location = world.getState('robot','waypoint').first()
        recommendation = world.getState(location,'recommendation').first()
        danger = world.getState(index2symbol(waypoint,level),'danger').first()
        print GetAcknowledgment(None,recommendation,location,danger,username,level,
                                parameters,world)
        if not world.terminated():
            # Continue onward
            waypoint = GetDecision(username,level,parameters,world)
            print index2symbol(waypoint,level)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
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
        runMission(username,level,ability,explanation,embodiment,acknowledgment)
    print time.time()-start
