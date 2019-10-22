# Team of agents that attempts to capture a flag without being caught by enemies
# Agents:
# Explorer - minimize distance between self and goal location
# Distractor - maximize distance between explorer and enemy (new)
# Enemy - minimize distance between self and explorer and distractor
# Base - deploy distractor when explorer in danger (new)

from __future__ import print_function
from psychsim.reward import *
from psychsim.pwl import *
from psychsim.action import *
from psychsim.world import *
from psychsim.agent import *
import pyglet
from pyglet.window import key
from multiprocessing import Process
from threading import Thread
import time

import loader as loader

MAP_SIZE_X = 0
MAP_SIZE_Y = 0

F_ACTORS = 0
F_START_LOC = []
F_GOAL_LOC = []

E_ACTORS = 0
E_START_LOC = []
E_PATROL_RANGE = 5

D_ACTORS = 0
D_START_LOC = []

BASE = [0.0, 0.0]
DISTRACTOR = [0.0, 0.0]
ENEMY = [0.0, 0.0, 0.0]
AGENT = [0.0, 0.0]


# MAP_SIZE_X = 8  # X value of map dimension
# MAP_SIZE_Y = 5  # Y value of map dimension
# SCREEN_WIDTH = (MAP_SIZE_X) * 32
# SCREEN_HEIGHT = (MAP_SIZE_Y) * 32
#
# # Friendly agents
# F_ACTORS = 1  # Number of agents in the team
# F_START_LOC = ["1,2"]  # Starting locations for each agent
# F_GOAL_LOC = ["5,4"]  # Objectives the agents need to visit to win
#
# # Enemy agents
# E_ACTORS = 1  # Number of agents in the team
# E_START_LOC = ["4,3"]
# E_PATROL_RANGE = 5
#
# # Distractor agents
# D_ACTORS = 1
# D_START_LOC = ["0,0"]  # Base location, also the start location of distractor
#
# # Reward weights - variables
# BASE = [0.5, 0.2]  # Minimize distractor and enemy distance, minimize distractor cost
# DISTRACTOR = [-1.0, 1.0]  # Minimize agent and enemy distance
# ENEMY = [0.5, 0.6,
#          -1.0]  # Minimize agent and enemy distance, minimize enemy and distractor distance, minimize agent and goal distance
# AGENT = [1.0, -0.5]  # Minimize agent and goal distance, maximize agent and enemy distance


def f_get_current_x(world, actor):
    return world.getState(actor.name, 'x').domain()[0]


def f_get_current_y(world, actor):
    return world.getState(actor.name, 'y').domain()[0]


def f_get_start_x(index):
    return int((F_START_LOC[index]).split(",", 1)[0])


def f_get_start_y(index):
    return int((F_START_LOC[index]).split(",", 1)[1])


def f_get_goal_x(index):
    return int((F_GOAL_LOC[index]).split(",", 1)[0])


def f_get_goal_y(index):
    return int((F_GOAL_LOC[index]).split(",", 1)[1])


def e_get_current_x(world, actor):
    return world.getState(actor.name, 'x').domain()[0]


def e_get_current_y(world, actor):
    return world.getState(actor.name, 'y').domain()[0]


def e_get_start_x(index):
    return int((E_START_LOC[index]).split(",", 1)[0])


def e_get_start_y(index):
    return int((E_START_LOC[index]).split(",", 1)[1])


def d_get_start_x(index):
    return int((D_START_LOC[index]).split(",", 1)[0])


def d_get_start_y(index):
    return int((D_START_LOC[index]).split(",", 1)[1])


def find_distance(start_x, start_y, goal_x, goal_y):
    return abs(goal_x - start_x) + abs(goal_y - start_y)


