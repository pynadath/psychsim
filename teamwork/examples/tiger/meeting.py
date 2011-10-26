"""
PsychSim specification of the robot grid meeting problem
"""
from teamwork.agent.AgentClasses import classHierarchy
from teamwork.math.Keys import ObservationKey
from teamwork.math.probability import Distribution
from teamwork.math.KeyedVector import ThresholdRow
from teamwork.math.KeyedMatrix import IdentityMatrix,IncrementMatrix
from teamwork.math.KeyedTree import KeyedPlane
from teamwork.math.ProbabilityTree import ProbabilityTree,createBranchTree

# Set of possible observations
Omega = {'left': ObservationKey({'type':'wall left'}),
         'right': ObservationKey({'type':'wall right'}),
         }

def setupMeeting():
    width = 2
    height = 2
    classHierarchy['Robot'] = {
        'parent': ['Entity'],
        'state': {},
        'dynamics': {'x': {}, 'y': {}},
        }
    # Set up range of X values
    dist = {0.: 1.,1.:0.}
    for x in range(1,width-1):
        dist[float(x)/float(width-1)] = 0.
    dist[1.] = 0.
    classHierarchy['Robot']['state']['x'] = Distribution(dist)
    # Set up range of Y values
    dist = {0.: 1.,1.: 0.}
    for y in range(1,height-1):
        dist[float(y)/float(height-1)] = 0.
    classHierarchy['Robot']['state']['y'] = Distribution(dist)
    # Set up actions
    directions = ['up','down','left','right']
    actions = {'type': 'XOR','key':'type',
               'values': []}
    for action in directions:
        actions['values'].append({'type':'literal','value':action})
    actions['values'].append({'type': 'literal', 'value': 'stay'})
    classHierarchy['Robot']['actions'] = actions
    # Set up observations
    obs = {Omega['left']['type']: {},
           Omega['right']['type']: {},
           }
    classHierarchy['Robot']['observations'] = obs
    # Set up dynamics
    classHierarchy['Robot']['dynamics']['x']['up'] = move('x',0,width)
    classHierarchy['Robot']['dynamics']['y']['up'] = move('y',1,height)
    classHierarchy['Robot']['dynamics']['x']['down'] = move('x',0,width)
    classHierarchy['Robot']['dynamics']['y']['down'] = move('y',-1,height)
    classHierarchy['Robot']['dynamics']['x']['left'] = move('x',-1,width)
    classHierarchy['Robot']['dynamics']['y']['left'] = move('y',0,height)
    classHierarchy['Robot']['dynamics']['x']['right'] = move('x',1,width)
    classHierarchy['Robot']['dynamics']['y']['right'] = move('y',0,height)
    
def move(dimension,delta=0,span=2,escape=0.1):
    """
    Generates dynamics for an action that tries to move in the specified 
    dimension
    @param dimension: the dimension of the intended move ('x' or 'y')
    @type dimension: str
    @param delta: the intended change in position (default is 0)
    @type delta,span: int
    @param span: the maximum length of the dimension (default is 2)
    @param escape: the probability of making a given unintended change
    @type escape: float
    """
    assert span == 2,'Unable to handle grids that are not 2x2.  Sorry'
    # Space between values along given dimension
    interval = 1./float(span-1) 
    stay = ProbabilityTree(IdentityMatrix(dimension))
    if dimension == 'x':
        # Dynamics trees for moves along X dimension
        moveUp = ProbabilityTree(IdentityMatrix(dimension))
        moveDown = ProbabilityTree(IdentityMatrix(dimension))
        moveLeft = ProbabilityTree(IncrementMatrix(dimension,value=-interval))
        moveRight = ProbabilityTree(IncrementMatrix(dimension,value=interval))
    else:
        assert dimension == 'y','Unknown dimension: %s' % (dimension)
        # Dynamics trees for moves along Y dimension
        moveUp = ProbabilityTree(IncrementMatrix(dimension,value=interval))
        moveDown = ProbabilityTree(IncrementMatrix(dimension,value=-interval))
        moveLeft = ProbabilityTree(IdentityMatrix(dimension))
        moveRight = ProbabilityTree(IdentityMatrix(dimension))
    # Assign extra probability to intended move
    leftover = 1. - 5.*escape
    if delta == 0:
        intended = stay
    elif dimension == 'x':
        if delta == 1:
            intended = moveRight
        else:
            assert delta == -1,'Unable to handle moves of %d spaces' % (delta)
            intended = moveLeft
    else:
        if delta == 1:
            intended = moveUp
        else:
            assert delta == -1,'Unable to handle moves of %d spaces' % (delta)
            intended = moveDown
    # Set up tree for upper left
    upperLeft = ProbabilityTree()
    dist = {stay: escape, moveUp: escape, moveDown: escape, 
            moveLeft: escape, moveRight: escape}
    dist[intended] += leftover
    dist[stay] += dist[moveLeft] + dist[moveUp]
    dist[moveLeft] = 0.
    dist[moveUp] = 0.
    upperLeft.branch(Distribution(dist))
    # Set up tree for upper right
    upperRight = ProbabilityTree()
    dist = {stay: escape, moveUp: escape, moveDown: escape, 
            moveLeft: escape, moveRight: escape}
    dist[intended] += leftover
    dist[stay] += dist[moveRight] + dist[moveUp]
    dist[moveRight] = 0.
    dist[moveUp] = 0.
    upperRight.branch(Distribution(dist))
    # Set up tree for lower left
    lowerLeft = ProbabilityTree()
    dist = {stay: escape, moveUp: escape, moveDown: escape, 
            moveLeft: escape, moveRight: escape}
    dist[intended] += leftover
    dist[stay] += dist[moveLeft] + dist[moveDown]
    dist[moveLeft] = 0.
    dist[moveDown] = 0.
    lowerLeft.branch(Distribution(dist))
    # Set up tree for lower right
    lowerRight = ProbabilityTree()
    dist = {stay: escape, moveUp: escape, moveDown: escape, 
            moveLeft: escape, moveRight: escape}
    dist[intended] += leftover
    dist[stay] += dist[moveRight] + dist[moveDown]
    dist[moveRight] = 0.
    dist[moveDown] = 0.
    lowerRight.branch(Distribution(dist))
    # Set up branches for testing which cell we're in
    xRow = ThresholdRow(keys=[{'entity':'self','feature':'x'}])
    yRow = ThresholdRow(keys=[{'entity':'self','feature':'y'}])
    leftTree = createBranchTree(KeyedPlane(yRow,0.5),lowerLeft,upperLeft)    
    rightTree = createBranchTree(KeyedPlane(yRow,0.5),lowerRight,upperRight)
    return createBranchTree(KeyedPlane(xRow,0.5),leftTree,rightTree)

if __name__ == '__main__':
    import bz2
    from teamwork.multiagent.GenericSociety import GenericSociety

    society = GenericSociety()
    try:
        f = bz2.BZ2File('meeting.soc','r')
        data = f.read()
        f.close()
        from xml.dom import minidom
        doc = minidom.parseString(data)
        society.parse(doc.documentElement)
    except IOError:
        setupMeeting()
        society.importDict(classHierarchy)
        society.save('meeting.soc')
