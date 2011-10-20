import copy
import sys
from teamwork.multiagent.Multiagent import *

class Team(MultiagentSystem):
    """Base class for representing a team of entities"""
    
    def generateAllActions(self,seedAction={}):
	"""Generates all possible combined team actions consistent
	with the specified seed action (generates all possible
	combined team actions if seed action is left unspecified)"""
	agentList = []
	for agent in self.members():
	    if not seedAction.has_key(agent.name):
		agentList.append(agent)
	return self.__generateAllActions([seedAction],agentList)

    def __generateAllActions(self,actList,agents):
	if len(agents) > 0:
	    newList = []
	    for act in agents[0].actions:
		for combinedAct in actList:
		    newAct = copy.copy(combinedAct)
		    newAct[agents[0].name] = act
		    newList.append(newAct)
	    return self.__generateAllActions(newList,agents[1:])
	else:
	    return actList

    def composeActions(self,actions):
	"""Translates a dictionary of agent:action pairs into a single 
	string"""
	agentList = self.keys()
	actionString = actions[agentList[0]]
	for agent in agentList[1:]:
	    actionString = actionString + ' ' + actions[agent]
	return actionString

    def decomposeActions(self,actionString):
	"""Translates a string into a dictionary of agent:action
	pairs"""
	actionList = string.split(actionString)
	actions = {}
	for agent in range(len(self.keys())):
	    actions[self.keys()[agent]] = actionList[agent]
	return actions

    # This method should probably be in ComMTDP
    def individualObs(self,state,actions,observation,agent):
	"""Default method for returning the probability distribution
	over observations for an individual agent.  Returns a uniform
	distribution.  Should be overwritten."""
        raise NotImplementedError

    # This method should probably be in ComMTDP
    def observableProb(self,state,actions,observation,agent):
	"""Handles the observation function for features that are
	completely observable.  If the observation does not match the
	true state on the completely observable features, then this
	function returns 0.0; otherwise, it returns 1.0"""
	for key in observation.keys():
	    if key[0] != '_' and \
	       self[agent].observations[key] == 'observable':
		if state[key] != observation[key]:
		    return 0.0
	else:
	    return 1.0
