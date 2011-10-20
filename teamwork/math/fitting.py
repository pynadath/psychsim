import copy
import string
import time
from types import *

import KeyedVector
from KeyedMatrix import *
from teamwork.math.KeyedTree import *
from ProbabilityTree import *

def expandPolicy(entity,name,interrupt=None,keys=[],debug=0):
    """
    @return: the dynamics that the given entity thinks govern the turn of the named other entity
    """
    other = entity.getEntity(name)
    policy = other.policy.compileTree(interrupt=interrupt,debug=debug)
    if not policy:
        return None
    policy = copy.deepcopy(policy)
    done = []
    for action in policy.leaves():
        if action in done:
            continue
        else:
            done.append(action)
        if debug > 0:
            print '\tExpanding:',action
        # Compute the specific dynamics for this action
        dynamics = entity.entities.getDynamics({name:action})
        if interrupt and interrupt.isSet():
            return None
        subtree = dynamics['state'].getTree()
        policy.replace(action,subtree)
        if interrupt and interrupt.isSet():
            return None
##         policy.prune()
##         if interrupt and interrupt.isSet():
##             return None
        if debug > 1:
            print '\t',subtree.simpleText()
    return policy

def getActionKeys(entity,sequence):
    actionKeys = []
    for key in entity.getGoalVector()['action'].keys():
        actionKeys.append(key)
    for turns in sequence:
        for name in turns:
            # Consider each agent who can act at this point in time
            other = entity.getEntity(name)
            for key in other.policy.tree.getKeys():
                if key['class'] == 'observation':
                    if not key in actionKeys:
                        actionKeys.append(key)
    return actionKeys

def getLookaheadTree(entity,chosenAction,sequence,
                     local=False,choices=None,
                     goals=None,interrupt=None,debug=0):
    """
    @param chosenAction: the action being projected
    @type chosenAction: L{teamwork.action.PsychActions.Action}[]
    @param sequence: the turns anticipated by this agent in its lookahead, as a list of turns, where each turn is a list of names
    @type sequence: str[][]
    @param local: if C{True}, then the entity will compile a locally optimal policy, expecting itself to behave according to whatever mental model it has of itself; otherwise, it will plan over I{all} of its turns in the sequence (more strategic).  Default is C{False}
    @type local: boolean
    @param choices: the possible actions to be considered in this policy (if C{None}, defaults to all available actions)
    @type choices: L{Action}[][]
    @param goals: if you want an expected value tree (as opposed to a reward-independent sum over state projections), then you can pass in a tree representing the reward function to use (default is to be reward-independent)
    @type goals: L{ProbabilityTree}
    @param interrupt: a thread Event, the compilation process will continually test whether the event is set; if it is, it will exit.  In other words, this is a way to interrupt the compilation
    @type interrupt: Event
    @return: a decision tree representing the dynamics of the given actions followed by the given sequence of agent responses.  The sequence is a list of lists of agent name strings.  The agents named in list I{i} of the sequence apply their policy-driven actions at time I{i}, where time 0 occurs in parallel with the given entity's performance of the chosen action
    """
    if debug > 0 and chosenAction:
        print 'Lookahead for:',chosenAction
    if choices is None:
        choices = entity.actions.getOptions()
    # The sum over the state sequence
    total = None
    # The dynamics over the prior state sequence
    last = None
    # The policy trees of the other agents
    policies = {}
    actionKeys = []
##    actionKeys = getActionKeys(entity,sequence)
##    if debug > 0:
##        print 'Actions:',actionKeys
    # Replace policy leaves with action dynamics trees
    flag = chosenAction
    for turns in sequence:
        for name in turns:
            if name == entity.name and flag:
                # Can skip the acting entity once
                flag = not local
            elif not policies.has_key(name):
                if debug > 1:
                    print 'Expanding policy for:',entity.ancestry(),name
                policies[name] = expandPolicy(entity,name,interrupt,
                                              actionKeys,debug)
                if interrupt and interrupt.isSet():
                    return None
                if debug > 0:
                    print '\tPolicy tree w/dynamics has %d leaves' % \
                          (len(policies[name].leaves()))
                if debug > 1:
                    print 'Expanded policy:', policies[name]
    # Create projection
    if len(sequence) == 0:
        sequence = [[entity.name]]
    recursed = False
    for t in range(len(sequence)):
        # Step t in the lookahead
        turns = sequence[t]
        if debug > 0:
            print '-----------'
            print 'Time: %d/%d' % (t+1,len(sequence))
            print '-----------'
        subtree = None
        stepValue = None
        for name in turns:
            if debug > 0:
                print 'Turn:',name
            if name == entity.name:
                if chosenAction:
                    if debug > 0:
                        print '\tFixed action:',chosenAction
                    # Fix my action to the one chosen
                    action = {entity.name:chosenAction}
                    newTree = entity.entities.getDynamics(action)['state'].getTree()
                    # Do this fixed action only once
                    chosenAction = False
                elif local:
                    # Use mental model of myself
                    newTree = policies[name]
                    if debug > 0:
                        print '\tInserting policy of size',
                        print len(newTree.leaves())
                else:
                    horizon = len(sequence)-t
                    # Compute my policy over the rest of the horizon
                    if debug > 0:
                        print '----------------------------------------------'
                        print '\tComputing subpolicy of horizon:',horizon
                    newTree = entity.policy.compileTree(horizon=horizon,
                                                        choices=choices,
                                                        key='weights',
                                                        interrupt=interrupt,
                                                        debug=debug)
                    if interrupt and interrupt.isSet():
                        return None
                    recursed = True
                    if debug > 0:
                        print '\tFinished with horizon %d (%d leaves)' % \
                              (len(sequence)-t,len(newTree.leaves()))
                        print '----------------------------------------------'
            else:
                # Combine this agent's policy into the overall dynamics
                # for this time step
                newTree = policies[name]
                if debug > 0:
                    print '\tInserting %s\'s policy dynamics [%d leaves]' % (name,len(newTree.leaves()))
            if newTree.getValue():
                # Update transition probability at time t
                if subtree is None:
                    subtree = newTree
                else:
                    subtree += newTree
                if interrupt and interrupt.isSet():
                    return None
                if debug > 1:
                    print name,subtree.simpleText()
                    print
                # Update value at time t
                if goals:
                    if recursed:
                        subValue = newTree
                    else:
                        subValue = goals*newTree
                    if stepValue is None:
                        stepValue = subValue
                    else:
                        stepValue += subValue
        if interrupt and interrupt.isSet():
            return None
        # Compute transition probability to time t
        if debug > 0:
            print 'Multiplying overall projection by step %d dynamics [%d leaves]' % \
                  (t+1,len(subtree.leaves()))
        if last:
            last = subtree * last
        else:
            last = subtree
        if debug > 0:
            if total:
                print 'Adding step %d projection [%d leaves] to total [%d leaves]' % \
                      (t+1,len(last.leaves()),len(total.leaves()))
        if interrupt and interrupt.isSet():
            return None
        # Update total value to time t
        if total is None:
            total = stepValue
        else:
            total += stepValue
        if debug > 0:
            print 'Total so far:',len(total.leaves()),'leaves'
        if recursed:
            # Recursive call has already computed the rest of the sequence
            break
    return {'transition':last,
            'total': total}