def create_base(world):
    base = Agent('Base')
    world.addAgent(base)
    base.setHorizon(5)

    world.defineState(base.name, 'x', int)
    world.setState(base.name, 'x', 0)

    world.defineState(base.name, 'y', int)
    world.setState(base.name, 'y', 0)

    # Deploy distractor
    action = base.addAction({'verb': 'Deploy'})
    tree = makeTree(setToConstantMatrix(stateKey('Distractor0', 'deployed'), True))
    world.setDynamics(stateKey('Distractor0', 'deployed'), action, tree)

    # Nop
    action = base.addAction({'verb': 'Wait'})
    tree = makeTree(incrementMatrix(stateKey(action['subject'], 'x'), 0.))
    world.setDynamics(stateKey(action['subject'], 'x'), action, tree)
    tree = makeTree(incrementMatrix(stateKey(action['subject'], 'y'), 0.))
    world.setDynamics(stateKey(action['subject'], 'y'), action, tree)

    base.setReward(minimizeDifference(stateKey('Distractor0', 'x'), stateKey('Enemy0', 'x')), BASE[0])
    base.setReward(minimizeDifference(stateKey('Distractor0', 'y'), stateKey('Enemy0', 'y')), BASE[0])
    base.setReward(minimizeFeature(stateKey('Distractor0', 'cost')), BASE[1])


def create_friendly_agents(world):
    for index in range(0, F_ACTORS):
        actor = Agent('Actor' + str(index))
        world.addAgent(actor)
        actor.setHorizon(5)

        # Set agent's starting location
        world.defineState(actor.name, 'x', int)
        world.setState(actor.name, 'x', f_get_start_x(index))
        world.defineState(actor.name, 'goal_x', int)
        world.setState(actor.name, 'goal_x', f_get_goal_x(index))

        world.defineState(actor.name, 'y', int)
        world.setState(actor.name, 'y', f_get_start_y(index))
        world.defineState(actor.name, 'goal_y', int)
        world.setState(actor.name, 'goal_y', f_get_goal_y(index))

        # Positive reward for going towards goal
        actor.setReward(minimizeDifference(stateKey(actor.name, 'x'), stateKey(actor.name, 'goal_x')), AGENT[0])
        actor.setReward(minimizeDifference(stateKey(actor.name, 'y'), stateKey(actor.name, 'goal_y')), AGENT[0])

        # Negative reward for going towards enemy
        for i in range(0, E_ACTORS):
            enemy = 'Enemy' + str(i)
            actor.setReward(minimizeDifference(stateKey(actor.name, 'x'), stateKey(enemy, 'x')), AGENT[1])
            actor.setReward(minimizeDifference(stateKey(actor.name, 'y'), stateKey(enemy, 'y')), AGENT[1])

        # Terminate if agent reaches goal
        tree = makeTree({'if': equalFeatureRow(stateKey(actor.name, 'x'), stateKey(actor.name, 'goal_x')),
                         True: {'if': equalFeatureRow(stateKey(actor.name, 'y'), stateKey(actor.name, 'goal_y')),
                                True: True,
                                False: False},
                         False: False})
        world.addTermination(tree)

        set_friendly_actions(world, actor)


