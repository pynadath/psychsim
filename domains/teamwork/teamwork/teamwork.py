# Team of agents that attempts to capture a flag without being caught by enemies
# Agents:
# Explorer - minimize distance between self and goal location
# Distractor - maximize distance between explorer and enemy (new)
# Enemy - minimize distance between self and explorer and distractor
# Base - deploy distractor when explorer in danger (new)

from __future__ import print_function, division
from psychsim.reward import *
from psychsim.pwl import *
from psychsim.action import *
from psychsim.world import *
from psychsim.agent import *
import pyglet
from pyglet.window import key
from threading import Thread
from time import time
import os

class Scenario:
    def __init__(self,
                 MAP_SIZE_X=0,
                 MAP_SIZE_Y=0,
                 F_ACTORS=0,
                 F_START_LOC=[],
                 F_GOAL_LOC=[],
                 E_ACTORS=0,
                 E_START_LOC=[],
                 E_PATROL_RANGE=5,
                 D_ACTORS=0,
                 D_START_LOC=[],
                 BASE=[0.0, 0.0],
                 DISTRACTOR=[0.0, 0.0],
                 ENEMY=[0.0, 0.0, 0.0],
                 AGENT=[0.0, 0.0]):

        self.MAP_SIZE_X = MAP_SIZE_X
        self.MAP_SIZE_Y = MAP_SIZE_Y
        self.F_ACTORS = F_ACTORS
        self.F_START_LOC = F_START_LOC
        self.F_GOAL_LOC = F_GOAL_LOC
        self.E_ACTORS = E_ACTORS
        self.E_START_LOC = E_START_LOC
        self.E_PATROL_RANGE = E_PATROL_RANGE
        self.D_ACTORS = D_ACTORS
        self.D_START_LOC = D_START_LOC
        self.BASE = BASE
        self.DISTRACTOR = DISTRACTOR
        self.ENEMY = ENEMY
        self.AGENT = AGENT

        self.world = World()
        self.world.defineState(None, 'turns', int)
        self.world.setState(None, 'turns', 0)
        self.world.addTermination(makeTree({'if': thresholdRow(stateKey(None, 'turns'), 20),
                                            True: True, False: False}))
        self.create_friendly_agents()
        self.create_enemy_agents()
        self.create_distract_agents()
        self.create_base()

        self.paused = False

        # Parallel action
        # self.world.setOrder([set(self.world.agents.keys())])
        # Sequential action
        self.world.setOrder(self.world.agents.keys())

    def f_get_current_x(self, actor):
        return self.world.getState(actor.name, 'x').domain()[0]

    def f_get_current_y(self, actor):
        return self.world.getState(actor.name, 'y').domain()[0]

    def f_get_start_x(self, index):
        return int((self.F_START_LOC[index]).split(",", 1)[0])

    def f_get_start_y(self, index):
        return int((self.F_START_LOC[index]).split(",", 1)[1])

    def f_get_goal_x(self, index):
        return int((self.F_GOAL_LOC[index]).split(",", 1)[0])

    def f_get_goal_y(self, index):
        return int((self.F_GOAL_LOC[index]).split(",", 1)[1])

    def e_get_current_x(self, actor):
        return self.world.getState(actor.name, 'x').domain()[0]

    def e_get_current_y(self, actor):
        return self.world.getState(actor.name, 'y').domain()[0]

    def e_get_start_x(self, index):
        return int((self.E_START_LOC[index]).split(",", 1)[0])

    def e_get_start_y(self, index):
        return int((self.E_START_LOC[index]).split(",", 1)[1])

    def d_get_start_x(self, index):
        return int((self.D_START_LOC[index]).split(",", 1)[0])

    def d_get_start_y(self, index):
        return int((self.D_START_LOC[index]).split(",", 1)[1])

    def find_distance(self, start_x, start_y, goal_x, goal_y):
        return abs(goal_x - start_x) + abs(goal_y - start_y)

    def create_base(self):
        for index in range(0, self.D_ACTORS):
            base = Agent('Base' + str(index))
            self.world.addAgent(base)
            base.setHorizon(5)

            self.world.defineState(base.name, 'x', int)
            self.world.setState(base.name, 'x', 0)

            self.world.defineState(base.name, 'y', int)
            self.world.setState(base.name, 'y', 0)

            # Deploy distractor
            action = base.addAction({'verb': 'Deploy'})
            tree = makeTree(setToConstantMatrix(stateKey('Distractor' + str(index), 'deployed'), True))
            self.world.setDynamics(stateKey('Distractor' + str(index), 'deployed'), action, tree)

            # Nop
            action = base.addAction({'verb': 'Wait'})
            tree = makeTree(incrementMatrix(stateKey(action['subject'], 'x'), 0.))
            self.world.setDynamics(stateKey(action['subject'], 'x'), action, tree)
            tree = makeTree(incrementMatrix(stateKey(action['subject'], 'y'), 0.))
            self.world.setDynamics(stateKey(action['subject'], 'y'), action, tree)

            base.setReward(
                minimizeDifference(stateKey('Distractor' + str(index), 'x'), stateKey('Enemy' + str(index), 'x')),
                self.BASE[0])
            base.setReward(
                minimizeDifference(stateKey('Distractor' + str(index), 'y'), stateKey('Enemy' + str(index), 'y')),
                self.BASE[0])

            base.setReward(minimizeFeature(stateKey('Distractor' + str(index), 'cost')), self.BASE[1])

    def create_friendly_agents(self):
        for index in range(0, self.F_ACTORS):
            actor = Agent('Actor' + str(index))
            self.world.addAgent(actor)
            actor.setHorizon(5)

            # Set agent's starting location
            self.world.defineState(actor.name, 'x', int)
            self.world.setState(actor.name, 'x', self.f_get_start_x(index))
            self.world.defineState(actor.name, 'goal_x', int)
            self.world.setState(actor.name, 'goal_x', self.f_get_goal_x(index))

            self.world.defineState(actor.name, 'y', int)
            self.world.setState(actor.name, 'y', self.f_get_start_y(index))
            self.world.defineState(actor.name, 'goal_y', int)
            self.world.setState(actor.name, 'goal_y', self.f_get_goal_y(index))

            # Positive reward for going towards goal
            actor.setReward(minimizeDifference(stateKey(actor.name, 'x'), stateKey(actor.name, 'goal_x')),
                            self.AGENT[0])
            actor.setReward(minimizeDifference(stateKey(actor.name, 'y'), stateKey(actor.name, 'goal_y')),
                            self.AGENT[0])

            # Negative reward for going towards enemy
            enemy = 'Enemy' + str(index)
            actor.setReward(minimizeDifference(stateKey(actor.name, 'x'), stateKey(enemy, 'x')), self.AGENT[1])
            actor.setReward(minimizeDifference(stateKey(actor.name, 'y'), stateKey(enemy, 'y')), self.AGENT[1])

            self.set_friendly_actions(actor)

            # Terminate if agent reaches goal
            tree = makeTree({'if': equalFeatureRow(stateKey(actor.name, 'x'), stateKey(actor.name, 'goal_x')),
                             True: {'if': equalFeatureRow(stateKey(actor.name, 'y'), stateKey(actor.name, 'goal_y')),
                                    True: True,
                                    False: False},
                             False: False})
            self.world.addTermination(tree)


    def set_friendly_actions(self, actor):
        # Nop
        action = actor.addAction({'verb': 'Wait'})
        tree = makeTree(incrementMatrix(stateKey(action['subject'], 'x'), 0.))
        self.world.setDynamics(stateKey(action['subject'], 'x'), action, tree)
        tree = makeTree(incrementMatrix(stateKey(action['subject'], 'y'), 0.))
        self.world.setDynamics(stateKey(action['subject'], 'y'), action, tree)
        tree = makeTree(incrementMatrix('turns', 1.0))
        self.world.setDynamics(stateKey(None, 'turns'), action, tree)

        # Increment X position
        action = actor.addAction({'verb': 'MoveRight'})
        tree = makeTree(incrementMatrix(stateKey(action['subject'], 'x'), 1.))
        self.world.setDynamics(stateKey(action['subject'], 'x'), action, tree)
        tree = makeTree(incrementMatrix('turns', 1.0))
        self.world.setDynamics('turns', action, tree)

        # Rightmost boundary check
        tree = makeTree({'if': equalRow(stateKey(actor.name, 'x'), str(self.MAP_SIZE_X)),
                         True: False, False: True})
        actor.setLegal(action, tree)

        ##############################

        # Decrement X position
        action = actor.addAction({'verb': 'MoveLeft'})
        tree = makeTree(incrementMatrix(stateKey(action['subject'], 'x'), -1.))
        self.world.setDynamics(stateKey(action['subject'], 'x'), action, tree)
        tree = makeTree(incrementMatrix('turns', 1.0))
        self.world.setDynamics(stateKey(None, 'turns'), action, tree)

        # Leftmost boundary check, min X = 0
        tree = makeTree({'if': equalRow(stateKey(actor.name, 'x'), '0'),
                         True: False, False: True})
        actor.setLegal(action, tree)

        ##############################

        # Increment Y position
        action = actor.addAction({'verb': 'MoveUp'})
        tree = makeTree(incrementMatrix(stateKey(action['subject'], 'y'), 1.))
        self.world.setDynamics(stateKey(action['subject'], 'y'), action, tree)
        tree = makeTree(incrementMatrix('turns', 1.0))
        self.world.setDynamics(stateKey(None, 'turns'), action, tree)

        # Downmost boundary check, max Y
        tree = makeTree({'if': equalRow(stateKey(actor.name, 'y'), self.MAP_SIZE_Y - 1),
                         True: False, False: True})
        actor.setLegal(action, tree)

        ##############################

        # Decrement Y position
        action = actor.addAction({'verb': 'MoveDown'})
        tree = makeTree(incrementMatrix(stateKey(action['subject'], 'y'), -1.))
        self.world.setDynamics(stateKey(action['subject'], 'y'), action, tree)
        tree = makeTree(incrementMatrix('turns', 1.0))
        self.world.setDynamics(stateKey(None, 'turns'), action, tree)

        # Upmost boundary check, min Y = 0
        tree = makeTree({'if': equalRow(stateKey(actor.name, 'y'), '0'),
                         True: False, False: True})
        actor.setLegal(action, tree)

    def create_distract_agents(self):
        for index in range(0, self.D_ACTORS):
            actor = Agent('Distractor' + str(index))
            self.world.addAgent(actor)
            actor.setHorizon(5)

            # Agent is not allowed to move if not deployed by the base
            self.world.defineState(actor.name, 'deployed', bool)
            self.world.setState(actor.name, 'deployed', False)

            # Every time the agent makes an action, there is a cost associated
            self.world.defineState(actor.name, 'cost', int)
            self.world.setState(actor.name, 'cost', 0)

            # Set agent's starting location
            self.world.defineState(actor.name, 'x', int)
            self.world.setState(actor.name, 'x', 0)

            self.world.defineState(actor.name, 'y', int)
            self.world.setState(actor.name, 'y', 0)

            # Positive reward for luring enemy away from Agents
            actor.setReward(
                minimizeDifference(stateKey('Actor' + str(index), 'x'), stateKey('Enemy' + str(index), 'x')),
                self.DISTRACTOR[0])
            actor.setReward(
                minimizeDifference(stateKey('Actor' + str(index), 'y'), stateKey('Enemy' + str(index), 'y')),
                self.DISTRACTOR[0])

            # Positive reward for moving closer to enemy
            actor.setReward(
                minimizeDifference(stateKey('Distractor' + str(index), 'x'), stateKey('Enemy' + str(index), 'x')),
                self.DISTRACTOR[1])
            actor.setReward(
                minimizeDifference(stateKey('Distractor' + str(index), 'y'), stateKey('Enemy' + str(index), 'y')),
                self.DISTRACTOR[1])

            self.set_distract_actions(actor)

    def set_distract_actions(self, actor):
        # Nop
        action = actor.addAction({'verb': 'Wait'})
        tree = makeTree(incrementMatrix(stateKey(action['subject'], 'x'), 0.))
        self.world.setDynamics(stateKey(action['subject'], 'x'), action, tree)
        tree = makeTree(incrementMatrix(stateKey(action['subject'], 'y'), 0.))
        self.world.setDynamics(stateKey(action['subject'], 'y'), action, tree)
        # Reward for not moving
        tree = makeTree(incrementMatrix(stateKey(action['subject'], 'cost'), -1.))
        self.world.setDynamics(stateKey(action['subject'], 'cost'), action, tree)

        # Increment X position
        action = actor.addAction({'verb': 'MoveRight'})
        tree = makeTree(incrementMatrix(stateKey(action['subject'], 'x'), 1.))
        self.world.setDynamics(stateKey(action['subject'], 'x'), action, tree)

        # Cost for moving
        tree = makeTree(incrementMatrix(stateKey(action['subject'], 'cost'), 1.))
        self.world.setDynamics(stateKey(action['subject'], 'cost'), action, tree)

        # Rightmost boundary check
        tree = makeTree({'if': equalRow(stateKey(actor.name, 'deployed'), True),
                         True: {'if': equalRow(stateKey(actor.name, 'x'), str(self.MAP_SIZE_X)),
                                True: False, False: True}, False: False})
        actor.setLegal(action, tree)

        ##############################

        # Decrement X position
        action = actor.addAction({'verb': 'MoveLeft'})
        tree = makeTree(incrementMatrix(stateKey(action['subject'], 'x'), -1.))
        self.world.setDynamics(stateKey(action['subject'], 'x'), action, tree)

        # Cost for moving
        tree = makeTree(incrementMatrix(stateKey(action['subject'], 'cost'), 1.))
        self.world.setDynamics(stateKey(action['subject'], 'cost'), action, tree)

        # Leftmost boundary check, min X = 0
        tree = makeTree({'if': equalRow(stateKey(actor.name, 'deployed'), True),
                         True: {'if': equalRow(stateKey(actor.name, 'x'), 0),
                                True: False, False: True}, False: False})
        actor.setLegal(action, tree)

        ##############################

        # Increment Y position
        action = actor.addAction({'verb': 'MoveUp'})
        tree = makeTree(incrementMatrix(stateKey(action['subject'], 'y'), 1.))
        self.world.setDynamics(stateKey(action['subject'], 'y'), action, tree)

        # Cost for moving
        tree = makeTree(incrementMatrix(stateKey(action['subject'], 'cost'), 1.))
        self.world.setDynamics(stateKey(action['subject'], 'cost'), action, tree)

        # Downmost boundary check, max Y
        tree = makeTree({'if': equalRow(stateKey(actor.name, 'deployed'), True),
                         True: {'if': equalRow(stateKey(actor.name, 'y'), str(self.MAP_SIZE_Y)),
                                True: False, False: True}, False: False})
        actor.setLegal(action, tree)

        ##############################

        # Decrement Y position
        action = actor.addAction({'verb': 'MoveDown'})
        tree = makeTree(incrementMatrix(stateKey(action['subject'], 'y'), -1.))
        self.world.setDynamics(stateKey(action['subject'], 'y'), action, tree)

        # Cost for moving
        tree = makeTree(incrementMatrix(stateKey(action['subject'], 'cost'), 1.))
        self.world.setDynamics(stateKey(action['subject'], 'cost'), action, tree)

        # Upmost boundary check, min Y = 0
        tree = makeTree({'if': equalRow(stateKey(actor.name, 'deployed'), True),
                         True: {'if': equalRow(stateKey(actor.name, 'Y'), 0),
                                True: False, False: True}, False: False})
        actor.setLegal(action, tree)

    def create_enemy_agents(self):
        for index in range(0, self.E_ACTORS):
            actor = Agent('Enemy' + str(index))
            self.world.addAgent(actor)
            actor.setHorizon(5)

            # Set agent's starting location
            self.world.defineState(actor.name, 'x', int)
            self.world.setState(actor.name, 'x', self.e_get_start_x(index))

            self.world.defineState(actor.name, 'y', int)
            self.world.setState(actor.name, 'y', self.e_get_start_y(index))

            enemy = 'Actor' + str(index)
            actor.setReward(minimizeDifference(stateKey(actor.name, 'x'), stateKey(enemy, 'x')), self.ENEMY[0])
            actor.setReward(minimizeDifference(stateKey(actor.name, 'y'), stateKey(enemy, 'y')), self.ENEMY[0])

            actor.setReward(minimizeDifference(stateKey(actor.name, 'x'), stateKey('Distractor' + str(index), 'x')),
                            self.ENEMY[1])
            actor.setReward(minimizeDifference(stateKey(actor.name, 'y'), stateKey('Distractor' + str(index), 'y')),
                            self.ENEMY[1])

            # actor.setReward(minimizeDifference(stateKey(enemy, 'x'), stateKey(enemy, 'goal_x')), self.ENEMY[2])
            # actor.setReward(minimizeDifference(stateKey(enemy, 'y'), stateKey(enemy, 'goal_y')), self.ENEMY[2])

            self.set_enemy_actions(actor, index)

            # Terminate if enemy captures agent
            tree = {'if': equalFeatureRow(stateKey(actor.name, 'x'), stateKey('Actor' + str(index), 'x')),
                    True: {'if': equalFeatureRow(stateKey(actor.name, 'y'), stateKey('Actor' + str(index), 'y')),
                           True: True, False: False},
                    False: False}
            self.world.addTermination(makeTree(tree))

    def set_enemy_actions(self, actor, index):
        # Nop
        action = actor.addAction({'verb': 'Wait'})
        tree = makeTree(incrementMatrix(stateKey(action['subject'], 'x'), 0.))
        self.world.setDynamics(stateKey(action['subject'], 'x'), action, tree)
        tree = makeTree(incrementMatrix(stateKey(action['subject'], 'y'), 0.))
        self.world.setDynamics(stateKey(action['subject'], 'y'), action, tree)
        tree = makeTree(incrementMatrix('turns', 1.0))
        self.world.setDynamics(stateKey(None, 'turns'), action, tree)

        # Increment X position
        action = actor.addAction({'verb': 'MoveRight'})
        tree = makeTree(incrementMatrix(stateKey(action['subject'], 'x'), 1.))
        self.world.setDynamics(stateKey(action['subject'], 'x'), action, tree)
        tree = makeTree(incrementMatrix('turns', 1.0))
        self.world.setDynamics('turns', action, tree)

        # Rightmost boundary check
        tree = makeTree({'if': equalRow(stateKey(actor.name, 'x'), str(self.MAP_SIZE_X)),
                         True: False, False: True})
        actor.setLegal(action, tree)

        ##############################

        # Decrement X position
        action = actor.addAction({'verb': 'MoveLeft'})
        tree = makeTree(incrementMatrix(stateKey(action['subject'], 'x'), -1.))
        self.world.setDynamics(stateKey(action['subject'], 'x'), action, tree)
        tree = makeTree(incrementMatrix('turns', 1.0))
        self.world.setDynamics(stateKey(None, 'turns'), action, tree)

        # Leftmost boundary check, min X = 0
        tree = makeTree({'if': equalRow(stateKey(actor.name, 'x'), '0'),
                         True: False, False: True})
        actor.setLegal(action, tree)

        ##############################

        # Increment Y position
        action = actor.addAction({'verb': 'MoveUp'})
        tree = makeTree(incrementMatrix(stateKey(action['subject'], 'y'), 1.))
        self.world.setDynamics(stateKey(action['subject'], 'y'), action, tree)
        tree = makeTree(incrementMatrix('turns', 1.0))
        self.world.setDynamics(stateKey(None, 'turns'), action, tree)

        # Downmost boundary check, max Y
        tree = makeTree({'if': equalRow(stateKey(actor.name, 'y'), self.MAP_SIZE_Y - 1),
                         True: False, False: True})
        actor.setLegal(action, tree)

        ##############################

        # Decrement Y position
        action = actor.addAction({'verb': 'MoveDown'})
        tree = makeTree(incrementMatrix(stateKey(action['subject'], 'y'), -1.))
        self.world.setDynamics(stateKey(action['subject'], 'y'), action, tree)
        tree = makeTree(incrementMatrix('turns', 1.0))
        self.world.setDynamics(stateKey(None, 'turns'), action, tree)

        # Upmost boundary check, min Y = 0
        tree = makeTree({'if': equalRow(stateKey(actor.name, 'y'), '0'),
                         True: False, False: True})
        actor.setLegal(action, tree)

    def evaluate_score(self):
        cwd = os.getcwd()
        print(cwd)
        t = str(time())
        file = open(cwd + "\output\\" + t + ".txt", "w")
        file.write("Parameters:\n")
        file.write("Map Size X: " + str(self.MAP_SIZE_X) + "\n")
        file.write("Map Size Y: " + str(self.MAP_SIZE_Y) + "\n")
        file.write("Soldiers: " + str(self.F_ACTORS) + "\n")
        file.write("Soldier Start Locations: " + str(self.F_START_LOC) + "\n")
        file.write("Soldier Goal Locations: " + str(self.F_GOAL_LOC) + "\n")
        file.write("Enemies: " + str(self.E_ACTORS) + "\n")
        file.write("Enemy Start Locations: " + str(self.E_START_LOC) + "\n")
        file.write("Bases/Helicopters: " + str(self.D_ACTORS) + "\n")
        file.write("Base/Helicopter Start Locations: " + str(self.D_START_LOC) + "\n")
        file.write("\n \n")
        file.write("Weights:\n")
        file.write("Soldier:\n")
        file.write("Minimizing soldier and goal distance: " + str(self.AGENT[0]) + "\n")
        file.write("Minimizing soldier and enemy distance: " + str(self.AGENT[1]) + "\n")
        file.write("Enemy:\n")
        file.write("Minimizing soldier and enemy distance: " + str(self.ENEMY[0]) + "\n")
        file.write("Minimizing soldier and helicopter distance: " + str(self.ENEMY[1]) + "\n")
        file.write("Minimizing soldier and goal distance: " + str(self.ENEMY[2]) + "\n")
        file.write("Base:\n")
        file.write("Minimizing helicopter and enemy distance: " + str(self.BASE[0]) + "\n")
        file.write("Minimizing helicopter cost: " + str(self.BASE[1]) + "\n")
        file.write("Helicopter:\n")
        file.write("Minimizing helicopter and enemy distance: " + str(self.DISTRACTOR[0]) + "\n")
        file.write("Minimizing soldier and enemy distance : " + str(self.DISTRACTOR[1]) + "\n")
        file.write("\n \n")

        max_distance = self.MAP_SIZE_X + self.MAP_SIZE_Y

        file.write("Scores:\n")
        file.write("Soldier-Goal Manhattan Distance: \n")
        agent_goal_scores = []
        for index in range(0, self.F_ACTORS):
            ending_x = int(self.world.getState('Actor' + str(index), 'x').domain()[0])
            ending_y = int(self.world.getState('Actor' + str(index), 'y').domain()[0])
            soldier_goal_distance = abs(self.f_get_goal_x(index) - ending_x) + abs(
                self.f_get_goal_y(index) - ending_y)
            agent_goal_scores.append(max_distance - soldier_goal_distance)
            file.write("Soldier" + str(index) + ": " + str(agent_goal_scores[index]) + "\n")
            # print(agent_goal_scores[index])

        file.write("Soldier-Enemy Manhattan Distance: \n")
        agent_enemy_scores = []
        for index in range(0, self.F_ACTORS):
            soldier_x = int(self.world.getState('Actor' + str(index), 'x').domain()[0])
            soldier_y = int(self.world.getState('Actor' + str(index), 'y').domain()[0])
            enemy_x = int(self.world.getState('Enemy' + str(index), 'x').domain()[0])
            enemy_y = int(self.world.getState('Enemy' + str(index), 'y').domain()[0])
            soldier_enemy_distance = abs(soldier_x - enemy_x) + abs(
                soldier_y - enemy_y)
            agent_enemy_scores.append(soldier_enemy_distance - max_distance)
            file.write("Soldier" + str(index) + ": " + str(agent_enemy_scores[index]) + "\n")
            if(agent_enemy_scores[index] == 0):
                file.write("Soldier was captured, penalty awarded")
            # print(agent_enemy_scores[index])

        file.write("Helicopter Deployment Costs: \n")
        helicopter_cost_scores =[]
        for index in range(0, self.D_ACTORS):
            helicopter_score = int(self.world.getState('Distractor'+str(index), 'cost').domain()[0])
            helicopter_cost_scores.append(helicopter_score)
            file.write("Distractor"+str(index)+": "+ str(helicopter_cost_scores[index])+"\n")

        file.write("Turns Taken: \n")
        turns = int(self.world.getState(None,'turns').domain()[0])
        file.write(str(turns) + "\n")
        if(turns < 10):
            file.write("Bonus for taking less than 10 turns")

        file.write("Overall Score: \n")
        for index in range(0, self.F_ACTORS):
            score = agent_goal_scores[index] + agent_enemy_scores[index] + 20 - helicopter_cost_scores[index] + 20 - turns
            possible = max_distance + 20 + 20
            print(float(score * 100 / possible))
            total = float(score * 100 / possible)
            file.write("Soldier" + str(index) + ": " + str(total))

    def run_without_visual(self):
        while not self.world.terminated():
            result = self.world.step()
            self.world.explain(result, 2)
        self.evaluate_score()

    def run_with_visual(self):
        pyglet.resource.path = ['../resources']
        pyglet.resource.reindex()

        SCREEN_WIDTH = self.MAP_SIZE_X * 32
        SCREEN_HEIGHT = self.MAP_SIZE_Y * 32
        window = pyglet.window.Window(resizable=True)
        window.set_size(SCREEN_WIDTH, SCREEN_HEIGHT)

        tile_image = pyglet.resource.image("grass.png")
        tiles_batch = pyglet.graphics.Batch()
        tiles = []
        for y in range(0, self.MAP_SIZE_Y):
            for x in range(0, self.MAP_SIZE_X):
                tiles.append(pyglet.sprite.Sprite(
                    img=tile_image,
                    x=x * 32,
                    y=y * 32,
                    batch=tiles_batch)
                )

        goal_image = pyglet.resource.image("target.png")
        goals_batch = pyglet.graphics.Batch()
        goals = []
        for index in range(0, len(self.F_GOAL_LOC)):
            goals.append(pyglet.sprite.Sprite(
                img=goal_image,
                x=self.f_get_goal_x(index) * 32,
                y=self.f_get_goal_y(index) * 32,
                batch=goals_batch)
            )

        agent_image = pyglet.resource.image("soldier_blue.png")
        agents_batch = pyglet.graphics.Batch()
        agents = []
        for index in range(0, self.F_ACTORS):
            agents.append(pyglet.sprite.Sprite(
                img=agent_image,
                x=self.f_get_start_x(index) * 32,
                y=self.f_get_start_y(index) * 32,
                batch=agents_batch)
            )

        enemy_image = pyglet.resource.image("soldier_red.png")
        enemies_batch = pyglet.graphics.Batch()
        enemies = []
        for index in range(0, self.E_ACTORS):
            enemies.append(pyglet.sprite.Sprite(
                img=enemy_image,
                x=self.e_get_start_x(index) * 32,
                y=self.e_get_start_y(index) * 32,
                batch=enemies_batch)
            )

        distractor_image = pyglet.resource.image("heli.png")
        base_image = pyglet.resource.image("base.png")
        allies_batch = pyglet.graphics.Batch()
        bases = []
        distractors = []
        for index in range(0, self.D_ACTORS):
            bases.append(pyglet.sprite.Sprite(
                img=base_image,
                x=self.d_get_start_x(index) * 32,
                y=self.d_get_start_y(index) * 32,
                batch=allies_batch)
            )
            distractors.append(pyglet.sprite.Sprite(
                img=distractor_image,
                x=self.d_get_start_x(index) * 32,
                y=self.d_get_start_y(index) * 32,
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

        @window.event
        def on_key_press(symbol, modifiers):
            if symbol == key.P:
                self.paused = True
                print('Paused')
            if symbol == key.U:
                self.paused = False
                print('Resumed')

        def update(dt):
            if not self.paused:
                result = self.world.step()
                self.world.explain(result, 2)
                if self.world.terminated():
                    self.evaluate_score()
                    window.close()

            for index in range(0, self.F_ACTORS):
                agents[index].x = int(self.world.getState('Actor' + str(index), 'x').domain()[0]) * 32
                agents[index].y = int(self.world.getState('Actor' + str(index), 'y').domain()[0]) * 32

            for index in range(0, self.E_ACTORS):
                enemies[index].x = int(self.world.getState('Enemy' + str(index), 'x').domain()[0]) * 32
                enemies[index].y = int(self.world.getState('Enemy' + str(index), 'y').domain()[0]) * 32

            for index in range(0, self.D_ACTORS):
                distractors[index].x = int(self.world.getState('Distractor' + str(index), 'x').domain()[0]) * 32
                distractors[index].y = int(self.world.getState('Distractor' + str(index), 'y').domain()[0]) * 32

        pyglet.clock.schedule_interval(update, 0.1)
        # pyglet.app.run()
        Thread(target=pyglet.app.run()).start()
        # target=pyglet.app.run()

if __name__ == '__main__':

    for i1 in range(0,10):
        sg = float(i1/10)
        for i2 in range(0,10):
            se = float(i2/10)
            run = Scenario(
                MAP_SIZE_X=8,
                MAP_SIZE_Y=5,
                F_ACTORS=1,
                F_START_LOC=["1,2"],
                F_GOAL_LOC=["5,4"],
                E_ACTORS=1,
                E_START_LOC=["4,3"],
                E_PATROL_RANGE=5,
                D_ACTORS=1,
                D_START_LOC=["0,0"],
                BASE=[0.5, 0.2],
                DISTRACTOR=[-1.0, 1.0],
                ENEMY=[0.5, 0.6, -1.0],
                AGENT=[sg, se])
            run.run_with_visual()
#     print('RUN COMPLETE!')
