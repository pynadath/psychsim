import pickle
import argparse
import re
from termcolor import colored
import os
import random
import json
import copy
import matplotlib.pyplot as plt
from matplotlib.legend_handler import HandlerLine2D
from matplotlib.figure import Figure
import operator
from collections import Counter
import statistics
from matplotlib.lines import Line2D

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

BOLD = '\033[1m'
END = '\033[0m'

def print_help():
    print('{}{}{}{}'.format(BOLD, colored("COMMANDS", "yellow"), END, colored(" - optional arguments are between []", "yellow")))
    for category in consts.HELP[consts.commands].keys():
        print(colored(category, "yellow"))
        for c_list, c_desc in consts.HELP[consts.commands][category].items():
            s = c_list[0]
            for arg in c_desc[consts.parameters]:
                name, optional = arg[consts.name], arg[consts.optional]
                optional_open = "[" if optional else ""
                optional_close = "]" if optional else ""
                s += " "+optional_open+"-" + arg[consts.name] + optional_close
            print(s)
            print(c_desc[consts.description]+"\n")

    print('{}{}{}'.format(BOLD,colored("ARGUMENTS", "yellow"), END))
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
        self.filter_list = list()
        self.filter_name_i = 1

        self.samples = dict()
        self.samples_name_i = 1

        self.stats = dict()
        self.stats_name_i = 1

        self.parse_logs(buffer)


    def init_queryparams(self):
        """
        Initiates the query_param object used to save the value of the parameters from the user command
        :return:
        """
        self.query_param = dict()
        self.query_param[consts.ACTOR] = None
        self.query_param[consts.DAYS] = list()
        self.query_param[consts.ATTRIBUTE] = list()
        self.query_param[consts.NUMBER] = -1
        self.query_param[consts.MODE_SELECTION] = consts.random_str
        # self.query_param[consts.MODE_DISPLAY] = consts.actors_list
        self.query_param[consts.ATTRIBUTE_VAL] = False
        self.query_param[consts.ENTITY] = None
        self.query_param[consts.NAME] = None
        self.query_param[consts.TYPE] = "all"
        self.query_param[consts.ACTORS_LIST] = list()
        self.query_param[consts.OPERATOR] = None
        self.query_param[consts.STAT_FCT] = list()
        self.query_param[consts.SAMPLE] = list()



    def parse_logs(self, buffer=None):
        """
        Checks that the Run and Instance parameter exists. Does a first parsing of the logs to get general info like the number of agents.
        :param buffer:
        :return:
        """
        if not os.path.isdir(self.logs_dir):
            print_with_buffer("%s is not a directory. The instance or the run specified does not exists." % self.logs_dir, buffer)
            exit(0)
        self.n_days = int((helper.count_files(self.logs_dir, ext="pkl") - 1) / 3)

        # get number of actors
        file_name = self.logs_dir + "/state1System.pkl"
        with open(file_name, 'rb') as f:
            content = pickle.load(f)
        self.actors_full_list = [key for key in content.keys() if "Actor" in key]

        # get entities' attributes
        self.entities_att_list = dict()
        state = content["__state__"]
        keys = state.keys()
        for key in keys:
            entity_category = self.get_entity_category(key) #e.g. Actor, Region, Nature, System
            if entity_category not in self.entities_att_list.keys():
                self.entities_att_list[entity_category] = list()
            att_name = key.split(" ")[1]
            if att_name not in self.entities_att_list[entity_category]:
                self.entities_att_list[entity_category].append(att_name)

        self.selected_agents = list(self.actors_full_list)
        self.n_actors = len(self.actors_full_list)


    def get_entity_category(self, entity_name):
        """
        Returns the category of an entity (e.g. Actor) -- assuming antity_name is base on category
        :param entity_name: name of the entity (e.g. Actor0001)
        :return: category (string)
        """
        s = entity_name.split("'")[0]
        s = helper.remove_numbers_from_string(s)
        return s



    ############################################################################################################
    ##                                     Loop: read and execute commands                                    ##
    ############################################################################################################

    def query_log(self, text_intro="Ready to query log. "):
        """
        Main loop: read a query from the user and executes it.
        :return:
        """
        q= False
        print(colored(text_intro+"Use q to quit and h for help.", "red"))
        while(not q):
            query = input(colored("Query: ", "red"))
            if query == 'q':
                q = True
            elif query == 'h':
                print_help()
            else:
                res = self.execute_query(preprocess(query))

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
            args_pair = args.strip()
            args_pair = re.split(' |,', args_pair)
            if len(args_pair) < 2:
                print_with_buffer("ParameterError: missing value for query parameter %s" % args, buffer)
                return False
            else:
                p_name, p_value = args_pair[0], args_pair[1:]
                if p_name not in consts.ALL_QUERY_PARAMS:
                    print_with_buffer("ParameterError: unknown parameter %s" % p_name, buffer)
                    return False
                elif self.check_number_of_values_for(p_name, p_value):
                    param_ok = self.set_param_value(p_name, p_value, buffer)
                    if param_ok is not True:
                        return False
                else:
                    number_of_args = self.split_args(p_value)
                    print_with_buffer("ParameterError: was not expecting %d values for %s." % (len(number_of_args), p_name), buffer)
                    return False
        return True

    def check_number_of_values_for(self, p_name, p_value):
        number_of_params = len(p_value)
        if number_of_params > 1 and not isinstance(self.query_param[p_name], list):
            return False
        else:
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
            if isinstance(self.query_param[p_name], list):
                self.query_param[p_name].append(p_val)
            else:
                self.query_param[p_name] = p_val
            return True
        else:
            verb_str = "have values from" if isinstance(self.query_param[p_name], list) else "be"
            values_in = " or ".join(values_in_list)
            print_with_buffer("ValueError: parameter %s should %s %s, got %s" % (p_name, verb_str, values_in, p_val), buffer)
            return False

    def set_list_of_p_with_values_in(self, p_name, p_val, possible_values, buffer):
        if isinstance(p_val, list):
            p_val = [val for val in p_val if val]
            for val in p_val:
                param_ok = self.set_p_with_values_in(p_name=p_name, p_val=val, values_in_list=possible_values, buffer=buffer)
                if not param_ok:
                    return False
            return True
        else:
            return self.set_p_with_values_in(p_name=p_name, p_val=p_val, values_in_list=possible_values, buffer=buffer)

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
                    param = i.__str__()
                else:
                    param = i
                if isinstance(self.query_param[p_name], list):
                    self.query_param[p_name].append(param)
                else:
                    self.query_param[p_name] = param
                return True
        except ValueError:
            print_with_buffer("ValueError: parameter %s takes integers, got %s" % (p_name, p_val), buffer)
            return False


    def set_p_bool(self, p_name, p_val, buffer):
        """
        Sets the value of a boolean query paramter in the self,query_param object
        :param p_name: name of the parameter
        :param p_val: value of the parameter (retrieved for the user's query)
        :param buffer:
        :return: True of False
        """
        lower_case_val = p_val.lower()
        if lower_case_val in consts.true_values:
            self.query_param[p_name] = True
            return True
        elif lower_case_val in consts.false_values:
            self.query_param[p_name] = False
            return True
        else:
            s_true_and_false = ", ".join(consts.true_values) + ", " + ", ".join(consts.false_values)
            print_with_buffer("ValueError: parameter %s takes booleans, got %s. Valid values are: %s" % (p_name, p_val, s_true_and_false), buffer)
            return False


    def set_p_days(self, p_val, buffer):
        """
        Set the value of the DAY parameter
        :return: True or False
        """
        # days_str_splited = p_val.lower().split(",")
        p_val
        # for d_str in p_val:
        skip_next = 0
        for i, e in enumerate(p_val):
            if skip_next == 0:
                if "to" in e:
                    if i == 0:
                        print_with_buffer("ParameterError: cannot you did not specify the beginning of the range")
                        return False
                    elif i == len(p_val) - 1:
                        print_with_buffer("ParameterError: cannot you did not specify the end of the range")
                        return False
                if i < len(p_val) - 2:
                    next_e = p_val[i+1]
                    if next_e == "to":
                        try:
                            d_begin = int(e)
                            d_end = int(p_val[i+2])
                            if d_end < d_begin:
                                print_with_buffer("ParameterError: parameter %s expects \"day_begin to day_end\" with day_begin < day_end.", buffer)
                            else:
                                for i in range(d_begin, d_end+1):
                                    param_ok = self.set_p_int_or_float(p_name=consts.DAYS, p_val=i, p_type=int, p_max=self.n_days, p_to_str=False, buffer=buffer)
                                    if not param_ok:
                                        return False
                            skip_next = 2
                        except:
                            print_with_buffer("Error here. Sorry", buffer)
                else:
                    param_ok = self.set_p_int_or_float(p_name=consts.DAYS, p_val=e.strip(), p_type=int, p_max=self.n_days, p_to_str=False, buffer=buffer)
                    if not param_ok:
                        return False
            else:
                skip_next -= 1
            self.query_param[consts.DAYS].sort()
        return True

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

    def set_p_operator(self, p_val, buffer):
        """
        Set the value of the operator parameter (used to apply filter).
        :return: True or False
        """
        return self.set_p_with_values_in(p_name=consts.OPERATOR, p_val=p_val, values_in_list=consts.OPERATOR_VALUES_IN, buffer=buffer)

    def set_p_entity(self, p_val, buffer):
        """
        Set the value of the entity parameter
        :return: True or False
        """
        return self.set_p_with_values_in(p_name=consts.ENTITY, p_val=p_val, values_in_list=self.entities_att_list.keys(), buffer=buffer)

    def set_p_attribute(self, p_val, buffer):
        # print(p_val)
        possible_values = self.get_attributes("Actor", buffer, verbose=False)
        return self.set_list_of_p_with_values_in(p_name=consts.ATTRIBUTE, p_val=p_val, possible_values=possible_values, buffer=buffer)

    def set_p_name(self, p_val, buffer):
        """
        Sets the value of the name paramter
        """
        self.query_param[consts.NAME] = p_val
        return True

    def set_p_type(self, p_val, buffer):
        """
        Sets the value of the TYPE parameter
        """
        return self.set_p_with_values_in(p_name=consts.TYPE, p_val=p_val, values_in_list=consts.TYPE_VALUES_IN, buffer=buffer)

    def set_p_actors_list(self, numbers_list, buffer):
        """
        Sets the value of the actors_list parameter.
        :param numbers_list:
        :param buffer:
        :return:
        """
        for i in numbers_list:
            param_ok = self.set_p_int_or_float(p_name=consts.ACTORS_LIST, p_val=i, p_type=int, p_max=self.n_actors, p_to_str=True, buffer=buffer)
            if not param_ok:
                return False
        return True

    def set_p_statfunction(self, p_val, buffer):
        return self.set_list_of_p_with_values_in(p_name=consts.STAT_FCT, p_val=p_val, possible_values=consts.STAT_FCT_VALUES_IN, buffer=buffer)
        # if isinstance(p_val, list):
        #     p_val = [val for val in p_val if val]
        #     for val in p_val:
        #         param_ok = self.set_p_with_values_in(p_name=consts.STAT_FCT, p_val=val, values_in_list=consts.STAT_FCT_VALUES_IN, buffer=buffer)
        #         if not param_ok:
        #             return False
        #     return True
        # else:
        #     return self.set_p_with_values_in(p_name=consts.STAT_FCT, p_val=p_val, values_in_list=consts.STAT_FCT_VALUES_IN, buffer=buffer)

    def set_p_sample_name(self, p_val, buffer):
        print("p_val", p_val)
        if self.samples:
            if p_val == "all":
                self.query_param[consts.SAMPLE] = self.samples.keys()
                return True
            else:
                if not isinstance(p_val, list):
                    p_val = [p_val]
                possible_values = [sample[consts.name] for sample in self.samples.values()]
                p_val = [x for x in p_val if x]
                # samples_names = p_val.split()
                print(p_val)
                for s_name in p_val:
                    param_ok = self.set_p_with_values_in(p_name=consts.SAMPLE, p_val=s_name, values_in_list=possible_values, buffer=buffer)
                    if not param_ok:
                        return False
                return True
        else:
            print_with_buffer("ParamterError: You have no saved samples.", buffer)
            return False

    def set_param_value(self, p_name, p_val, buffer=None):
        """
        Sets the value p_val of parameter p_name in the self.query_param object for query execution
        :param p_name: name of the paramter
        :param p_val: value of the paramter
        :param buffer:
        :return: True or False
        """
        set_param_functions_dict = {
            consts.DAYS: self.set_p_days,
            consts.ACTOR: self.set_p_actor,
            consts.NUMBER: self.set_p_number,
            consts.MODE_SELECTION: self.set_p_mode_selection,
            consts.ATTRIBUTE: self.set_p_attribute,
            consts.ATTRIBUTE_VAL: self.set_p_att_value,
            consts.OPERATOR: self.set_p_operator,
            consts.ENTITY: self.set_p_entity,
            consts.NAME: self.set_p_name,
            consts.TYPE: self.set_p_type,
            consts.ACTORS_LIST: self.set_p_actors_list,
            consts.STAT_FCT: self.set_p_statfunction,
            consts.SAMPLE: self.set_p_sample_name
        }
        for param_name, set_fct in set_param_functions_dict.items():
            if p_name in consts.QUERY_PARAM[param_name]:
                p_val = p_val[0] if len(p_val) == 1 else p_val
                return set_fct(p_val, buffer)

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
            res = None
            # General methods
            if self.command in consts.COMMAND_GET_NDAYS:
                res = self.get_ndays(buffer)
            elif self.command in consts.COMMAND_GET_NACTORS:
                res = self.get_nactors(buffer)
            elif self.command in consts.COMMAND_GET_VALUES:
                res = self.get_att_values(self.query_param[consts.ACTOR], p_days=self.query_param[consts.DAYS], buffer=buffer)
            elif self.command in consts.COMMAND_GET_ENTITIES:
                res = self.get_entities(buffer)
            elif self.command in consts.COMMAND_GET_ATTNAMES:
                res = self.get_attributes(p_entity=self.query_param[consts.ENTITY], buffer=buffer)
            # Select actors
            elif self.command in consts.COMMAND_SELECT_NACTORS:
                res = self.select_nactors(p_n=self.query_param[consts.NUMBER], p_mode_select=self.query_param[consts.MODE_SELECTION], buffer=buffer)
            elif self.command in consts.COMMAND_SHOW_SELECTION:
                res = self.display_actor_selection(buffer=buffer)
            elif self.command in consts.COMMAND_SHOW_FILTERS:
                res = self.display_filters(self.query_param[consts.TYPE], buffer)
            elif self.command in consts.COMMAND_RESET_SELECTION:
                res = self.reset_selection(buffer)
            elif self.command in consts.COMMAND_APPLY_FILTER:
                p_days, p_att, p_val, p_op, p_name = self.query_param[consts.DAYS], self.query_param[consts.ATTRIBUTE], self.query_param[consts.ATTRIBUTE_VAL], self.query_param[consts.OPERATOR], self.query_param[consts.NAME]
                res = self.apply_filter(p_days=p_days, p_att=p_att, p_val=p_val, p_operator=p_op, p_name=p_name, buffer=buffer)
            elif self.command in consts.COMMAND_DEACTIVATE_FILTER:
                res = self.deactivate_filter(p_name=self.query_param[consts.NAME], buffer=buffer)
            elif self.command in consts.COMMAND_REACTIVATE_FILTER:
                res = self.reactivate_filter(p_name=self.query_param[consts.NAME], buffer=buffer)
            elif self.command in consts.COMMAND_SELECT_ACTORS_BY_NAME:
                res = self.select_actors_by_name(p_list_names=self.query_param[consts.ACTORS_LIST], buffer=buffer)
            # Samples
            elif self.command in consts.COMMAND_SAVE_SAMPLE:
                res = self.save_sample(p_name=self.query_param[consts.NAME], buffer=buffer)
            elif self.command in consts.COMMAND_DISPLAY_SAMPLES:
                res = self.display_samples(buffer)
            elif self.command in consts.COMMAND_DISPLAY_ONE_SAMPLE:
                res = self.display_one_sample(p_name=self.query_param[consts.NAME], buffer=buffer)
            # Stats
            elif self.command in consts.COMMAND_GET_STATS:
                res = self.get_stats(p_att=self.query_param[consts.ATTRIBUTE], p_fct_list=self.query_param[consts.STAT_FCT], p_days=self.query_param[consts.DAYS], p_sample_names=self.query_param[consts.SAMPLE], buffer=buffer)
            elif self.command in consts.COMMAND_COUNT_ACTORS:
                res = self.count_actors(p_days=self.query_param[consts.DAYS], p_att=self.query_param[consts.ATTRIBUTE], p_op=self.query_param[consts.OPERATOR], p_val=self.query_param[consts.ATTRIBUTE_VAL], buffer=buffer)
            else:
                print_with_buffer("QueryError: \"%s\" command unknown" % self.command, buffer)
            return res
        else:
            print_with_buffer("ERROR, cannot execute query: %s." % query, buffer)
            return False


    ############################################################################################################
    ##                                              COMMANDS                                                  ##
    ############################################################################################################

    ## ---------------------------------------       General queries         -------------------------------- ##
    ## ------------------------------------------------------------------------------------------------------ ##


    def get_ndays(self, buffer):
        """
        Tells the user the number of days.
        :param buffer:
        :return:
        """
        print_with_buffer("Simulation stopped after %d days" % self.n_days, buffer)
        return self.n_days

    def get_nactors(self, buffer):
        """
        Tells the user the number of actors in the simulation
        :param buffer:
        :return:
        """
        print_with_buffer("There are %d actors in the simulation" % self.n_actors, buffer)
        return self.n_days

    def get_entities(self, buffer):
        """
        Tells the user about which kind of entities are present in the simulation
        :param buffer:
        :return:
        """
        entities_list = self.entities_att_list.keys()
        print_with_buffer("The categories of entities in the simulation are: %s" % ", ".join(entities_list), buffer)
        return entities_list

    def get_attributes(self, p_entity, buffer, verbose=True):
        """
        Tells the user about which attributes are associated with a kind of entity
        :param p_entity: kind of entity (e.g. Actor)
        :param buffer:
        :return:
        """
        if p_entity:
            attributes_list = self.entities_att_list[p_entity]
            if verbose:
                print_with_buffer("The attributes associated with the category %s are: %s." % (p_entity, ", ".join(attributes_list)), buffer)
            return attributes_list
        else:
            if verbose:
                print_with_buffer("MssingParamterError: expecting an entity", buffer)

    ## ---------------------------------------       Select agents           -------------------------------- ##
    ## ------------------------------------------------------------------------------------------------------ ##

    def error_selection_not_enough_actors(self, p_n, buffer):
        """
        Gives feedback to the user regarding why we can't select as many actors as they asked.
        :param p_n: number of actors the user wanted to select
        :param buffer:
        :return:
        """
        if not self.filter_list:
            error_msg = "Selection Error: There are only %d actors in the simulation, we cannot select %d actors." % (self.n_actors, p_n)
        else:
            error_msg = "Your filters are too restrictive to select %d actors. With these filters, you can sample at most %d actors" % (self.n_actors, len(self.selected_agents))
        print_with_buffer(error_msg, buffer)

    def select_nactors(self, p_n=-1, p_mode_select=consts.random_str, buffer=None):
        """
        Selects actors for the user.
        :param p_n: number of actors to select
        :param p_actors: TODO: give the possibility to the user to select several actors by name.
        :param p_mode_select: selection mode (ordered (alphabetical order) or random. Default is random.
        :param buffer:
        :return:
        """
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
        return self.selected_agents


    def select_actors_by_name(self, p_list_names, buffer=None):
        """
        Selects actors by their number.
        :param p_list_names: list of numbers (str, mapped to actors' names).
        :param buffer:
        :return:
        """
        print(colored("WARNING: all your filters are now deactivated because you selected agents by names!!!", "cyan"), buffer)
        for f in self.filter_list:
            f[consts.active] = False
        self.selected_agents = self.actors_full_list
        p_list_names = [helper.actor_number_to_name(i) for i in p_list_names]
        self.selected_agents = [actor for actor in self.selected_agents if actor in p_list_names]
        self.display_actor_selection()
        return self.selected_agents

    def reset_selection(self, buffer):
        """
        Resets the selection
        :param buffer:
        :return:
        """
        self.selected_agents = self.actors_full_list
        print_with_buffer("Reset selection", buffer)
        if self.filter_list:
            for filter in self.filter_list:
                filter[consts.active] = False
            print_with_buffer("All filters are inactive", buffer)
        return self.selected_agents


    ## --------------------------------------- Display selection and filters -------------------------------- ##
    ## ------------------------------------------------------------------------------------------------------ ##


    def display_actor_selection(self, buffer=None):
        """
        Display the selection --> actors list (names).
        :param p_display_mode: criteria or names.
        :param buffer:
        :return:
        """
        if len(self.selected_agents) == self.n_actors:
            print_with_buffer("All agents are selected", buffer)
        else:
            print_with_buffer("%d agents are selected:\n" % len(self.selected_agents), buffer)
            print_with_buffer(", ".join(self.selected_agents), buffer)
        return self.selected_agents


    def filters_to_str(self, f, display_activation_status=True):
        """
        Creates a string describing the filter.
        :param f: filter object
        :return: string
        """
        active = "active" if f[consts.active] else "inactive"
        str = self.filters_to_str2(f[consts.DAYS], f[consts.ATTRIBUTE], f[consts.ATTRIBUTE_VAL], f[consts.OPERATOR], f[consts.NAME])
        if display_activation_status:
            str += "  (" + active + ")"
        return str

    def filters_to_str2(self, p_days, p_att, p_val, p_op, p_name):
        # print(p_days, p_att, p_val, p_op, p_name)
        str_days_list = []
        for d in list(helper.find_ranges(p_days)):
            if isinstance(d, tuple):
                str_days_list.append(d[0].__str__() + " to " + d[1].__str__())
            else:
                str_days_list.append(d.__str__())
        str_days = ", ".join(str_days_list)
        str_name = p_name + ": " if p_name else ""
        str = str_name + p_att[0] + " " + p_op + " " + p_val.__str__() + " at " + consts.DAYS + "(s) " + str_days
        return str

    def display_filters(self, type=consts.all_values[0], buffer=None):
        """
        Displays the filters (active or inactive)
        :param active: if True displays the active filters only, if false displays the inactive filters only. Inactive filters are filters that the user set up at some point and then cancelled.
        :param buffer:
        :return:
        """
        if self.filter_list:
            if type in consts.all_values[0]:
                filters_str_list = [self.filters_to_str(f) for f in self.filter_list]
                s_intro = "All filters are"
            else:
                if type in consts.active_values:
                    filters_str_list = [self.filters_to_str(f) for f in self.filter_list if f[consts.active] is True]
                    s_intro = "%d filter(s) are active (%d agents selected)" % (len(filters_str_list), len(self.selected_agents))
                elif type in consts.inactive_values:
                    filters_str_list = [self.filters_to_str(f) for f in self.filter_list if f[consts.active] is False]
                    s_intro = "%d filter(s) are inactive" % len(filters_str_list)
                else:
                    print_with_buffer("Parameter error: Got %s for parameter %s. Was expecting values in %s" % (type, consts.TYPE, ", ".join(consts.TYPE_VALUES_IN)), buffer)
                    return False
            filters_str = "\n\t- ".join(filters_str_list)
            print_with_buffer("%s:\n\t- %s" % (s_intro, filters_str), buffer)
        else:
            print_with_buffer("You haven't created any filter.", buffer)
        return self.filter_list



    ## ---------------------------------------  Select agents with filters   -------------------------------- ##
    ## ------------------------------------------------------------------------------------------------------ ##


    def get_att_val(self, actors_list, p_att, p_day):
        """
        For a specific actor, day and attribute, returns the value (STATE OF THE WORLD, --NOT belief) of the attribute.
        :param actor_name:
        :param p_att:
        :param p_days:
        :return:
        """
        file_name = self.logs_dir + "/state" + p_day.__str__() + "System.pkl"
        if os.path.exists(file_name):
            with open(file_name, 'rb') as f:
                content = pickle.load(f)
                att_values = list()
                for actor_name in actors_list:
                    # print(actor_name, p_att)
                    k = actor_name+"'s "+p_att
                    if k in content['__state__'].keys():
                        distrib = content['__state__'][k]
                        att_values.append(helper.get_val(distrib=distrib))
                    else:
                        att_values.append(consts.THISISFALSE)
                return att_values


    def add_filter_to_filter_list(self, p_days, p_att, p_val, p_operator, p_name, p_active=True, buffer=None):
        """
        Adds a new filter in our filter list to remember it.
        """
        new_filter = dict()
        new_filter[consts.DAYS] = p_days
        new_filter[consts.ATTRIBUTE] = p_att
        new_filter[consts.ATTRIBUTE_VAL] = p_val
        new_filter[consts.OPERATOR] = p_operator
        new_filter[consts.active] = p_active
        if p_name:
            if p_name in [f[consts.NAME] for f in self.filter_list]:
                forbidden_name = p_name
                p_name = "filter" + self.filter_name_i.__str__()
                print_with_buffer("There already is a filter named %s. Your filter is automatically renamed to %s." % (forbidden_name, p_name), buffer)
            new_filter[consts.NAME] = p_name
        else:
            new_filter[consts.NAME] = "filter" + self.filter_name_i.__str__()
            self.filter_name_i += 1
        self.filter_list.append(new_filter)
        return self.filter_list


    def check_filter_already_applied(self, p_days, p_att, p_val, p_operator, buffer=None):
        """
        Checks weather the filter is already applied.
        :return: True or False
        """
        for filter in self.filter_list:
            if filter[consts.DAYS] == p_days and filter[consts.ATTRIBUTE] == p_att and filter[consts.ATTRIBUTE_VAL] == p_val and filter[consts.OPERATOR] == p_operator:
                print_with_buffer("Filter already applied (%s)" % filter[consts.NAME], buffer)
                return filter
        return False



    def apply_filter(self, p_days, p_att, p_val, p_operator, p_name=None, buffer=None, verbose=True, save=True):
        """
        Applies a filter to the currently selected agents. A filter is for example "location = 2 at da 1" or "health > 0.6 at day 16"
        :param p_days: day for which the selection should be done.
        :param p_att: attribute on which we are filtering actors.
        :param p_val: value given by the user.
        :param p_operator: operator to compare the actual value to the value given by the user.
        :param buffer:
        :return:
        """
        if isinstance(p_att, list):
            if len(p_att) > 1:
                print_with_buffer("ParameterError: Given to many values for argument %s.\nCannot apply filter." % consts.ATTRIBUTE, buffer)
                return False
            else:
                p_att = p_att[0]


        # print(p_days, p_att, p_val, p_operator, p_name)
        new_selection = copy.deepcopy(self.selected_agents)
        if not self.check_filter_already_applied(p_days, p_att, p_val, p_operator, buffer):
            if p_days:
                for d in p_days:
                    att_values = self.get_att_val(actors_list=new_selection, p_att=p_att, p_day=d)
                    old_selection = copy.deepcopy(new_selection)
                    new_selection = list()
                    for i, agent in enumerate(old_selection):
                        if helper.compare(att_values[i], v2=p_val, op=p_operator):
                            new_selection.append(agent)
                if save:
                    if len(new_selection) == 0:
                        self.add_filter_to_filter_list(p_days, p_att, p_val, p_operator, p_name, False, buffer)
                        if verbose:
                            print_with_buffer("FilterError: Given the current selection, no agents fulfil your new criteria --> new filter CANNOT be applied. However your filter is saved in memory (it's just inactive)", buffer)
                    else:
                        self.selected_agents = new_selection
                        self.add_filter_to_filter_list(p_days, p_att, p_val, p_operator, p_name, True, buffer)
                        if verbose:
                            print_with_buffer("After applying filter", buffer=buffer)
                            self.display_actor_selection()
            else:
                print_with_buffer("ParameterError: parameter %s not set" % consts.DAYS, buffer)
        return new_selection, self.filter_list


    def get_filter(self, p_name, buffer):
        """
        Finds a filter given a filter name in the list of filters
        :param p_name: name of the filter to look for
        :param buffer:
        :return: filter object
        """
        for f in self.filter_list:
            if f[consts.NAME] == p_name:
                return f
        print_with_buffer("No filter with name %s" % p_name, buffer)
        return False


    def deactivate_filter(self, p_name, buffer=None):
        """
        Deactivates a filter --> performs agent selection again after cancelling the filter.
        :param p_name: name of filter to deactivate
        :param buffer:
        :return:
        """
        filter = self.get_filter(p_name, buffer)
        if filter:
            filter[consts.active] = False
            old_filter_list = self.filter_list
            self.filter_list = list()
            self.selected_agents = self.actors_full_list
            for f in old_filter_list:
                if f[consts.active]:
                    self.apply_filter(p_days=f[consts.DAYS], p_att=f[consts.ATTRIBUTE], p_val=f[consts.ATTRIBUTE_VAL], p_operator=f[consts.OPERATOR], p_name=f[consts.NAME], verbose=False)
                else:
                    self.add_filter_to_filter_list(p_days=f[consts.DAYS], p_att=f[consts.ATTRIBUTE], p_val=f[consts.ATTRIBUTE_VAL], p_operator=f[consts.OPERATOR], p_name=f[consts.NAME], p_active=False)
            # self.display_filters(buffer=buffer)
            print_with_buffer("After deactivating filter %s" % p_name, buffer)
            self.display_actor_selection(buffer=buffer)
        return self.filter_list


    def reactivate_filter(self, p_name, buffer=None):
        """
        Reactivates an inactive filter --> re-selects the agents accordingly
        :param p_name: filter name
        :param buffer:
        :return:
        """
        f = self.get_filter(p_name, buffer)
        if f:
            if not f[consts.active]:
                self.filter_list.remove(f)
                self.apply_filter(p_days=f[consts.DAYS], p_att=f[consts.ATTRIBUTE], p_val=f[consts.ATTRIBUTE_VAL], p_operator=f[consts.OPERATOR], p_name=f[consts.NAME])
            else:
                print_with_buffer("Filter %s is already active" % p_name, buffer)
        return self.filter_list


    ## ---------------------------------------       Save sample of agents   -------------------------------- ##
    ## ------------------------------------------------------------------------------------------------------ ##

    def save_sample(self, p_name=None, buffer=None):
        this_sample_exists, s = self.get_sample(p_name, buffer)
        if this_sample_exists:
            str = "Warning: this sample already exists."
            if p_name != s[consts.name] :
                str += " It is saved with the name %s and will NOT be renamed with the name you provided (%s)" % (s[consts.name], p_name)
        else:
            if s:
                str = "Error: another sample already has this name. Choose another name for your sample to save it."
            else:
                new_sample = self.create_new_sample(p_name, buffer)
                sample_name = new_sample[consts.name]
                self.samples[sample_name] = new_sample
                str = "A new sample was created (%s)" % sample_name
                s = new_sample
        print_with_buffer(str, buffer)
        return s


    def create_new_sample(self, p_name, buffer):
        new_sample = dict()
        if not p_name:
            p_name = "sample_" + self.samples_name_i.__str__()
            self.samples_name_i += 1
        new_sample[consts.name] = p_name
        new_sample[consts.ACTORS_LIST] = copy.deepcopy(self.selected_agents)
        new_sample[consts.filters] = list()
        for f in self.filter_list:
            if f[consts.active]:
                new_sample[consts.filters].append(f)
        return new_sample


    def get_sample(self, p_name=None, buffer=None):
        for s in self.samples.values():
            if s[consts.ACTORS_LIST] == self.selected_agents:
                return True, s
        if p_name and p_name in self.samples.keys():
            return False, self.samples[p_name]
        else:
            return False, False

    def display_samples(self, buffer=None):
        if self.samples:
            str = "Your samples are:"
            for s in self.samples.values():
                str += "\n - %s, %d actors " % (s[consts.name], len(s[consts.ACTORS_LIST]))
                str += self.sample_selection_method_str(sample=s)
            str += "\n[Note: To see the list of actors for each filter, use command \"display one_sample -name nameofyoursample\"]"

        else:
            str = "You have no saved samples."
        print_with_buffer(str, buffer)
        return self.samples

    def sample_selection_method_str(self, sample, display_full_filter=False):
        if sample[consts.filters]:
            if display_full_filter:
                str_filters = "\n\t- " + "\n\t- ".join([self.filters_to_str(f, display_activation_status=False) for f in sample[consts.filters]])
            else:
                str_filters = ", ".join([f[consts.name] for f in sample[consts.filters]])
            str = "selected through filters %s" % str_filters
        else:
            str = "selected randomly."
        return str

    def display_one_sample(self, p_name, buffer=None):
        if p_name in self.samples.keys():
            sample = self.samples[p_name]
            selection_method_str = self.sample_selection_method_str(sample, True)
            str = "Actors in sample %s are: %s.\nThey were %s" % (p_name, ", ".join(sample[consts.ACTORS_LIST]), selection_method_str)
            print_with_buffer(str, buffer)
            return sample
        else:
            str = "ParameterError: There is no sample with this name."
            print_with_buffer(str, buffer)
            self.display_samples(buffer)


    ## ---------------------------------------      Get and compute Stats    -------------------------------- ##
    ## ------------------------------------------------------------------------------------------------------ ##


    def count_actors(self, p_days, p_att, p_op, p_val, buffer):
        tmp_copy_actors, _ = self.apply_filter(p_days=p_days, p_att=p_att, p_operator=p_op, p_val=p_val, buffer=buffer, save=False)
        tmp_filter_string = self.filters_to_str2(p_days, p_att, p_val, p_op, None)
        n_actors = len(tmp_copy_actors)
        print_with_buffer("We have %d agents with %s" % (n_actors, tmp_filter_string))
        return n_actors

    def get_stats(self, p_att, p_fct_list, p_days=[], p_sample_names=[], buffer=None, fig=None, using_gui=False):
        """
        Execute a user query involving stats.
        :param p_att:
        :param p_fct:
        :param p_days:
        :param p_name:
        :param buffer:
        :return:
        """
        if not p_days:
            p_days = list(range(1, self.n_days))

        if not p_sample_names:
            print_with_buffer("You did not specify for which sample you want to get the stats. We'll use your current selection and create a new sample with it.")
            sample = self.save_sample(p_name=None, buffer=buffer)
            p_sample_names = list(sample[consts.name])

        stat_objects_list = list()

        for sample_name in p_sample_names:
            for att in p_att:
                stat_obj = self.get_stat_obj(p_sample_name=sample_name, p_att=att)
                if not stat_obj:
                    stat_obj = self.compute_stats(p_sample_name=sample_name, p_att=att, p_days=p_days, p_name=sample_name, buffer=buffer)

                stat_objects_list.append(stat_obj)
        # stat_objects_list = list(set(stat_objects_list))
        stat_objects_list = helper.remove_duplicates_from_list_of_dicts(stat_objects_list)

        self.plot_stats(stat_objects_list=stat_objects_list, p_att=p_att, p_fct_list=p_fct_list, p_days=p_days, buffer=buffer, fig=fig, using_gui=using_gui)


    def compute_stats(self, p_sample_name, p_att, p_days=[], p_name=None, stat_obj=None, buffer=None):
        """
        Compute stats --> creates a new stat object that is saved in self.stats
        :param p_sample_name:
        :param p_fct:
        :param p_days:
        :param p_name:
        :param buffer:
        :return:
        """
        print_with_buffer("Wait, computing stats for %s %s... " % (p_att, p_sample_name))
        # get stat values (all)

        if stat_obj:
            new_stat = stat_obj
        else:
            new_stat = self.create_new_stat_obj(p_sample_name, p_name, p_att)
        stat_res = dict()
        for fct in consts.STAT_FCT_VALUES_IN:
            stat_res[fct] = dict()
        min_val, min_idx, min_overall_idx = 1, 0, 0
        min_overall_values = []
        max_val = []


        for day in p_days:
            values = self.get_att_val(self.samples[p_sample_name][consts.ACTORS_LIST], p_att, day)
            # print(values)
            values = list(filter(lambda a: a != "thisisfalse", values))
            # print(values)
            stat_res[consts.val_list][day] = values
            stat_res[consts.mean][day] = statistics.mean(values)
            stat_res[consts.median][day] = statistics.median(values)
            stat_res[consts.std_dev][day] = statistics.stdev(values)
            stat_res[consts.var][day] = statistics.variance(values)
            stat_res[consts.min][day] = min(values)

            min_tmp, idx_tmp = min((val, idx) for (idx, val) in enumerate(values))
            if min_tmp < min_val:
                min_val, min_idx = min_tmp, idx_tmp

            if not min_overall_values:
                min_overall_values = copy.deepcopy(values)
            else:
                for i, v in enumerate(values):
                    min_overall_values[i] += v
                _, min_overall_idx = max((val, idx) for (idx, val) in enumerate(values))

            if not max_val:
                max_val = copy.deepcopy(values)
            else:
                for i, v in enumerate(values):
                    max_val[i] += v
                _, idx_max = max((val, idx) for (idx, val) in enumerate(values))


        for day in p_days:
            stat_res[consts.min_ever_actor][day] = stat_res[consts.val_list][day][min_idx]
            stat_res[consts.min_overall_actor][day] = stat_res[consts.val_list][day][min_idx]
            stat_res[consts.max_actor][day] = stat_res[consts.val_list][day][idx_max]

        new_stat[consts.stat_res][p_att] = stat_res
        # print_with_buffer(new_stat, buffer)
        self.stats[p_name] = new_stat

        return new_stat


    def get_stat_obj(self, p_sample_name, p_att):
        """
        Returns a stat object is it already exists.
        :return:
        """
        if p_sample_name in self.stats.keys():
            # print(self.stats[p_sample_name]['stat_res'])
            return self.stats[p_sample_name]
        else:
            return False


    def create_new_stat_obj(self, p_sample_name, p_name, p_att):
        """
        Creates a new empty stat object
        :return:
        """
        new_stat = dict()
        new_stat[consts.NAME] = p_name
        new_stat[consts.actor_sample] = p_sample_name
        # new_stat[consts.ATTRIBUTE] = p_att
        new_stat[consts.stat_res] = dict()
        new_stat[consts.stat_res][p_att] = dict()
        return new_stat



    ## ---------------------------------------           Plot Stats          -------------------------------- ##
    ## ------------------------------------------------------------------------------------------------------ ##

    def plot_stats(self, stat_objects_list, p_att, p_fct_list, p_days=[], buffer=None, fig=None, using_gui=False):
        if not fig:
            import matplotlib.pyplot as plt
            fig = plt.figure()
        """
        Plots the stat ask asks by in the user command.
        :param stat_res:
        :param p_att:
        :param p_fct:
        :param p_days:
        :param p_name:
        :param buffer:
        :return:
        """
        only_one = True if len(stat_objects_list) == 1 and len(p_fct_list) == 1 and len(p_att) == 1 else False


        ax = fig.add_subplot()

        scatter_list, labels_list, lines_list = list(), list(), list()

        for j, stat_obj in enumerate(stat_objects_list):

            for i_att, attribute in enumerate(p_att):
                # print(attribute, consts.linestyles[i_att])

                if attribute not in stat_obj[consts.stat_res].keys():
                    self.compute_stats(p_sample_name=stat_obj[consts.actor_sample], p_att=attribute, p_days=p_days, p_name=stat_obj[consts.name], stat_obj=stat_obj, buffer=buffer)
                stat_res = stat_obj[consts.stat_res][attribute]
                sample = self.samples[stat_obj[consts.actor_sample]]
                sample_info_str = " for the %d actors\nof sample %s" % (len(sample[consts.ACTORS_LIST]), sample[consts.name])

                fct_str = ", ".join(p_fct_list)
                # if only_one:
                #     title = fct_str + " of " + ", ".join(p_att) + sample_info_str
                #     label = None
                # else:
                #     title = fct_str + " of " + ", ".join(p_att)
                #     label = " of " + attribute + sample_info_str
                title, label = "", ""
                if len(p_fct_list) == 1:
                    title = p_fct_list[0]
                else:
                    title = ", ".join(p_fct_list)
                if len(p_att) == 1:
                    title += " of " + p_att[0]
                else:
                    title += " of " + ", ".join(p_att)
                    label = attribute
                if len(stat_objects_list) == 1:
                    title += sample_info_str
                else:
                    title += " for samples " + ", ".join([s[consts.name] for s in stat_objects_list])
                    label += sample_info_str
                x_list, y_list = list(), list()
                if label == "":
                    label = None

                for i_p_fct, p_fct in enumerate(p_fct_list):
                    marker = consts.markers[i_p_fct]
                    # print(p_fct, marker)
                    if len(p_fct_list) > 1:
                        new_label = p_fct + " " + label
                    else:
                        new_label = label
                    if p_fct == consts.val_list:
                        plotting_for_multiple_agents = isinstance(stat_res[consts.val_list][p_days[0]], list)
                        if plotting_for_multiple_agents:
                            # for each agent
                            for i in range(len(stat_res[consts.val_list][p_days[0]])):
                                list_values_y_for_agent_i = list()
                                list_values_x_for_agent_i = list()
                                # for each day
                                for day in stat_res[consts.val_list].keys():
                                    list_values_x_for_agent_i.append(day)
                                    list_values_y_for_agent_i.append(stat_res[consts.val_list][day][i])
                                x_list.append(list_values_x_for_agent_i)
                                y_list.append(list_values_y_for_agent_i)
                            if only_one and len(p_att) <2:
                                self.plot_multiple_agents(ax=ax, x_lists=x_list, y_lists=y_list, y_label=p_att, title=title, label=None, color=None)
                            else:
                                self.plot_multiple_agents(ax=ax, x_lists=x_list, y_lists=y_list, y_label=p_att, title=title, label=new_label, color=consts.colors[j], linestyle=consts.linestyles[i_att])
                    else:
                        # print("check we are here", j, i_att, i_p_fct)
                        # print(stat_obj[consts.name], attribute, p_fct)
                        x_list, y_list = list(), list()
                        for x_elt, y_elt in stat_res[p_fct].items():
                            x_list.append(x_elt)
                            y_list.append(y_elt)
                            # std_dev_list = list(stat_res[consts.std_dev].values()) if p_fct == consts.mean else None
                            std_dev_list = None
                        scatter, line = self.plot(ax, x_list=x_list, y_list=y_list, std_dev=std_dev_list, marker=marker, label=new_label, color=consts.colors[j], linestyle=consts.linestyles[i_att])
                        scatter_list.append(scatter)
                        lines_list.append(line)
                        labels_list.append(new_label)

        if scatter_list:
            fake_lines_for_legend = list()
            for i_line, line in enumerate(lines_list):
                fake_lines_for_legend.insert(i_line, Line2D([0,1],[1,0], marker=line.get_marker(), linestyle=line.get_linestyle(), color=line.get_color()))
            ax.set_title(title)
            ax.set_xticks(x_list)
            ax.set_xticklabels(x_list)
            ax.set_ylabel(", ".join(p_att))
            ax.set_xlabel(consts.DAYS)
            # plt.gca().legend()
            ax.legend(fake_lines_for_legend, labels_list, fontsize=8, scatterpoints=1)
        # fig.show()

        if not using_gui:
            print("show plot")
            plt.show()
        else:
            return fig



    def plot_multiple_agents(self, ax, x_lists, y_lists, y_label, title, label, color, linestyle=consts.linestyles[0]):
        """
        Plots values for multiple agents (list of individual values).
        :param x_lists:
        :param y_lists:
        :param y_label:
        :param title:
        :return:
        """
        # Points
        x_flattened = [item for sublist in x_lists for item in sublist]
        y_flattened = [item for sublist in y_lists for item in sublist]
        c = Counter(zip(x_flattened,y_flattened))
        s = [10*c[(xx,yy)] for xx,yy in zip(x_flattened, y_flattened)]
        if color:
            ax.scatter(x_flattened, y_flattened, s=s, color=color)
        else:
            ax.scatter(x_flattened, y_flattened, s=s)

        # Connect points
        for i in range(len((x_lists))):
            x_one_agent = x_lists[i]
            y_one_agent = y_lists[i]
            if i == 0:
                self.plot_one_of_multiple_agents(ax, x_one_agent, y_one_agent, color, label, linestyle)
            else:
                self.plot_one_of_multiple_agents(ax, x_one_agent, y_one_agent, color, None, linestyle)

        ax.set_title(title)
        ax.set_xticks(x_flattened)
        ax.set_xticklabels(x_flattened)
        ax.set_ylabel(y_label)
        ax.set_xlabel(consts.DAYS)
        # ax.gca().legend()
        ax.legend()
        # plt.show()
        # return plt

    def plot_one_of_multiple_agents(self, ax, x_list, y_list, color, label, linestyle=consts.linestyles[0]):
        """
        Plots values for one of multiple agents --> adds points in an already existing plot.
        :param x_list:
        :param y_list:
        :param plt:
        :return:
        """
        if color:
            if label:
                line, = ax.plot(x_list, y_list, color=color, label=label, linestyle=linestyle)
                ax.legend(handler_map = {line: HandlerLine2D(numpoints=1)})
            else:
                ax.plot(x_list, y_list, color=color, linestyle=linestyle)
        else:
            ax.plot(x_list, y_list)

    def get_density(self, x_list, y_list):
        c = Counter(zip(x_list,y_list))
        s = [10*c[(xx,yy)] for xx,yy in zip(x_list,y_list)]
        return s


    def plot(self, ax, x_list, y_list, std_dev=None, marker=consts.markers[0], label=None, color=consts.colors[0], linestyle=consts.linestyles[0]):
        """
        Plots agregated values in one stat function, e.g. "mean".
        :param x_list:
        :param y_list:
        :param y_label:
        :param title:
        :return:
        """
        # print(marker)
        density = self.get_density(x_list, y_list)
        # print(x_list)
        # print(density)
        if marker:
            density = [d*5 for d in density]
        scatter = ax.scatter(x_list, y_list, s=density, marker=marker, color=color)
        if std_dev:
            print("line 1357")
            print(std_dev)

            ax.errorbar(x_list, y_list, std_dev, color=color)
        line, = ax.plot(x_list, y_list, color=color, marker=marker, label=label, linestyle=linestyle)
        # plt.show()
        return scatter, line
    #
    # def add_to_plot(self, x_list, y_list, plt, color=consts.colors[0], linestyle=consts.linestyles[0]):
    #     plt.scatter(x_list, y_list, s=self.get_density(x_list, y_list), color=color)
    #     plt.plot(x_list, y_list, color=consts.colors[0], linestyle=linestyle)


    ## ---------------------------------------   Query on one specific agent -------------------------------- ##
    ## ------------------------------------------------------------------------------------------------------ ##

    def get_att_values(self, p_actor, p_days, buffer=None):
        """
        Displays the attributes (BELIEFS) of a specific agent. 2 modes:
            - a day is selected:    returns the list of attributes and their values for that day
            - no day is selected:   returns just the list of attributes attached to that actor (no values)
        :param p_actor: name of the actor
        :param p_days: day
        :param buffer:
        :return:
        """
        print("Function deprecated", buffer)
        return False









    ############################################################################################################
    ##                                         RUN DEMO AND AUTOTESTS                                         ##
    ############################################################################################################

    def demo(self, autotest=False, buffer=None):
        """
        Demo function, helps the user understand the system by showing them example queries.
        :param autotest: boolean, if True, demo is slow and pauses between every command, otherwise demo is fast, doesn't give explanations and doesn't pause between queries (--> it's kind of a developer mode)
        :param buffer:
        :return:
        """
        if autotest:
            with open("psychsim/domains/groundtruth/explore_simulation/demo.json", 'rb') as f:
                content = json.load(f)
        else:
            with open("psychsim/domains/groundtruth/explore_simulation/demo.json", 'rb') as f:
                content = json.load(f)
        for i, ex in enumerate(content):
            query = ex["command"]
            text = ex["explanations"]
            if autotest:
                print(colored("Wait while we execute predefined queries...", "red"))
                print(colored(query, "green"))
                res = self.execute_query(preprocess(query))
            else:
                if i == 0:
                    next = input(colored("We thought we would make it easy for you :-)\nWe will walk you through an example with pre-written queries. You'll just have to press \"y\" to execute the next query when you're ready.\nShould we start? (y: yes, q: quit) > ", "red"))
                    if next.lower() == "q":
                        exit(1)
                print(colored(text, "blue"))
                print(colored(query, "green"))
                res = self.execute_query(preprocess(query))
                if i < (len(content) - 1):
                    next = input(colored("Next query? (y: yes, q: quit) > ", "red"))
                    if next.lower() == "q":
                        exit(1)
        self.query_log(text_intro="You can continue explore this simulation. ")



if __name__ == "__main__":

    argp = argparse.ArgumentParser()
    argp.add_argument('-i', metavar='instance', type=str, help='Instance number to process.')
    argp.add_argument('-r', metavar='run', type=str, help='Run number to process.')
    argp.add_argument("--autotest", help="Auto test using demo.json", action="store_true")
    argp.add_argument("--test", help="Test the tool yourself", action="store_true")
    argp.add_argument("--demo", help="Demo of the explore_simulation tool", action="store_true")

    args = argp.parse_args()

    logparser = LogParser(args.i, args.r)
    if (args.test):
        logparser.query_log()
    elif (args.autotest):
        logparser.demo(autotest=True)
    elif (args.demo):
        logparser.demo(autotest=False)
    else:
        argp.print_help()
        exit(0)