def set_friendly_actions(world, actor):
    # Nop
    action = actor.addAction({'verb': 'Wait'})
    tree = makeTree(incrementMatrix(stateKey(action['subject'], 'x'), 0.))
    world.setDynamics(stateKey(action['subject'], 'x'), action, tree)
    tree = makeTree(incrementMatrix(stateKey(action['subject'], 'y'), 0.))
    world.setDynamics(stateKey(action['subject'], 'y'), action, tree)

    # Increment X position
    action = actor.addAction({'verb': 'MoveRight'})
    tree = makeTree(incrementMatrix(stateKey(action['subject'], 'x'), 1.))
    world.setDynamics(stateKey(action['subject'], 'x'), action, tree)

    # Rightmost boundary check
    tree = makeTree({'if': equalRow(stateKey(actor.name, 'x'), str(MAP_SIZE_X)),
                     True: False, False: True})
    actor.setLegal(action, tree)

    ##############################

    # Decrement X position
    action = actor.addAction({'verb': 'MoveLeft'})
    tree = makeTree(incrementMatrix(stateKey(action['subject'], 'x'), -1.))
    world.setDynamics(stateKey(action['subject'], 'x'), action, tree)

    # Leftmost boundary check, min X = 0
    tree = makeTree({'if': equalRow(stateKey(actor.name, 'x'), '0'),
                     True: False, False: True})
    actor.setLegal(action, tree)

    ##############################

    # Increment Y position
    action = actor.addAction({'verb': 'MoveUp'})
    tree = makeTree(incrementMatrix(stateKey(action['subject'], 'y'), 1.))
    world.setDynamics(stateKey(action['subject'], 'y'), action, tree)

    # Downmost boundary check, max Y
    tree = makeTree({'if': equalRow(stateKey(actor.name, 'y'), MAP_SIZE_Y - 1),
                     True: False, False: True})
    actor.setLegal(action, tree)

    ##############################

    # Decrement Y position
    action = actor.addAction({'verb': 'MoveDown'})
    tree = makeTree(incrementMatrix(stateKey(action['subject'], 'y'), -1.))
    world.setDynamics(stateKey(action['subject'], 'y'), action, tree)

    # Upmost boundary check, min Y = 0
    tree = makeTree({'if': equalRow(stateKey(actor.name, 'y'), '0'),
                     True: False, False: True})
    actor.setLegal(action, tree)


def create_distract_agents(world):
    for index in range(0, D_ACTORS):
        actor = Agent('Distractor' + str(index))
        world.addAgent(actor)
        actor.setHorizon(5)

        # Agent is not allowed to move if not deployed by the base
        world.defineState(actor.name, 'deployed', bool)
        world.setState(actor.name, 'deployed', False)

        # Every time the agent makes an action, there is a cost associated
        world.defineState(actor.name, 'cost', int)
        world.setState(actor.name, 'cost', 0)

        # Set agent's starting location
        world.defineState(actor.name, 'x', int)
        world.setState(actor.name, 'x', 0)

        world.defineState(actor.name, 'y', int)
        world.setState(actor.name, 'y', 0)

        # Positive reward for luring enemy away from Agents
        actor.setReward(minimizeDifference(stateKey('Actor' + str(index), 'x'), stateKey('Enemy' + str(index), 'x')),
                        DISTRACTOR[0])
        actor.setReward(minimizeDifference(stateKey('Actor' + str(index), 'y'), stateKey('Enemy' + str(index), 'y')),
                        DISTRACTOR[0])

        # Positive reward for moving closer to enemy
        actor.setReward(
            minimizeDifference(stateKey('Distractor' + str(index), 'x'), stateKey('Enemy' + str(index), 'x')),
            DISTRACTOR[1])
        actor.setReward(
            minimizeDifference(stateKey('Distractor' + str(index), 'y'), stateKey('Enemy' + str(index), 'y')),
            DISTRACTOR[1])

        set_distract_actions(world, actor)


