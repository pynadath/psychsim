from psychsim.pwl import *
        
def maximizeFeature(key,agent):
    return KeyedTree(setToFeatureMatrix(rewardKey(agent),key,1.))
        
def minimizeFeature(key,agent):
    return KeyedTree(setToFeatureMatrix(rewardKey(agent),key,-1.))

def achieveFeatureValue(key,value,agent):
    return makeTree({'if': equalRow(key,value),
                     True: setToConstantMatrix(rewardKey(agent),1.),
                     False: setToConstantMatrix(rewardKey(agent),0.)})

def achieveGoal(key,agent):
    return makeTree({'if': trueRow(key),
                     True: setToConstantMatrix(rewardKey(agent),1.),
                     False: setToConstantMatrix(rewardKey(agent),0.),})

def minimizeDifference(key1,key2,agent):
    return makeTree({'if': greaterThanRow(key1, key2),
                     True: dynamicsMatrix(rewardKey(agent),{key1: -1.,key2: 1.}),
                     False: dynamicsMatrix(rewardKey(agent),{key1: 1.,key2: -1.})})
