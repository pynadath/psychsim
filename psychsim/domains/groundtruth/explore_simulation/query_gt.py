import pickle
import argparse
import re
from termcolor import colored
import os
import random

import psychsim.domains.groundtruth.explore_simulation.query_gt_consts as consts
import psychsim.domains.groundtruth.explore_simulation.helper_functions as helper

'''
    scneario.pkl does not open.
        Traceback (most recent call last):
            File "/Users/lucileca/Desktop/groundtruth/psychsim/domains/groundtruth/simulation/query_gt.py", line 19, in <module>
            s = pickle.load(f)
            _pickle.UnpicklingError: could not find MARK


    Problem with current psychsim logs:
    they are not readable. 
    2:
    100%    : 1.0
            Actor0001's __REWARD__: 0.0
    3:
    100%    : 1.0
            Actor0001's location: 35
    4:
    100%    : 1.0
            Nature's __ACTION__: 17
    7:
    100%    : 1.0
            System's __ACTION__: 740
    9:
    100%    : 1.0
            System's __MODEL__: 739
    10:
    100%    : 1.0
            Nature's category: 0
    What are the Numbers??? (missing values: 2, 3, 4, 7, 9, 10...)
    What is action 17?? (Nature's action?)


    
    Querying states is the only thing we can do here.
    
    Looks like state1Actor.pkl and state1Actor.pkl are the same.

    I cannot run instance 15 myself --> Errors (I pulled, I am up-to-date).
    
    Files on the drive take forever to download.
    
    What is TURN? --> in state2Actor, why is Nature's turn 2, actor's turn 0,system's turn 1?
    
    Why s['Actor0001'] = {'Actor00010': <psychsim.pwl.state.VectorDistributionSet object at 0x7faeb8087048>} ?? (why an extra 0?)

'''

def get_ints(s):
    return [int(s) for s in str.split(" ") if s.isdigit()]

def preprocess(s):
    s = s.replace("\n", " ")
    s = s.strip()
    s = re.sub(' +', ' ', s)
    return s

def print_help():
    print(colored("Commands - optional arguments are between []", "yellow"))
    for c_list, c_desc in consts.HELP[consts.commands].items():
        s = c_list[0]
        for arg in c_desc[consts.parameters]:
            name, optional = arg[consts.name], arg[consts.optional]
            optional_open = "[" if optional else ""
            optional_close = "]" if optional else ""
            s += " "+optional_open+"-" + arg[consts.name] + optional_close
        print(s)
        print(c_desc[consts.description]+"\n")

    print(colored("Arguments", "yellow"))
    args = consts.HELP[consts.parameters].keys()
    longest_str = max(args, key=len)
    max_len = len(longest_str) + 2
    f = '{:>%d}' % max_len
    for arg, arg_desc in consts.HELP[consts.parameters].items():
        s = helper.add_space_at_end(arg, max_len-len(arg))
        s += arg_desc[consts.value_type]
        print(s)
        s = helper.add_space_at_end("", max_len)
        s += arg_desc[consts.description]
        print(s)

    print("\n")

def print_with_buffer(message, buffer=None):
    if buffer:
        print(message, buffer)
    else:
        print(message)


