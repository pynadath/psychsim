consistencyCalculationAvailable = True
try:
    from teamwork.math.KeyedVector import UnchangedRow
    from MemoryAgent import MemoryAgent
    from teamwork.math.probability import Distribution
    from teamwork.math.Keys import StateKey,ConstantKey
    from cvxopt.base import matrix,print_options
    from cvxopt.solvers import qp
    from cvxopt import solvers
    solvers.options['show_progress'] = False
    from numpy.lib.polynomial import poly1d
    from copy import deepcopy
except ImportError:
    consistencyCalculationAvailable = False

class ConsistentAgent(MemoryAgent):
    def __init__(self,name):
        MemoryAgent.__init__(self,name)

    def calculateMessageConsistency(self,msg):

        #we can short-circuit things if our agent has no memory.. thus there is nothing to be consistent with
        if len(self.memory) == 0:
            return {"currentConsistency"  : 0,
                    "proposedConsistency" : 0,
                    "proposedMemory"      : [],
                    "proposedBeliefState" : self.getAllBeliefs()['state']}
        else:
            currentConsistency = self.getMemoryConsistency()

            proposedMemory = self.__propagateBeliefsBackInTime__(msg)
            result = self.__propagateBeliefsForwardInTime__(memory=proposedMemory)
            proposedConsistency = self.getMemoryConsistency(memory=result['updatedMemory'])

            return {"currentConsistency" : currentConsistency, 
                    "proposedConsistency" : proposedConsistency, 
                    "proposedMemory" : result['updatedMemory'],
                    "proposedBeliefState" : result['updatedStateBeliefs']}

    def getMemoryConsistency(self,memory=None):
        if not memory:
            memory = self.memory

        #iterate through the memories and figure out how 'good' each taken action was compared to the others
        consistency = 1
        for mem in memory:
            actions = mem['actions']
            actor = actions.keys()[0]
            availableActions = self.entities[actor].actions.getOptions()
            avdict = {}
            bestValue = None
            worstValue = None
            for action in availableActions:
                av = self.entities[actor].actionValue(action,state=deepcopy(mem['previousBeliefs']))[0].items()[0][0]
                avdict[action[0]] = av
                if not bestValue:
                    bestValue = av
                else:
                    if av > bestValue:
                        bestValue = av
                if not worstValue:
                    worstValue = av
                else:
                    if av < worstValue:
                        worstValue = av

            performedValue = avdict[actions.values()[0][0]]
            gap = bestValue - worstValue
            actualGap = bestValue - performedValue

            if (gap != 0):
                consistency *= 1. - (actualGap/gap)

        return consistency





    def __solveForUniqueTreePath__(self,path,leaf,memory,currentState,specifiedEqualityConstraints=None):

        #inequality constraints
        gContents = []
        hContents = []

        keys = self.entities.getState().domain()[0].keys()[:]
        keys.remove(ConstantKey())


        for p in path: 
            multiplier = -1
            if not p[1]:
                multiplier = 1
            for key in keys:
                gContents.append(p[0][0].__getitem__(key) * multiplier)
            hContents.append(p[0][0].threshold * multiplier)
                    
        #equality constraints
        aContents = []
        bContents = []

        #if specifiedEqualityConstraints == None, then we assume we can use the current state values as the current
        #equality targets
        if not specifiedEqualityConstraints:
            for key in keys:
                row = leaf.getValue().__getitem__(key)
                leafContents = []

                if not isinstance(row,UnchangedRow):
                    for k in keys:
                        leafContents.append(row.__getitem__(k))
                    #the following should account for increment and settoconstant rows
                    value = currentState.items()[0][0][key] - row.__getitem__(ConstantKey())
                    bContents.append(value)
                    aContents.extend(leafContents)

        #otherwise we ONLY want to constrain certain values
        else:
            sec = specifiedEqualityConstraints[:]
            for key in keys:
                row = leaf.getValue().__getitem__(key)
                leafContents = []

                if not isinstance(row,UnchangedRow) and sec.__contains__(key):
                    for k in keys:
                        leafContents.append(row.__getitem__(k))
                    #the following should account for increment and settoconstant rows
                    value = currentState.items()[0][0][key] - row.__getitem__(ConstantKey())
                    bContents.append(value)
                    aContents.extend(leafContents)
                    #remember to remove the key from specified equality constraints
                    sec.remove(key)
            #now we add in any unadded specified constraints
            for key in sec:
                leafContents = []
                for k in keys:
                    if k == key:
                        leafContents.append(1)
                    else:
                        leafContents.append(0)
                value = currentState.items()[0][0][key]
                bContents.append(value)
                aContents.extend(leafContents)

        #finally, take care of the objective function
        #this attempts to minimize the squared distance between the newly proposed beliefs and the 
        #agent's previous memory of beliefs representing the agent's desire to keep its memory
        #as consistent as possible
        qContents = []
        pContents = []
        for key in keys:
            oldval = memory['previousBeliefs']['state'].items()[0][0][key]
