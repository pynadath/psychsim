import re
import operator
import itertools
import os

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
    return  s