class LogParser:


    ############################################################################################################
    ##                       Initialisation: arsing log and saving info to answer queries                     ##
    ############################################################################################################


    def __init__(self, instance, run, buffer=None):
        self.instance = instance
        self.run = run
        self.n_days = -1
        self.n_actors = -1
        self.logs_dir = "psychsim/domains/groundtruth/Instances/Instance"+instance+"/Runs/run-"+run

        self.command = None
        self.query_param = dict()
        self.init_queryparams()

        self.selected_agents = list()
        self.selection_criteria = dict()
        self.selection_criteria[consts.empty] = True

        self.parse_logs(buffer)


    def init_queryparams(self):
        self.query_param = dict()
        self.query_param[consts.ACTOR] = None
        self.query_param[consts.DAY] = -1
        self.query_param[consts.ATTRIBUTE] = None
        self.query_param[consts.NUMBER] = -1
        self.query_param[consts.MODE_SELECTION] = consts.random_str
        self.query_param[consts.MODE_DISPLAY] = consts.actors_list



    def parse_logs(self, buffer):
        if not os.path.isdir(self.logs_dir):
            print("%s is not a directory. The instance or the run specified doesnot exists." % self.logs_dir, buffer)
            exit(0)
        self.n_days = int((helper.count_files(self.logs_dir, ext="pkl") - 1) / 3)

        # get number of actors
        file_name = self.logs_dir + "/state1Actor.pkl"
        with open(file_name, 'rb') as f:
            content = pickle.load(f)
        self.actors_full_list = [key for key in content.keys() if "Actor" in key]
        self.selected_agents = list(self.actors_full_list)
        self.n_actors = len(self.actors_full_list)




    ############################################################################################################
    ##                                     Loop: read and execute commands                                    ##
    ############################################################################################################

    def query_log(self):
        q= False
        print(colored("Ready to query log. Use q to quit and h for help.", "red"))
        while(not q):
            query = input(colored("Query: ", "red"))
            if query == 'q':
                q = True
            elif query == 'h':
                print_help()
            else:
                self.execute_query(preprocess(query))

    ############################################################################################################
    ##                            Reading, understanding and executing user command                           ##
    ############################################################################################################

    def get_command(self, query):
        self.command = ' '.join(query.split()[:2])


    def get_arguments(self, query, buffer=None):
        query_dash_splited = query.split('-')
        for args in query_dash_splited[1:]:
            # print(args)
            args_pair = args.strip().split(' ')
            # print(args_pair)
            if len(args_pair) < 2:
                print_with_buffer("ParameterError: missing value for query parameter %s" % args, buffer)
                return False
            elif len(args_pair) > 2:
                # print_with_buffer("ParameterError: too many values for query parameter %s" % args, buffer)
                return False
            else:
                p_name, p_value = args_pair[0], args_pair[1]
                if p_name not in consts.ALL_QUERY_PARAMS:
                    print_with_buffer("ParameterError: unknown parameter %s" % p_name, buffer)
                    return False
                else:
                    param_ok =  self.set_param_value(p_name, p_value, buffer)
                    if param_ok is not True:
                        return False
        return True



    def set_param_value(self, p_name, p_val, buffer=None):
        if p_name in consts.QUERY_PARAM[consts.DAY]:
            # print("in here")
            try:
                i = int(p_val)
                # print("got turn "+i.__str__())
                if i > self.n_days:
                    print_with_buffer("ValueError: max for parameter %s is %d" % (p_name, self.n_days), buffer)
                    return False
                else:
                    self.query_param[consts.DAY] = i
                return True
            except ValueError:
                print_with_buffer("ValueError: parameter %s takes integers, got %s" % (p_name, p_val), buffer)
                return False
        elif p_name in consts.QUERY_PARAM[consts.ACTOR]:
            try:
                i = int(p_val)
                if i > self.n_actors:
                    print_with_buffer("ValueError: there are only %d actors" % self.n_actors, buffer)
                    return False
                else:
                    self.query_param[consts.ACTOR] = i.__str__()
                    return True
            except ValueError:
                print_with_buffer("ValueError: parameter %s takes integers, got %s" % (p_name, p_val), buffer)
                return False
        elif p_name in consts.QUERY_PARAM[consts.NUMBER]:
            try:
                i = int(p_val)
                self.query_param[consts.NUMBER] = i
                return True
            except ValueError:
                print_with_buffer("ValueError: parameter %s takes integers, got %s" % (p_name, p_val), buffer)
                return False
        elif p_name in consts.QUERY_PARAM[consts.MODE_SELECTION]:
            if p_val in consts.MODE_SELECTION_VALUES_IN:
                self.query_param[consts.MODE_SELECTION] = p_val
                return True
            else:
                values_in = " or ".join(consts.MODE_SELECTION_VALUES_IN)
                print_with_buffer("ValueError: parameter %s should be %s, got %s" % (p_name, values_in, p_val), buffer)
                return False
        elif p_name in consts.QUERY_PARAM[consts.MODE_DISPLAY]:
            if p_val in consts.MODE_DISPLAY_VALUES_IN:
                self.query_param[consts.MODE_DISPLAY] = p_val
                return True
            else:
                values_in = " or ".join(consts.MODE_DISPLAY_VALUES_IN)
                print_with_buffer("ValueError: parameter %s should be %s, got %s" % (p_name, values_in, p_val), buffer)
                return False
        else:
            print_with_buffer("ParamaterError: %s does not exists." % p_val, buffer)
            return False
        print_with_buffer("DEBUG: set_param_value for param %s have returned something!" % p_name, buffer)



    def parse_query(self, query, buffer):
        self.init_queryparams()
        self.get_command(query)
        res = self.get_arguments(query, buffer=buffer)
        return res

    def execute_query(self, query, buffer=None):
        if self.parse_query(query, buffer=buffer):
            if self.command in consts.COMMAND_GET_NDAYS:
                self.get_ndays(buffer)
            elif self.command in consts.COMMAND_GET_NACTORS:
                self.get_nactors(buffer)
            elif self.command in consts.COMMAND_GET_ATTRIBUTES:
                self.get_attributes(self.query_param[consts.ACTOR], p_day=self.query_param[consts.DAY], buffer=buffer)
            elif self.command in consts.COMMAND_SELECT_ACTORS:
                self.select_actors(p_n=self.query_param[consts.NUMBER], p_actors=None, p_day=1, p_mode_select=self.query_param[consts.MODE_SELECTION], buffer=buffer)
            elif self.command in consts.COMMAND_SHOW_SELECTION:
                self.display_actor_selection(p_display_mode=self.query_param[consts.MODE_DISPLAY], buffer=buffer)
            elif self.command in consts.COMMAND_RESET_SELECTION:
                self.reset_selection(buffer)
            else:
                print_with_buffer("QueryError: \"%s\" command unknown" % self.command, buffer)
        else:
            print_with_buffer("ERROR, cannot execute query: %s" % query, buffer)
            return False


    ############################################################################################################
    ##                                              COMMANDS                                                  ##
    ############################################################################################################

    ## ---------------------------------------       General queries         -------------------------------- ##


    def get_ndays(self, buffer):
        print_with_buffer("Simulation stopped after %d days" % self.n_days, buffer)

    def get_nactors(self, buffer):
        print_with_buffer("There are %d actors in the simulation" % self.n_actors, buffer)


    ## ---------------------------------------       Select agents           -------------------------------- ##

    def error_selection_not_enough_actors(self, p_n, buffer):
        if self.selection_criteria[consts.empty] == True:
            error_msg = "Selection Error: There are only %d actors in the simulation, we cannot select %d actors." % (self.n_actors, p_n)
        else:
            error_msg = "Your criteria are too restrictive go select %d actors. There are only %d actors that fulfil your criteria" % (self.n_actors, len(self.selected_agents))
        print_with_buffer(error_msg, buffer)

    def select_actors(self, p_n=-1, p_actors=None, p_day=1, p_mode_select=consts.random_str, buffer=None):
        # Select by names
        if isinstance(p_actors, list):
            self.selected_agents = [actor for actor in self.selected_agents if actor in p_actors]
        else:
            self.selected_agents = list(self.selected_agents)

        # Select by criteria

        # Shuffle list if random select
        if p_mode_select == consts.random_str:
            random.shuffle(self.selected_agents)

        # Sample p_n agents
        if p_n != -1:
            n = len(self.selected_agents)
            if p_n > n:
                self.error_selection_not_enough_actors(p_n=p_n, buffer=buffer)
            else:
                self.selected_agents = self.selected_agents[:p_n]

        print_with_buffer("Selected %d agents:" % len(self.selected_agents), buffer)
        self.display_actor_selection(buffer=buffer)


    def display_actor_selection(self, p_display_mode=consts.actors_list, buffer=None):
        if len(self.selected_agents) == self.n_actors:
            print_with_buffer("All agents are selected", buffer)
        if p_display_mode == consts.actors_list:
            print_with_buffer(", ".join(self.selected_agents), buffer)

    def reset_selection(self, buffer):
        self.selected_agents = self.actors_full_list
        print_with_buffer("Reset selection.")


    ## ---------------------------------------   Query on one specific agent -------------------------------- ##


    def get_attributes(self, p_actor, p_day=-1, buffer=None):
        if p_actor == None:
            print_with_buffer("ParameterError: missing parameter -%s for command \"get attibute(s)\"" % consts.ACTOR, buffer)
            return False
        p_day_not_set = False
        if p_day == -1:
            #read attributes for a random day
            p_day = 1
            p_day_not_set = True

        file_name = self.logs_dir + "/state" + p_day.__str__() + "Actor.pkl"
        if os.path.exists(file_name):
            with open(file_name, 'rb') as f:
                content = pickle.load(f)
            actor_name = 'Actor000'+p_actor
            dict_for_actor = content[actor_name][actor_name+'0']
            keys = dict_for_actor.keys()
            attributes = [key.split()[1] for key in keys if (actor_name in key and "__" not in key)]

            if p_day_not_set:
                s = "%s has attributes: " % actor_name
                s += ", ".join(attributes)
            else:
                s = "At %s %d, %s has:\n" % (consts.DAY, p_day, actor_name)
                att_to_printable_distrib_dict = dict()
                for att in attributes:
                    att_to_printable_distrib_dict[att] = helper.str_distribution(dict_for_actor[actor_name+"'s "+att])
                s += helper.str_aligned_values(att_to_printable_distrib_dict)
            print_with_buffer(s, buffer)

        else:
            print_with_buffer("ERROR - Missing file: %s" % file_name, buffer)
            return False



if __name__ == "__main__":

    argp = argparse.ArgumentParser()
    argp.add_argument('-i', metavar='instance', type=str, help='Instance number to process.')
    argp.add_argument('-r', metavar='run', type=str, help='Run number to process.')

    args = argp.parse_args()

    logparser = LogParser(args.i, args.r)
    logparser.query_log()
