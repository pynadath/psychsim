"""
This module holds functions that are responsible for creating a new
decision tree and for using the tree for data classificiation.
"""
from id3 import frequency

def majority_value(data, target_attr):
    """
    Creates a list of all values in the target attribute for each record
    in the data list object, and returns the value that appears in this list
    the most frequently.
    """
    histogram = frequency(data,target_attr)
    highest_freq = 0
    most_freq = None
    for value,count in histogram.items():
        if most_freq is None or count > highest_freq:
            most_freq = value
            highest_freq = count
    return most_freq

def unique(lst):
    """
    Returns a list made up of the unique values found in lst.  i.e., it
    removes the redundant values in lst.
    """
    unique = []
    # Cycle through the list and add each value to the unique list only once.
    for item in lst:
        if not item in unique:
            unique.append(item)
    # Return the list with all redundant values removed.
    return unique

def get_values(data, attr):
    """
    Creates a list of values in the chosen attribute for each record in data,
    prunes out all of the redundant values, and return the list.  
    """
    return unique([record[attr] for record in data \
                   if record[attr] is not None])

def choose_attribute(data, attributes, target_attr, fitness):
    """
    Cycles through all the attributes and returns the attribute with the
    highest information gain (or lowest entropy).
    """
    # dp: removed unnecessary copy
##     data = data[:]
    best_gain = 0.0
    best_attr = None

    for attr in attributes:
        if attr != target_attr:
            gain = fitness(data, attr, target_attr)
            if best_attr is None or gain >= best_gain:
                best_gain = gain
                best_attr = attr
    return best_attr

def get_examples(data, attr, value):
    """
    Returns a list of all the records in <data> with the value of <attr>
    matching the given value.
    """
    return filter(lambda r:r[attr] == value or r[attr] is None,data)

def get_classification(record, tree):
    """
    This function recursively traverses the decision tree and returns a
    classification for the given record.
    """
    # If the current node is a string, then we've reached a leaf node and
    # we can return it as our answer
    if type(tree) == type("string"):
        return tree

    # Traverse the tree further until a leaf node is found.
    else:
        attr = tree.keys()[0]
        t = tree[attr][record[attr]]
        return get_classification(record, t)

def classify(tree, data):
    """
    Returns a list of classifications for each of the records in the data
    list as determined by the given decision tree.
    """
    # dp: removed unnecessary copy
##     data = data[:]
    classification = []
    
    for record in data:
        classification.append(get_classification(record, tree))

    return classification

def create_decision_tree(data, attributes, target_attr, fitness_func):
    """
    Returns a new decision tree based on the examples given.
    """
    # dp: removed unnecessary copy
##     data = data[:]
    vals = get_values(data,target_attr)
    default = majority_value(data, target_attr)
    # If the dataset is empty or the attributes list is empty, return the
    # default value. When checking the attributes list for emptiness, we
    # need to subtract 1 to account for the target attribute.
    if not data or len(attributes) <= 1:
        return default
    # If all the records in the dataset have the same classification,
    # return that classification.
    elif len(vals) == 1:
        return vals[0]
    else:
        # Choose the next best attribute to best classify our data
        best = choose_attribute(data, attributes, target_attr,
                                fitness_func)
        # Create a new decision tree/node with the best attribute and an empty
        # dictionary object--we'll fill that up next.
        tree = {best:{}}

        # Create a new decision tree/sub-node for each of the values in the
        # best attribute field
        subattributes = [attr for attr in attributes if attr != best]
        for val in get_values(data, best):
            # Create a subtree for the current value under the "best" field
            subdata = get_examples(data,best,val)
            if attributes.index(best) == 6:
                print val,len(subdata)
            subtree = create_decision_tree(subdata,subattributes,
                                           target_attr,fitness_func)

            # Add the new subtree to the empty dictionary object in our new
            # tree/node we just created.
            tree[best][val] = subtree
        if len(tree[best]) == 0:
            # Not sure whether this should ever happen
            return create_decision_tree(data,subattributes,
                                        target_attr,fitness_func)
    return tree
