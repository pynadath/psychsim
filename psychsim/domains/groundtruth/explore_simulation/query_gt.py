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
        if consts.values_in in arg_desc.keys():
            s = helper.add_space_at_end("", max_len)
            s += "Possible values: " + ", ".join(arg_desc[consts.values_in])
            print(s)
    print("\n")

def print_with_buffer(message, buffer=None):
    if buffer:
        print(message, buffer)
    else:
        print(message)


class LogParser:
    """
    Log parser object.
    Will allow the user to read the logs of a specific simulation (instance and run given by the user) and to query it.
    """


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
        """
        Initiates the query_param object used to save the value of the parameters from the user command
        :return:
        """
        self.query_param = dict()
        self.query_param[consts.ACTOR] = None
        self.query_param[consts.DAY] = -1
        self.query_param[consts.ATTRIBUTE] = None
        self.query_param[consts.NUMBER] = -1
        self.query_param[consts.MODE_SELECTION] = consts.random_str
        self.query_param[consts.MODE_DISPLAY] = consts.actors_list
        self.query_param[consts.ATTRIBUTE_VAL] = False



    def parse_logs(self, buffer=None):
        """
        Checks that the Run and Instance parameter exists. Does a first parsing of the logs to get general info like the number of agents.
        :param buffer:
        :return:
        """
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
        """
        Main loop: read a query from the user and executes it.
        :return:
        """
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
        """
        Parses the user's query to get the command out of it and save if for execution.
        :param query: user's query
        :return:
        """
        self.command = ' '.join(query.split()[:2])


    def get_arguments(self, query, buffer=None):
        """
        Parses the parameters/arguments of the query give by the user.
        Query format is: commandword1 commandword2 -argname1 val1 -argname2 val2 etc
        :param query: user's query (string)
        :param buffer:
        :return: True or False
        """
        query_dash_splited = query.split('-')
        for args in query_dash_splited[1:]:
            # print(args)
            args_pair = args.strip().split(' ')
            # print(args_pair)
            if len(args_pair) < 2:
                print_with_buffer("ParameterError: missing value for query parameter %s" % args, buffer)
                return False
            elif len(args_pair) > 2:
                print_with_buffer("ParameterError: too many values for query parameter %s" % args, buffer)
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


    def set_p_with_values_in(self, p_name, p_val, values_in_list, buffer):
        """
        Set the value of a query parameter (that has a set of possible values) in the self.query_param object.
        :param p_name: name of the parameter
        :param p_val: value of the parameter (retrieved for the user's query)
        :param values_in_list: list of possible values for the parameter
        :param buffer:
        :return: True or False
        """
        if p_val in values_in_list:
            self.query_param[p_name] = p_val
            return True
        else:
            values_in = " or ".join(values_in_list)
            print_with_buffer("ValueError: parameter %s should be %s, got %s" % (p_name, values_in, p_val), buffer)
            return False

    def set_p_int_or_float(self, p_name, p_val, p_type, p_max=False, p_to_str=False, buffer=None):
        """
        Set the value of a query parameter that is either a float or an integer in the self.query_param object.
        :param p_name: name of the parameter
        :param p_val: value of the parameter (retrieved for the user's query)
        :param p_type: type (float or int) of the parameter
        :param p_max: maximum value of the parameter (if it has one)
        :param p_to_str: should the parameter be transformed into a string?
        :param buffer:
        :return: True of False
        """
        try:
            i = p_type(p_val)
            if p_max is not False and i > p_max:
                print_with_buffer("ValueError: max for parameter %s is %d" % (p_name, p_max), buffer)
                return False
            else:
                if p_to_str:
                    self.query_param[p_name] = i.__str__()
                else:
                    self.query_param[p_name] = i
                return True
        except ValueError:
            print_with_buffer("ValueError: parameter %s takes integers, got %s" % (p_name, p_val), buffer)
            return False

    def set_p_day(self, p_val, buffer):
        """
        Set the value of the DAY parameter
        :return: True or False
        """
        return self.set_p_int_or_float(p_name=consts.DAY, p_val=p_val, p_type=int, p_max=self.n_days, p_to_str=True, buffer=buffer)

    def set_p_actor(self, p_val, buffer):
        """
        Set the value of the ACTOR parameter
        :return: True or False
        """
        return self.set_p_int_or_float(p_name=consts.ACTOR, p_val=p_val, p_type=int, p_max=self.n_actors, p_to_str=True, buffer=buffer)

    def set_p_number(self, p_val, buffer):
        """
        Set the value of the NUMBER parameter
        :return: True or False
        """
        return self.set_p_int_or_float(p_name=consts.NUMBER, p_val=p_val, p_type=int, p_max=False, p_to_str=False, buffer=buffer)

    def set_p_att_value(self, p_val, buffer):
        """
        Set the value of the ATTRIBUTE_VALUE parameter
        :return: True or False
        """
        return self.set_p_int_or_float(p_name=consts.ATTRIBUTE_VAL, p_val=p_val, p_type=float, p_max=False, p_to_str=False, buffer=buffer)

    def set_p_mode_selection(self, p_val, buffer):
        """
        Set the value of the selection mode parameter
        :return: True or False
        """
        return self.set_p_with_values_in(p_name=consts.MODE_SELECTION, p_val=p_val, values_in_list=consts.MODE_SELECTION_VALUES_IN, buffer=buffer)

    def set_p_mode_display(self, p_val, buffer):
        """
        Set the value of the display mode parameter
        :return: True or False
        """
        return self.set_p_with_values_in(p_name=consts.MODE_DISPLAY, p_val=p_val, values_in_list=consts.MODE_DISPLAY_VALUES_IN, buffer=buffer)

    def set_p_operator(self, p_val, buffer):
        """
        Set the value of the operator parameter (used to apply filter).
        :return: True or False
        """
        return self.set_p_with_values_in(p_name=consts.OPERATOR, p_val=p_val, values_in_list=consts.OPERATOR_VALUES_IN, buffer=buffer)

    def set_p_attribute(self, p_val, buffer):
        self.query_param[consts.ATTRIBUTE] = p_val
        return True


    def set_param_value(self, p_name, p_val, buffer=None):
        """
        Sets the value p_val of parameter p_name in the self.query_param object for query execution
        :param p_name: name of the paramter
        :param p_val: value of the paramter
        :param buffer:
        :return: True or False
        """
        if p_name in consts.QUERY_PARAM[consts.DAY]:
            return self.set_p_day(p_val, buffer)
        elif p_name in consts.QUERY_PARAM[consts.ACTOR]:
            return self.set_p_actor(p_val, buffer)
        elif p_name in consts.QUERY_PARAM[consts.NUMBER]:
            return self.set_p_number(p_val, buffer)
        elif p_name in consts.QUERY_PARAM[consts.MODE_SELECTION]:
            return  self.set_p_mode_selection(p_val, buffer)
        elif p_name in consts.QUERY_PARAM[consts.MODE_DISPLAY]:
            return self.set_p_mode_display(p_val, buffer)
        elif p_name in consts.QUERY_PARAM[consts.ATTRIBUTE]:
            return self.set_p_attribute(p_val, buffer)
        elif p_name in consts.QUERY_PARAM[consts.ATTRIBUTE_VAL]:
            return self.set_p_att_value(p_val, buffer)
        elif p_name in consts.QUERY_PARAM[consts.OPERATOR]:
            return self.set_p_operator(p_val, buffer)
        else:
            print_with_buffer("ParamaterError: %s does not exists." % p_name, buffer)
            return False


    def parse_query(self, query, buffer):
        """
        Parses the user query: get the command and the parameters. Parameters values are checked. Returns a boolean indicating whether the query could be parsed correctly.
        :param query: user query
        :param buffer:
        :return: True or False
        """
        self.init_queryparams()
        self.get_command(query)
        res = self.get_arguments(query, buffer=buffer)
        return res


    def execute_query(self, query, buffer=None):
        """
        Executes the user query by calling the right function with the right arguments.
        :param query: user query
        :param buffer:
        :return:
        """
        if self.parse_query(query, buffer=buffer):
            if self.command in consts.COMMAND_GET_NDAYS:
                self.get_ndays(buffer)
            elif self.command in consts.COMMAND_GET_NACTORS:
                self.get_nactors(buffer)
            elif self.command in consts.COMMAND_GET_ATTRIBUTES:
                self.get_attributes(self.query_param[consts.ACTOR], p_day=self.query_param[consts.DAY], buffer=buffer)
            elif self.command in consts.COMMAND_SELECT_NACTORS:
                self.select_nactors(p_n=self.query_param[consts.NUMBER], p_actors=None, p_mode_select=self.query_param[consts.MODE_SELECTION], buffer=buffer)
            elif self.command in consts.COMMAND_SHOW_SELECTION:
                self.display_actor_selection(p_display_mode=self.query_param[consts.MODE_DISPLAY], buffer=buffer)
            elif self.command in consts.COMMAND_RESET_SELECTION:
                self.reset_selection(buffer)
            elif self.command in consts.COMMMAND_APPLY_FILTER:
                self.apply_filter(p_day=self.query_param[consts.DAY], p_att=self.query_param[consts.ATTRIBUTE], p_val=self.query_param[consts.ATTRIBUTE_VAL], p_operator=self.query_param[consts.OPERATOR], buffer=buffer )
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
        """
        Tells the user the number of days.
        :param buffer:
        :return:
        """
        print_with_buffer("Simulation stopped after %d days" % self.n_days, buffer)

    def get_nactors(self, buffer):
        """
        Tells the user the number of actors in the simulation
        :param buffer:
        :return:
        """
        print_with_buffer("There are %d actors in the simulation" % self.n_actors, buffer)


    ## ---------------------------------------       Select agents           -------------------------------- ##

    def error_selection_not_enough_actors(self, p_n, buffer):
        """
        Gives feedback to the user regarding why we can't select as many actors as they asked.
        :param p_n: number of actors the user wanted to select
        :param buffer:
        :return:
        """
        if self.selection_criteria[consts.empty] == True:
            error_msg = "Selection Error: There are only %d actors in the simulation, we cannot select %d actors." % (self.n_actors, p_n)
        else:
            error_msg = "Your criteria are too restrictive go select %d actors. There are only %d actors that fulfil your criteria" % (self.n_actors, len(self.selected_agents))
        print_with_buffer(error_msg, buffer)

    def select_nactors(self, p_n=-1, p_actors=None, p_mode_select=consts.random_str, buffer=None):
        """
        Selects actors for the user.
        :param p_n: number of actors to select
        :param p_actors: TODO: give the possibility to the user to select several actors by name.
        :param p_mode_select: selection mode (ordered (alphabetical order) or random. Default is random.
        :param buffer:
        :return:
        """
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
        """
        Display the selection by by actors list (names) or (TODO) criteria list.
        :param p_display_mode: criteria or names.
        :param buffer:
        :return:
        """
        if len(self.selected_agents) == self.n_actors:
            print_with_buffer("All agents are selected", buffer)
        if p_display_mode == consts.actors_list:
            print_with_buffer("%d agents are selected:\n" % len(self.selected_agents), buffer)
            print_with_buffer(", ".join(self.selected_agents), buffer)

    def reset_selection(self, buffer):
        """
        Resets the selection
        :param buffer:
        :return:
        """
        self.selected_agents = self.actors_full_list
        print_with_buffer("Reset selection.")


    ## ---------------------------------------   Query on one specific agent -------------------------------- ##


    def get_attributes(self, p_actor, p_day=-1, buffer=None):
        """
        Displays the attributes (BELIEFS) of a specific agent. 2 modes:
            - a day is selected:    returns the list of attributes and their values for that day
            - no day is selected:   returns just the list of attributes attached to that actor (no values)
        :param p_actor: name of the actor
        :param p_day: day
        :param buffer:
        :return:
        """
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

    def get_att_val(self, actor_name, p_att, p_day):
        """
        For a specific actor, day and attribute, returns the value (STATE OF THE WORLD, --NOT belief) of the attribute.
        :param actor_name:
        :param p_att:
        :param p_day:
        :return:
        """
        file_name = self.logs_dir + "/state" + p_day  + "System.pkl"
        if os.path.exists(file_name):
            with open(file_name, 'rb') as f:
                content = pickle.load(f)
                distrib = content['__state__'][actor_name+"'s "+p_att]
                return helper.get_val(distrib=distrib)


    def apply_filter(self, p_day, p_att, p_val, p_operator, buffer=None):
        """
        Applies a filter to the currently selected agents. A filter is for example "location = 2" of "health > 0.6"
        TODO: Save filter as the selection criteria.
        :param p_day: day for which the selection should be done.
        :param p_att: attribute on which we are filtering actors.
        :param p_val: value given by the user.
        :param p_operator: operator to compare the actual value to the value given by the user.
        :param buffer:
        :return:
        """
        self.selected_agents = [agent for agent in self.selected_agents if helper.compare(v1=self.get_att_val(agent, p_att=p_att, p_day=p_day), v2=p_val, op=p_operator)]
        print_with_buffer("After applying filter", buffer=buffer)
        self.display_actor_selection()
        # att_val = self.get_att_val("1", p_att, p_day)
        # print(att_val)

if __name__ == "__main__":

    argp = argparse.ArgumentParser()
    argp.add_argument('-i', metavar='instance', type=str, help='Instance number to process.')
    argp.add_argument('-r', metavar='run', type=str, help='Run number to process.')

    args = argp.parse_args()

    logparser = LogParser(args.i, args.r)
    logparser.query_log()
