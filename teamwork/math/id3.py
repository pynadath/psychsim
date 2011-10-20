"""
This module contains the functions for calculating the information gain of a
dataset as defined by the ID3 (Information Theoretic) heuristic.
"""
import copy
import math

def frequency(data,attr):
    """Computes the histogram over values for the given attribute
    @param data: the data to be analyzed
    @type data: dict[]
    @param attr: the attribute to be analyzed
    @return: a dictionary of frequency counts, indexed by attribute values
    @rtype: dict
    @warning: assumes all fields have the same number of possible values
    """
    val_freq = {}
    # Calculate the frequency of each of the values in the target attr
    for record in data:
        value = record[attr]
        if value is not None:
            val_freq[value] = 0.
    for record in data:
        weight = pow(float(len(val_freq)),record.values().count(None))
        if record[attr] is None:
            # This counts equally toward all counts
            for value in val_freq.keys():
                val_freq[value] += weight/float(len(val_freq))
        else:
            val_freq[record[attr]] += weight
    return val_freq

def entropy(data, target_attr):
    """
    Calculates the entropy of the given data set for the target attribute.
    """
    val_freq = frequency(data,target_attr)
    data_entropy = 0.0
    total = float(sum(val_freq.values()))
    for freq in val_freq.values():
        prob = freq/total
        data_entropy -= prob * math.log(prob, 2) 
        
    return data_entropy
    
def gain(data, attr, target_attr):
    """
    Calculates the information gain (reduction in entropy) that would
    result by splitting the data on the chosen attribute (attr).
    """
    val_freq = frequency(data,attr)
    subset_entropy = 0.0

    # Calculate the sum of the entropy for each subset of records weighted
    # by their probability of occuring in the training set.
    total = float(sum(val_freq.values()))
    for val in val_freq.keys():
        val_prob = val_freq[val] / total
        data_subset = []
        for record in data:
            if record[attr] == val:
                data_subset.append(record)
            elif record[attr] is None:
                datum = copy.copy(record)
                datum[attr] = val
                data_subset.append(datum)
        subset_entropy += val_prob * entropy(data_subset, target_attr)

    # Subtract the entropy of the chosen attribute from the entropy of the
    # whole data set with respect to the target attribute (and return it)
    return (entropy(data, target_attr) - subset_entropy)
            