##                'total': total.scale(1./float(len(sequence)))}

def getDiffTree(entity,action1,action2,sequence,debug=1):
    """Returns a decision tree representing the state difference
    between the two specified actions (i.e., S(action1)-S(action2)),
    subject to the provided turn sequence, following the format for
    L{getLookaheadTree}."""
    gValue = entity.policy.getActionTree(action1)
    if debug > 0:
        print 'EV[%s] = %s' % (action1,gValue.simpleText())
    bValue = entity.policy.getActionTree(action2)
    if debug > 0:
        print 'EV[%s] = %s' % (action2,bValue.simpleText())
    return gValue, bValue
    
def sign(value):
    """Returns 1 for any positive value, -1 for any negative value,
    and 0 for any zero value"""
    return value.__cmp__(0.)
    
def findConstraint(entity,goodAction,badAction,sequence,debug=None):
    """Returns a dictionary of possible singleton goal weight changes
    that satisfy the constraint that the specified entity prefer the
    goodAction over the badAction given the provided lookahead turn
    sequence.  If the constraint is satisfied by the current goal
    weights, then the returned dictionary is empty"""
    # Compute dynamics
    goodV,badV  = getDiffTree(entity,goodAction,badAction,sequence,
                              max(0,debug-1))
    diffTree = goodV - badV
    if debug > 0:
        print 'Tree:',diffTree.simpleText()
    # Find leaf node for current state
    state = getStateVector(diffTree.getKeys(),entity)
    if debug > 0:
        print 'State:',state
    # Apply goals to difference
    goals = entity.getGoalVector()['state']
    if debug > 0:
        print 'Goals:',goals
        goodTotal = goodV[state]*state
        print 'EV[%s] =' % (goodAction),goodTotal
        print 'EV[%s] = %5.3f' % (goodAction,float(goals*goodTotal))
        badTotal = badV[state]*state
        print 'EV[%s] =' % (badAction),badTotal
        print 'EV[%s] = %5.3f' % (badAction,float(goals*badTotal))
        print 'Delta EV =',goodTotal-badTotal
        print 'Delta EV = %5.3f' % \
              (float(goals*goodTotal)-float(goals*badTotal))
        print 'Difference Tree:',diffTree[state].simpleText()
    diffVector = diffTree[state]*state
    if debug > 0:
        print 'Difference Vector:',diffVector
    diff = float(goals*diffVector)
    solutions = {}
    constraint = {'delta':diff,
                  'plane':diffVector,
                  'solution':solutions,
                  'slope':{},
                  }
    if diff > 0.:
        if debug > 0:
            print 'Correct: Chose %s over %s' % (goodAction,badAction)
    else:
        if debug > 0:
            print 'Incorrect: Chose %s over %s' % (badAction,goodAction)
            print 'Off by:',abs(diff)
        for key in goals.keys():
            try:
                slope = diffVector[key]
            except KeyError:
                slope = 0.
            constraint['slope'][key] = slope
            try:
                delta = -diff/slope-epsilon
            except ZeroDivisionError:
                delta = 'NaN'
            if debug > 0:
                print key
                print '\tCurrent Value:',goals[key]
                print '\tSlope:',slope
                print '\tdelta:',delta
##            new = goals[key]+delta
##            if (not sign(goals[key]) or not sign(new) or \
##               (sign(goals[key]) == sign(new))) and \
##               (new >= Interval.FLOOR and new < Interval.CEILING):
##                if debug > 0:
##                    print '\tNew Value:',new
##                solutions[key] = new
##            else:
##                if debug > 0:
##                    print '\tInvalid change'
    return constraint

def findAllConstraints(entity,goodAction,sequence,debug=0):
    constraints = []
    for action in entity.actions.getOptions():
        if action != goodAction:
            constraints.append(findConstraint(entity,goodAction,action,
                                              sequence,debug))
    return constraints
