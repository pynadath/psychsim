from pwl import *
        
def maximizeFeature(key):
    return KeyedTree(KeyedVector({key: 1.}))
        
def minimizeFeature(key):
    return KeyedTree(KeyedVector({key: -1.}))

def achieveFeatureValue(key,value):
    return makeTree({'if': equalRow(key,value),
                     True: KeyedVector({CONSTANT: 1.}),
                     False: KeyedVector({CONSTANT: 0.})})

def minimizeDifference(key1, key2):
    return makeTree({'if': greaterThanRow(key1, key2),
                     True: KeyedVector({key1: -1., key2: 1.}),
                     False: KeyedVector({key1: 1., key2: -1.})})
