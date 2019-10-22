from psychsim.reward import *
from psychsim.pwl import *
from psychsim.action import *
from psychsim.world import *
from psychsim.agent import *
import pyglet

# Initialize the Psychsim World
world = World()

################################
# 1. Creating an Agent
################################
# Create an Agent
actor = Agent('Agent')
# Add it to the World
world.addAgent(actor)
# Set the number of steps to look-ahead
actor.setHorizon(5)

################################
# 2. Define the Agent and World States
################################
# Define the x-position of the agent as a State
world.defineState(actor.name,'x',int)
# Define the y-position of the agent as a State
world.defineState(actor.name,'y',int)

# Define the x and y positions of the goal as States
world.defineState(actor.name, 'goal_x', int)
world.defineState(actor.name, 'goal_y', int)

# Define the initial values for all states
world.setState(actor.name, 'x', 0)
world.setState(actor.name, 'y', 0)
world.setState(actor.name, 'goal_x', 5)
world.setState(actor.name, 'goal_y', 5)

# Define the termination state
tree = makeTree({'if': equalFeatureRow(stateKey(actor.name, 'x'), stateKey(actor.name, 'goal_x')),
                 True: {'if': equalFeatureRow(stateKey(actor.name, 'y'), stateKey(actor.name, 'goal_y')),
                        True: True,
                        False: False},
                 False: False})
world.addTermination(tree)

# Generate random obstacles. Set 1/10 of the 9x9 map to obstacles
#for i in range(0,int(9*9/5)):
#    obstacles.append((random.randint(0,9),random.randint(0,9)))
#obstacles = [(2,0),(2,1),(2,2),(2,3)]
obstacles = [(0,1),(0,2),(0,3),(1,3),(2,3),(3,3),(4,3),(4,2),(4,1),(2,1),(2,0)]

################################
# 3. Set Actions
################################
# Helper functions for the action-legality check
def add_branch_plus_x(i):
    if i == -1:
        return True
    else:
        return {'if': equalRow(stateKey(actor.name, 'x'), obstacles[i][0]-1), True: {'if': equalRow(stateKey(actor.name, 'y'), obstacles[i][1]),True: False, False: add_branch_plus_x(i-1)}, False: add_branch_plus_x(i-1)}
 
def add_branch_minus_x(i):
    if i == -1:
        return True
    else:
        return {'if': equalRow(stateKey(actor.name, 'x'), obstacles[i][0]+1), True: {'if': equalRow(stateKey(actor.name, 'y'), obstacles[i][1]),True: False, False: add_branch_minus_x(i-1)}, False: add_branch_minus_x(i-1)}

def add_branch_plus_y(i):
    if i == -1:
        return True
    else:
        return {'if': equalRow(stateKey(actor.name, 'y'), obstacles[i][1]-1), True: {'if': equalRow(stateKey(actor.name, 'x'), obstacles[i][0]),True: False, False: add_branch_plus_y(i-1)}, False: add_branch_plus_y(i-1)}

def add_branch_minus_y(i):
    if i == -1:
        return True
    else:
        return {'if': equalRow(stateKey(actor.name, 'y'), obstacles[i][1]+1), True: {'if': equalRow(stateKey(actor.name, 'x'), obstacles[i][0]),True: False, False: add_branch_minus_y(i-1)}, False: add_branch_minus_y(i-1)}

# Increment X position and set world dynamics
action = actor.addAction({'verb': 'MoveRight'})
tree = makeTree(incrementMatrix(stateKey(action['subject'], 'x'), 1.))
world.setDynamics(stateKey(action['subject'], 'x'), action, tree)

# Boundary and Obstacle check
tree = makeTree({'if': equalRow(stateKey(actor.name, 'x'), '5'),
             True: False, False: add_branch_plus_x(len(obstacles)-1)})
actor.setLegal(action, tree)


# Decrement X position and set world dynamics
action = actor.addAction({'verb': 'MoveLeft'})
tree = makeTree(incrementMatrix(stateKey(action['subject'], 'x'), -1.))
world.setDynamics(stateKey(action['subject'], 'x'), action, tree)