#            oldval = currentState.items()[0][0][key]
            #I think the above was wrong because we want to minimize the agent's old memory, not the newly proposed one
            eq = poly1d([1,-2*oldval,oldval**2])
            qContents.append(eq.deriv()[0])
            for k in keys:
                if k == key:
                    #the 2nd derivitive will always reduce down to 2 in our case
                    pContents.append(2)
                else:
                    pContents.append(0)

        G = matrix(gContents, (len(keys), len(hContents)))
        G = G.trans()
        h = matrix(hContents, (len(hContents), 1))
        if len(bContents) == 0:
            A = None
            b = None
        else:
            A = matrix(aContents, (len(keys), len(bContents)))
            A = A.trans()
            b = matrix(bContents, (len(bContents), 1))

        q = matrix(qContents, (len(keys), 1))
        P = matrix(pContents, (len(keys), len(keys)))

#        print "G"
#        print G
#        print "h"
#        print h
#        print "A"
#        print A
#        print "b"
#        print b
#        print "P"
#        print P
#        print "q"
#        print q
#
        #solve the QP
        result = qp(P=P, q=q, G=G, h=h, A=A, b=b)
        if result['x'] == None:
            return None

        #we need to return the value of the objective function (sum of squares)
        objvalue = 0
        for key,index in zip(keys,range(len(keys))):
            objvalue += (currentState.items()[0][0][key] - result['x'][index]) ** 2

        return ({'objective':objvalue,'solution':dict(zip(keys,result['x']))})

    def __getStateIntegratedWithMessage__(self,msg):
        #debug: I need to reexamine this and see if there's a better way to apply the messages
        #we need the current state
        currentState = deepcopy(self.getAllBeliefs()['state'])

        #then update the current state to reflect the message contents
        #note that this doesn't seem to be able to handle messages referencing multiple states
        key = self.__getMessageContentKey__(msg)
        currentState.items()[0][0].unfreeze()
        currentState.items()[0][0].__setitem__(key,msg['factors'][0]['value'].items()[0][0])
        currentState.items()[0][0].freeze()

        return currentState

    def __getMessageContentKey__(self,msg):
        key = StateKey()
        key['entity'] = msg['factors'][0]['lhs'][1]
        key['feature'] = msg['factors'][0]['lhs'][3]
        return key

    def __propagateBeliefsForwardInTime__(self,memory=None):

        newBeliefs = []
        newCurrentBeliefs = None

        if not memory:
            memory = self.memory

        #we reverse the memory so that we start with the oldest memory first
        reverseMemory = deepcopy(memory)
        reverseMemory.reverse()
        for mem in reverseMemory:
            #get the dnyamics
            dynamics = self.entities.getDynamics(mem['actions'])['state']

            #apply the dynamics
            delta = dynamics.apply(mem['previousBeliefs']['state'])

            #apply the change in state
            newMem = delta * mem['previousBeliefs']['state']

            #append the new memory
            newBeliefs.append(newMem)

        #We're not quite done yet
        #the last belief in our newBeliefs list is actually the current belief - not a memory so we need to adjust
        newCurrentBeliefs = newBeliefs[-1]
        newBeliefs = newBeliefs[:-1]

        #now we reverse the new beliefs so that they align correctly with our old beliefs
        newBeliefs.reverse()

        #make a deep copy of the current memory
        updatedMemory = deepcopy(memory)

        #iterate through the beliefs and reset the state to what we just calculated
        for mem,beliefs in zip(updatedMemory[:-1],newBeliefs):
            mem['previousBeliefs']['state'] = beliefs

        #now just return the whole thing in a nicely packed dictionary
        return {'updatedMemory':updatedMemory,'updatedStateBeliefs':newCurrentBeliefs}

    def __propagateBeliefsBackInTime__(self,msg):
        updatedMemory = []

        #we need the current state as if the message had been accepted
        acceptedState = self.__getStateIntegratedWithMessage__(msg)
        equalityConstraints = [self.__getMessageContentKey__(msg)]

        #loop through the number of memories that this agent holds
        for memory in self.memory:

            #make a deep copy of our old memory
            newMemory = deepcopy(memory)

            #Get the dynamic for the most recent action that we remember
            dynamics = self.entities.getDynamics(memory['actions'])['state']

            #Here we get all the unique paths (i.e. paths leading to differnt leaves) for the given dynamic
            #for each unique path we'll construct a unique qp formulation
            allPaths = map(lambda x: (x.getPath(),x), dynamics.getTree().leafNodes())

            #iterate through all the possible paths and set up and solve the QP for each one
            bestMinResult = None
            bestSolution = None
            for path,leaf in allPaths: 
                result = self.__solveForUniqueTreePath__(path,leaf,memory,acceptedState,specifiedEqualityConstraints=equalityConstraints)
                if result == None:
                    continue

                if bestSolution == None or result['objective'] < bestMinResult:
                    bestMinResult = result['objective']
                    bestSolution = result['solution']

            #reset the additional equality constraints
            equalityConstraints = None

            #here we update our current state to be the solution we just found
            #debug - not sure if this is right
            for key in bestSolution.keys():
                acceptedState.items()[0][0].__setitem__(key,bestSolution[key])

            #then update the 'state' value entry with our new accepted state
            newMemory['previousBeliefs']['state'] = deepcopy(acceptedState)

            #then append the new instance of memory to an overall updated record of memory
            updatedMemory.append(newMemory)

        return updatedMemory

