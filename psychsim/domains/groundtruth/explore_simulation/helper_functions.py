import re
import operator
import itertools
import os
import more_itertools as mit

try:
    import psychsim.domains.groundtruth.explore_simulation.query_gt_consts as consts
except ModuleNotFoundError:
    import query_gt_consts as consts


def remove_numbers_from_string(input_string):
    return re.sub(r'\d+', '', input_string)


def print_with_buffer(message, buffer=None):
    if buffer:
        print(message, buffer)
    else:
        print(message)


def string_between_parentheses(s):
    return  s[s.find("(")+1:s.find(")")]


def extract_floats(s):
    return re.findall("\d+\.\d+", s)


def sort_dic_by_values(x):
    return sorted(x.items(), key=operator.itemgetter(1))


def add_space_at_end(s, n=1):
    for i in range(n):
        s += " "
    return s


def get_list_of_files(mypath, ext=None):
    files = [f for f in os.listdir(mypath) if os.path.isfile(os.path.join(mypath, f))]
    if ext:
        files = [f for f in files if f.endswith('.'+ext)]
    return files


def count_files(mypath, ext=None):
    return len(get_list_of_files(mypath, ext))


def str_distribution(distrib, tabs=""):
    s = ""
    elts = distrib._domain.values()
    if len(elts) > 1:
        tabs += "\t"
    for el in elts:
        len_el = len(str(el).expandtabs())
        s += tabs + "%s \t (certainty: %d%%)\n" % (str(el), 100*distrib[el])
    return s[:-1]


def get_val(distrib):
    elts = distrib._domain.values()
    if len(elts) > 1:
        print("ERROR: we should not try to get a single value when certainty is not 100%%!!!!!")
    else:
        for el in elts:
            return el


def str_aligned_values(dictionary, tabs=""):
    max_length_key = max(dictionary.keys(), key=len)
    max_length = len(max_length_key)
    s = ""
    for key, value in dictionary.items():
        spaces = max_length - len(key) + 2
        s += str_key_value_with_space_between(key, value, n_space=spaces, tabs=tabs) + "\n"
    return s[:-1]


def str_key_value_with_space_between(key, value, n_space=1, separator=":", tabs=""):
    s = tabs + key + separator
    for i in range(n_space):
        s += " "
    s += "\t" + value
    return s


def compare(v1, v2, op):
    if (isinstance(v1, float) or isinstance(v1, int)) and (isinstance(v1, float) or isinstance(v1, int)):
        all_operations_valid = True
    else:
        all_operations_valid = False
    if op == "=":
        return  v1 == v2
    elif op == '<' and all_operations_valid:
        return v1 < v2
    elif op == '>' and all_operations_valid:
        return v1 > v2
    elif op in ['<=', '=<'] and all_operations_valid:
        return v1 <= v2
    elif op in ['>=', '=>'] and all_operations_valid:
        return v1 >= v2
    # print("ERROR: Cannot compare %s (%s) with %s (%s)" % (v1.__str__(), type(v1), v2.__str__(), type(v2)))
    return False

def actor_number_to_name(i):
    len_i = len(i)
    s = "Actor"
    for j in range(4 - len_i):
        s += '0'
    s += i
    return s

def find_ranges(iterable):
    """Yield range of consecutive numbers."""
    for group in mit.consecutive_groups(iterable):
        group = list(group)
        if len(group) == 1:
            yield group[0]
        else:
            yield group[0], group[-1]


def remove_duplicates_from_list_of_dicts(my_list):
    new_list = list()
    for elt in my_list:
        if elt not in new_list:
            new_list.append(elt)
    return new_list