def set_distract_actions(world, actor):
    # Nop
    action = actor.addAction({'verb': 'Wait'})
    tree = makeTree(incrementMatrix(stateKey(action['subject'], 'x'), 0.))
    world.setDynamics(stateKey(action['subject'], 'x'), action, tree)
    tree = makeTree(incrementMatrix(stateKey(action['subject'], 'y'), 0.))
    world.setDynamics(stateKey(action['subject'], 'y'), action, tree)
    # Reward for not moving
    tree = makeTree(incrementMatrix(stateKey(action['subject'], 'cost'), -1.))
    world.setDynamics(stateKey(action['subject'], 'cost'), action, tree)

    # Increment X position
    action = actor.addAction({'verb': 'MoveRight'})
    tree = makeTree(incrementMatrix(stateKey(action['subject'], 'x'), 1.))
    world.setDynamics(stateKey(action['subject'], 'x'), action, tree)

    # Cost for moving
    tree = makeTree(incrementMatrix(stateKey(action['subject'], 'cost'), 1.))
    world.setDynamics(stateKey(action['subject'], 'cost'), action, tree)

    # Rightmost boundary check
    tree = makeTree({'if': equalRow(stateKey(actor.name, 'deployed'), True),
                     True: {'if': equalRow(stateKey(actor.name, 'x'), str(MAP_SIZE_X)),
                            True: False, False: True}, False: False})
    actor.setLegal(action, tree)

    ##############################

    # Decrement X position
    action = actor.addAction({'verb': 'MoveLeft'})
    tree = makeTree(incrementMatrix(stateKey(action['subject'], 'x'), -1.))
    world.setDynamics(stateKey(action['subject'], 'x'), action, tree)

    # Cost for moving
    tree = makeTree(incrementMatrix(stateKey(action['subject'], 'cost'), 1.))
    world.setDynamics(stateKey(action['subject'], 'cost'), action, tree)

    # Leftmost boundary check, min X = 0
    tree = makeTree({'if': equalRow(stateKey(actor.name, 'deployed'), True),
                     True: {'if': equalRow(stateKey(actor.name, 'x'), 0),
                            True: False, False: True}, False: False})
    actor.setLegal(action, tree)

    ##############################

    # Increment Y position
    action = actor.addAction({'verb': 'MoveUp'})
    tree = makeTree(incrementMatrix(stateKey(action['subject'], 'y'), 1.))
    world.setDynamics(stateKey(action['subject'], 'y'), action, tree)

    # Cost for moving
    tree = makeTree(incrementMatrix(stateKey(action['subject'], 'cost'), 1.))
    world.setDynamics(stateKey(action['subject'], 'cost'), action, tree)

    # Downmost boundary check, max Y
    tree = makeTree({'if': equalRow(stateKey(actor.name, 'deployed'), True),
                     True: {'if': equalRow(stateKey(actor.name, 'y'), str(MAP_SIZE_Y)),
                            True: False, False: True}, False: False})
    actor.setLegal(action, tree)

    ##############################

    # Decrement Y position
    action = actor.addAction({'verb': 'MoveDown'})
    tree = makeTree(incrementMatrix(stateKey(action['subject'], 'y'), -1.))
    world.setDynamics(stateKey(action['subject'], 'y'), action, tree)

    # Cost for moving
    tree = makeTree(incrementMatrix(stateKey(action['subject'], 'cost'), 1.))
    world.setDynamics(stateKey(action['subject'], 'cost'), action, tree)

    # Upmost boundary check, min Y = 0
    tree = makeTree({'if': equalRow(stateKey(actor.name, 'deployed'), True),
                     True: {'if': equalRow(stateKey(actor.name, 'Y'), 0),
                            True: False, False: True}, False: False})
    actor.setLegal(action, tree)


def create_enemy_agents(world):
    for index in range(0, E_ACTORS):
        actor = Agent('Enemy' + str(index))
        world.addAgent(actor)
        actor.setHorizon(5)

        # Set agent's starting location
        world.defineState(actor.name, 'x', int)
        world.setState(actor.name, 'x', e_get_start_x(index))

        world.defineState(actor.name, 'y', int)
        world.setState(actor.name, 'y', e_get_start_y(index))

        enemy = 'Actor' + str(index)
        actor.setReward(minimizeDifference(stateKey(actor.name, 'x'), stateKey(enemy, 'x')), ENEMY[0])
        actor.setReward(minimizeDifference(stateKey(actor.name, 'y'), stateKey(enemy, 'y')), ENEMY[0])

        actor.setReward(minimizeDifference(stateKey(actor.name, 'x'), stateKey('Distractor' + str(index), 'x')),
                        ENEMY[1])
        actor.setReward(minimizeDifference(stateKey(actor.name, 'y'), stateKey('Distractor' + str(index), 'y')),
                        ENEMY[1])

        # actor.setReward(minimizeDifference(stateKey(enemy, 'x'), stateKey(enemy, 'goal_x')), ENEMY[2])
        # actor.setReward(minimizeDifference(stateKey(enemy, 'y'), stateKey(enemy, 'goal_y')), ENEMY[2])

        set_enemy_actions(world, actor, index)

        # Terminate if enemy captures agent
        tree = {'if': equalFeatureRow(stateKey(actor.name, 'x'), stateKey('Actor' + str(index), 'x')),
                True: {'if': equalFeatureRow(stateKey(actor.name, 'y'), stateKey('Actor' + str(index), 'y')),
                       True: True, False: False},
                False: False}
        world.addTermination(makeTree(tree))