if __name__ == '__main__':
    from teamwork.messages.PsychMessage import Message

    from teamwork.shell.PsychShell import PsychShell
    
    #set up some keys
    bPowerKey = StateKey()
    bPowerKey['entity'] = 'Bully'
    bPowerKey['feature'] = 'power'

    vPowerKey = StateKey()
    vPowerKey['entity'] = 'Victim'
    vPowerKey['feature'] = 'power'

    #load the test file
    shell = PsychShell()
    shell.load("/home/ito/Documents/isi/projects/teamwork/simpleSchool.scn")
    agents = shell.scenario

    results = agents['Teacher'].entities.microstep(turns=[{'name':'Bully'}],hypothetical=True)['decision']['Bully']
    print "The teacher expects the bully to do the following: %s" % results
    print

    result = agents.microstep(turns=[{'name':'Bully'}])['decision']['Bully']
    print "But in reality, the bully does the following: %s" % result
    print
    print "After %s, the teacher's beliefs are as follows:" % result
    print "\t--> %s: %f" % (bPowerKey,agents['Teacher'].getAllBeliefs()['state'].items()[0][0][bPowerKey])
    print "\t--> %s: %f" % (vPowerKey,agents['Teacher'].getAllBeliefs()['state'].items()[0][0][vPowerKey])
    print 
    print "But the victim, who has an accurate representation of the world, has the following beliefs:"
    print "\t--> %s: %f" % (bPowerKey,agents['Victim'].getAllBeliefs()['state'].items()[0][0][bPowerKey])
    print "\t--> %s: %f" % (vPowerKey,agents['Victim'].getAllBeliefs()['state'].items()[0][0][vPowerKey])

    #construct a message
    factor = {}
    factor['topic'] = 'state'
    factor['lhs'] = ['entities', 'Bully', 'state', 'power']
    dist = Distribution()
    dist[agents['Victim'].getAllBeliefs()['state'].items()[0][0][bPowerKey]] = 1
    factor['value'] = dist
    factor['relation'] = '='
    msg = Message({'factors':[factor]})
    receives = []
    overhears = []
    receives.append('Teacher')
    
    #do the whole tamale
    tamale = agents['Teacher'].calculateMessageConsistency(msg)

    print 
    print "The victim decides to send a message to the teacher indicating that the bully's power is actually %f" % agents['Victim'].getAllBeliefs()['state'].items()[0][0][bPowerKey]

    print 
    print "The teacher's full state of the world (the teacher's beliefs at t=0) before the victim was picked on is the following:"
    print "\tMemory:"
    print "\t\t--> %s: %f" % (bPowerKey,agents['Teacher'].memory[0]['previousBeliefs']['state'].items()[0][0][bPowerKey])
    print "\t\t--> %s: %f" % (vPowerKey,agents['Teacher'].memory[0]['previousBeliefs']['state'].items()[0][0][vPowerKey])
    print "\tCurrent Beliefs:"
    print "\t\t--> %s: %f" % (bPowerKey,agents['Teacher'].getAllBeliefs()['state'].items()[0][0][bPowerKey])
    print "\t\t--> %s: %f" % (vPowerKey,agents['Teacher'].getAllBeliefs()['state'].items()[0][0][vPowerKey])
    print "\tCurrent Memory Consistency:"
    print "\t\t--> %f" % tamale['currentConsistency']

    print
    print "If the teacher were to accept the message, the teacher would adjust its memory of the state to the following:"
    print "\tProposed Memory:"
    print "\t\t--> %s: %f" % (bPowerKey,tamale['proposedMemory'][0]['previousBeliefs']['state'].items()[0][0][bPowerKey])
    print "\t\t--> %s: %f" % (vPowerKey,tamale['proposedMemory'][0]['previousBeliefs']['state'].items()[0][0][vPowerKey])
    print "\tProposed Beliefs:"
    print "\t\t--> %s: %f" % (bPowerKey,tamale['proposedBeliefState'].items()[0][0][bPowerKey])
    print "\t\t--> %s: %f" % (vPowerKey,tamale['proposedBeliefState'].items()[0][0][vPowerKey])
    print "\tProposed Consistency:"
    print "\t\t--> %f" % tamale['proposedConsistency']

