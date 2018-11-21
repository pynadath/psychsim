import numpy as np
import random
from psychsim_teamofrivals.domains.teamofrivals import teamofrivals as env


class buffer():

    def __init__(self,size):
        self.size = size
        self.buf = []

    def add(self,memory):
        if len(self.buf) < self.size:
            self.buf.append(memory)
        else:
            del self.buf[0]
            self.buf.append(memory)

    def get_train_batch(self,batch_size):
        batch = random.sample(self.buf,batch_size)
        return batch



class Agent():

    def __init__(self,num_ters,exploration_f,gamma,lr):
        self.table = {}
        self.available_places = num_ters
        self.exploration_factor = exploration_f
        self.gamma = gamma
        self.learning_rate = lr
        self.exp_buffer = buffer(10000)

    def update_lr(self,new):
        self.learning_rate = new

    def update_gamma(self,new):
        self.gamma = new

    def update_exploration(self,new):
        self.exploration_factor = new

    def get_valid_actions(self,state):
        available_territories = np.ones(self.available_places)
        for player in range(state.shape[0]-1):
            res_dist = state[player][1:]
            for territory in range(res_dist.shape[0]):
                if res_dist[territory] > 0:
                    available_territories[territory] = 0
        return available_territories

    def initialize_actions(self,state):
        init_value = 0
        n = int(state[0].shape[0])
        val = n*(n+1)/2
        print val
        # Create actions array
        Actions = np.zeros(val)
        Actions.fill(-np.inf)

        available_territories = self.get_valid_actions(state)
        # got the available territories to attck for the current position
        for ter1 in range(self.available_places):
            if available_territories[ter1] == 1:
                Actions[ter1] = init_value
                temp_val = (self.available_places-ter1)*(ter1+1)
                for ter2 in range(ter1+1,self.available_places):
                    if available_territories[ter2] == 1:
                        Actions[temp_val] = init_value
                    temp_val += 1

        return Actions

    def generate_action(self,state):
        if str(state) not in self.table:
            self.table[str(state)] = self.initialize_actions(state)

        # Genarate random number to check exploration vs explotation
        r = np.random.random()
        if r <= self.exploration_factor:
            # Genarate random move
            valid_moves = self.get_valid_actions(state)
            indices = [i for i,v in enumerate(valid_moves != -np.inf) if v]
            index = indices[np.random.choice(len(indices), 1, replace=True)]

            return index

        else:
            move = np.argmax(self.table[str(state)])
            return move


    def train(self,batch_size):
        train_batch = self.exp_buffer.get_train_batch(batch_size)
        for data in train_batch:
            state = data[0]
            action = data[1]
            reward = data[2]
            next_state = data[3]
            done_flag = data[4]

            if done_flag:
                self.table[state] = reward

            else:
                self.table[state] = (1-self.learning_rate)*self.table[state] + self.learning_rate*(reward + self.gamma*(np.max(self.table[next_state])))