def set_enemy_actions(world, actor, index):
    # Nop
    action = actor.addAction({'verb': 'Wait'})
    tree = makeTree(incrementMatrix(stateKey(action['subject'], 'x'), 0.))
    world.setDynamics(stateKey(action['subject'], 'x'), action, tree)
    tree = makeTree(incrementMatrix(stateKey(action['subject'], 'y'), 0.))
    world.setDynamics(stateKey(action['subject'], 'y'), action, tree)

    # Increment X position
    action = actor.addAction({'verb': 'MoveRight'})
    tree = makeTree(incrementMatrix(stateKey(action['subject'], 'x'), 1.))
    world.setDynamics(stateKey(action['subject'], 'x'), action, tree)

    # Rightmost boundary check
    tree = makeTree({'if': equalRow(stateKey(actor.name, 'x'), str(e_get_start_x(index) + E_PATROL_RANGE)),
                     True: False, False: True})
    actor.setLegal(action, tree)

    ##############################

    # Decrement X position
    action = actor.addAction({'verb': 'MoveLeft'})
    tree = makeTree(incrementMatrix(stateKey(action['subject'], 'x'), -1.))
    world.setDynamics(stateKey(action['subject'], 'x'), action, tree)

    # Leftmost boundary check, min X = 0
    tree = makeTree({'if': equalRow(stateKey(actor.name, 'x'), str(e_get_start_x(index) - E_PATROL_RANGE)),
                     True: False, False: True})
    actor.setLegal(action, tree)

    ##############################

    # Increment Y position
    action = actor.addAction({'verb': 'MoveUp'})
    tree = makeTree(incrementMatrix(stateKey(action['subject'], 'y'), 1.))
    world.setDynamics(stateKey(action['subject'], 'y'), action, tree)

    # Downmost boundary check, max Y
    tree = makeTree({'if': equalRow(stateKey(actor.name, 'y'), str(e_get_start_y(index) + E_PATROL_RANGE)),
                     True: False, False: True})
    actor.setLegal(action, tree)

    ##############################

    # Decrement Y position
    action = actor.addAction({'verb': 'MoveDown'})
    tree = makeTree(incrementMatrix(stateKey(action['subject'], 'y'), -1.))
    world.setDynamics(stateKey(action['subject'], 'y'), action, tree)

    # Upmost boundary check, min Y = 0
    tree = makeTree({'if': equalRow(stateKey(actor.name, 'y'), str(e_get_start_y(index) - E_PATROL_RANGE)),
                     True: False, False: True})
    actor.setLegal(action, tree)


