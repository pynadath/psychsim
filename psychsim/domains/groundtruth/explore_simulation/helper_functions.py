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