# Boundary and Obstacle check
tree = makeTree({'if': equalRow(stateKey(actor.name, 'x'), '0'),
             True: False, False: add_branch_minus_x(len(obstacles)-1)})
actor.setLegal(action, tree)


# Increment Y position and set world dynamics
action = actor.addAction({'verb': 'MoveUp'})
tree = makeTree(incrementMatrix(stateKey(action['subject'], 'y'), 1.))
world.setDynamics(stateKey(action['subject'], 'y'), action, tree)

# Boundary and Obstacle check
tree = makeTree({'if': equalRow(stateKey(actor.name, 'y'), '5'),
             True: False, False: add_branch_plus_y(len(obstacles)-1)})
actor.setLegal(action, tree)


# Decrement Y position and set world dynamics
action = actor.addAction({'verb': 'MoveDown'})
tree = makeTree(incrementMatrix(stateKey(action['subject'], 'y'), -1.))
world.setDynamics(stateKey(action['subject'], 'y'), action, tree)

# Boundary and Obstacle check
tree = makeTree({'if': equalRow(stateKey(actor.name, 'y'), '0'),
             True: False, False: add_branch_minus_y(len(obstacles)-1)})
actor.setLegal(action, tree)

################################
# 4. Set Rewards
################################
# Set the Agent reward to minimize getting to goal
actor.setReward(minimizeDifference(stateKey(actor.name, 'x'), stateKey(actor.name, 'goal_x')), 1.0)
actor.setReward(minimizeDifference(stateKey(actor.name, 'y'), stateKey(actor.name, 'goal_y')), 1.0)

################################
# 5. Set Turn Order
################################
# Parallel action
# self.world.setOrder([set(self.world.agents.keys())])
# Sequential action
world.setOrder(world.agents.keys())


################################
# Graphics
################################
pyglet.resource.path = ['../resources']
pyglet.resource.reindex()

SCREEN_WIDTH = 6 * 32
SCREEN_HEIGHT = 6 * 32
window = pyglet.window.Window(resizable=True)
window.set_size(SCREEN_WIDTH, SCREEN_HEIGHT)

tile_image = pyglet.resource.image("grass.png")
tiles_batch = pyglet.graphics.Batch()
tiles = []
for y in range(0, 10):
    for x in range(0, 10):
        tiles.append(pyglet.sprite.Sprite(
            img=tile_image,
            x=x * 32,
            y=y * 32,
            batch=tiles_batch)
        )

goal_image = pyglet.resource.image("target.png")
goals_batch = pyglet.graphics.Batch()
goals = []
goals.append(pyglet.sprite.Sprite(
    img=goal_image,
    x=5 * 32,
    y=5 * 32,
    batch=goals_batch)
)

agent_image = pyglet.resource.image("soldier_blue.png")
agents_batch = pyglet.graphics.Batch()
agents = []
agents.append(pyglet.sprite.Sprite(
    img=agent_image,
    x=0 * 32,
    y=0 * 32,
    batch=agents_batch)
)

obstacle_image = pyglet.resource.image("rock.png")
obstacles_batch = pyglet.graphics.Batch()
obs = []
for index in range(0,len(obstacles)):
    obs.append(pyglet.sprite.Sprite(
        img=obstacle_image,
        x=obstacles[index][0]*32,
        y=obstacles[index][1]*32,
        batch=obstacles_batch)
    )

@window.event
def on_draw():
    window.clear()
    tiles_batch.draw()
    obstacles_batch.draw()
    goals_batch.draw()
    agents_batch.draw()
    
def update(dt):
    result = world.step()
    world.explain(result, 2)
    if world.terminated():
        window.close()

    agents[0].x = int(world.getState('Agent', 'x').domain()[0]) * 32
    agents[0].y = int(world.getState('Agent', 'y').domain()[0]) * 32

pyglet.clock.schedule_interval(update, 0.5)
pyglet.app.run()