if __name__ == '__main__':
    master = loader.Tk()
    app = loader.BaseLoader(master)
    Thread(target=master.mainloop()).start()
    while not loader.ready:
        x = 1
    MAP_SIZE_X = loader.MAP_SIZE_X
    MAP_SIZE_Y = loader.MAP_SIZE_Y
    F_ACTORS = loader.F_ACTORS
    F_START_LOC = loader.F_START_LOC
    F_GOAL_LOC = loader.F_GOAL_LOC
    E_ACTORS = loader.E_ACTORS
    E_START_LOC = loader.E_START_LOC
    D_ACTORS = loader.D_ACTORS
    D_START_LOC = loader.D_START_LOC
    BASE = loader.BASE
    DISTRACTOR = loader.DISTRACTOR
    ENEMY = loader.ENEMY
    AGENT = loader.AGENT

    world = World()
    create_friendly_agents(world)
    create_enemy_agents(world)
    create_distract_agents(world)
    create_base(world)

    # Parallel action
    # world.setOrder([set(world.agents.keys())])
    # Sequential action
    world.setOrder(world.agents.keys())

    ##### Begin pyglet visualization code ######
    pyglet.resource.path = ['../resources']
    pyglet.resource.reindex()

    SCREEN_WIDTH = (MAP_SIZE_X) * 32
    SCREEN_HEIGHT = (MAP_SIZE_Y) * 32
    window = pyglet.window.Window(resizable=True)
    window.set_size(SCREEN_WIDTH, SCREEN_HEIGHT)

    tile_image = pyglet.resource.image("grass.png")
    tiles_batch = pyglet.graphics.Batch()
    tiles = []
    for y in range(0, MAP_SIZE_Y):
        for x in range(0, MAP_SIZE_X):
            tiles.append(pyglet.sprite.Sprite(
                img=tile_image,
                x=x * 32,
                y=y * 32,
                batch=tiles_batch)
            )

    goal_image = pyglet.resource.image("target.png")
    goals_batch = pyglet.graphics.Batch()
    goals = []
    for index in range(0, len(F_GOAL_LOC)):
        goals.append(pyglet.sprite.Sprite(
            img=goal_image,
            x=f_get_goal_x(index) * 32,
            y=f_get_goal_y(index) * 32,
            batch=goals_batch)
        )

    agent_image = pyglet.resource.image("soldier_blue.png")
    agents_batch = pyglet.graphics.Batch()
    agents = []
    for index in range(0, F_ACTORS):
        agents.append(pyglet.sprite.Sprite(
            img=agent_image,
            x=f_get_start_x(index) * 32,
            y=f_get_start_y(index) * 32,
            batch=agents_batch)
        )

    enemy_image = pyglet.resource.image("soldier_red.png")
    enemies_batch = pyglet.graphics.Batch()
    enemies = []
    for index in range(0, E_ACTORS):
        enemies.append(pyglet.sprite.Sprite(
            img=enemy_image,
            x=e_get_start_x(index) * 32,
            y=e_get_start_y(index) * 32,
            batch=enemies_batch)
        )

    distractor_image = pyglet.resource.image("heli.png")
    base_image = pyglet.resource.image("base.png")
    allies_batch = pyglet.graphics.Batch()
    bases = []
    distractors = []
    for index in range(0, D_ACTORS):
        bases.append(pyglet.sprite.Sprite(
            img=base_image,
            x=d_get_start_x(index) * 32,
            y=d_get_start_y(index) * 32,
            batch=allies_batch)
        )
        distractors.append(pyglet.sprite.Sprite(
            img=distractor_image,
            x=d_get_start_x(index) * 32,
            y=d_get_start_y(index) * 32,
            batch=allies_batch)
        )


    @window.event
    def on_draw():
        window.clear()
        tiles_batch.draw()
        goals_batch.draw()
        agents_batch.draw()
        enemies_batch.draw()
        allies_batch.draw()

    paused = False


    @window.event
    def on_key_press(symbol, modifiers):
        global paused
        if symbol == key.P:
            paused = True
            print('Paused')
        if symbol == key.U:
            paused = False
            print('Resumed')


    def update(dt):
        global paused
        if not paused:
            result = world.step()
            world.explain(result, 2)

        for index in range(0, F_ACTORS):
            agents[index].x = int(world.getState('Actor' + str(index), 'x').domain()[0]) * 32
            agents[index].y = int(world.getState('Actor' + str(index), 'y').domain()[0]) * 32

        for index in range(0, E_ACTORS):
            enemies[index].x = int(world.getState('Enemy' + str(index), 'x').domain()[0]) * 32
            enemies[index].y = int(world.getState('Enemy' + str(index), 'y').domain()[0]) * 32

        for index in range(0, D_ACTORS):
            distractors[index].x = int(world.getState('Distractor' + str(index), 'x').domain()[0]) * 32
            distractors[index].y = int(world.getState('Distractor' + str(index), 'y').domain()[0]) * 32
    ###### End pyglet visualization code ######


    pyglet.clock.schedule_interval(update, 1)
    Thread(target=pyglet.app.run()).start()

    print('RUN COMPLETE!')
