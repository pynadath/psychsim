import string
import sys
import re
import os

#from ELECTClasses import *
from teamwork.math.probability import Distribution
from teamwork.reward.goal import maxGoal,minGoal
from teamwork.agent.AgentClasses import classHierarchy
from teamwork.dynamics.pwlDynamics import *
from teamwork.multiagent.GenericSociety import GenericSociety
from transfer import *




## TODO make accept temporal, make it undesirable to assume
## actions will be taken, 




### File format
### the file starts off by listing all the agents
### each agent a name, a superclass, state values (wealth, health, norm) and
### goal weights. Goal weights have the form relation,wealth,securtiy,norm
### where relation can be self or any defined relation - so an agent can have
### the goal of increasing its own or the norm of its community, etc.
### Every agent is defined as a class whose name is the name of the agent.
### Some of these agents will be astract in the sense that they are abstract
### groups that won't act
### Here is what the AGENT line will look like:
#AGENT,Farid,PoliceChief,STATE,3,5,6,GOALWEIGHTS,self,.2,.3,.4,religion,,,
#AGENT,alhimaya,Community,STATE,3,5,6,GOALWEIGHTS,self,.2,.3,.4
#AGENT,shiite,Religion,STATE,3,5,6,GOALWEIGHTS,self,.2,.3,.4

### After all the agents are defined, there will be the relations between 
### agents. If Farid's community is alhimaya and religion is shiite:
#RELATIONS Farid,community,alhimaya,religion,shiite


### Next comes a line that identifies which agent is the negotiator
#NEGOTIATOR Farid


### Finally come the actions. Each action is defined as who can take
### the action, whether the agent can offer, request or threaten to do the
### action, the action itself and dynamics. As above, the dynamics is
### is represented as zero or more 4-tuples of the form
### relation,wealth,health,norm. Note each action must result in multiple
### changes in the agent models, it has to be listed as one of the agent's
### actions, the ability to offer or request the action during negotiation must
### be listed and finally the dynamics of the action as well as the dynamics
### of its offer/request/threat. Finally a offered or requested state
### feature for that action must be added

#ACTION,Farid,offer,US,Police cooperation,actor,,-4,1,community,-2,-3,
#ACTION,Farid,request,US,Help fixing the market problem,actor,,,2,community,,,
#ACTION,Farid,threat,US,Refuse police coordination with U.S. efforts,actor,,,-2,community,,-1,,


typepat = re.compile(r"""^(?P<linetype>[^,]*),(?P<rest>.*$)""",re.VERBOSE)
namepat = re.compile(r"""^(?P<name>[^,]*),(?P<rest>.*$)""",re.VERBOSE)
relargs = re.compile(r"""^(?P<type>[^,]*),(?P<arg>[^,]*),(?P<rest>.*$)""",re.VERBOSE)

# AGENT pattern
agtpat = re.compile(r"""
(?P<name>[a-zA-Z]*),
(?P<type>[a-zA-Z]*),
(STATE),
(?P<pleasure>[.0-9]*),
(?P<health>[.0-9]*),
(?P<dummy>[.0-9]*),
(GOALWEIGHTS),
(?P<rest>.*$)""",
		    re.VERBOSE)

# ACTION pattern
actpat = re.compile(r"""
(?P<name>[a-zA-Z]*),
(?P<type>[a-zA-Z]*),
(?P<recipient>[a-zA-Z]*),
(?P<group>[^,]*),
(?P<act>[^,]*),
(?P<rest>.*$)""",
		    re.VERBOSE)
# ACTOR WEIGHTS pattern
actorpat = re.compile(r"""
(actor),
(?P<pleasure>[-.0-9]*),
(?P<health>[-.0-9]*),
(?P<dummy>[-.0-9]*)""",
		    re.VERBOSE)

# OBJECT WEIGHTS pattern
objectpat = re.compile(r"""
(object),
(?P<pleasure>[-.0-9]*),
(?P<health>[-.0-9]*),
(?P<dummy>[-.0-9]*)""",
		    re.VERBOSE)

# Weight and dynamics pattern
weightpat = re.compile(r"""
(?P<entity>[a-zA-Z]+),
(?P<pleasure>[-.0-9]*),
(?P<health>[-.0-9]*),
(?P<dummy>[-.0-9]*),
(?P<rest>.*$)""",
		       re.VERBOSE)

numpat = re.compile(r"""
                    (?P<sign>[-]*)
                    (?P<rest>.*$)""",
                    re.VERBOSE)

negpat = re.compile(r"""
(?P<entity>[a-zA-Z]+),
(?P<selfwt>[.0-9]*),
(?P<otherwt>[.0-9]*)""",
		    re.VERBOSE)

belpat = re.compile(r"""
(?P<name>[a-zA-Z]*),
(?P<other>[a-zA-Z]*),
(GOALWEIGHTS),
(?P<pleasure>[.0-9]*),
(?P<health>[.0-9]*),
(?P<dummy>[.0-9]*),
(?P<SNS>[.0-9]*),
(?P<ONS>[.0-9]*)""",
		    re.VERBOSE)

#allActType = {}
beliefs = {}
actionGroups = {}
class elect_reader:
    """
    @cvar aggregateDelivery: If C{True}, there is only one binary decision about whether to follow through or renege on promised offers.  If C{False}, the agent makes decisions about each individual offer.
    @type aggregateDelivery: bool
    @cvar deliverAction: the label of the action type corresponding to the binary decision to follow through on offers
    @type deliverAction: str
    @cvar costbenefit: If C{True}, costs and benefits are tracked separately, rather than being aggregate along the one C{negSatisfaction} dimension
    @type costbenefit: bool
    """
##    agents ={}
##    statefeaturelst = {}
##    actionlst = {}
##    tmpdyn = {}
##    dynlst = {}
##    data = None
    deliverAction = 'deliver on offers'
    aggregateDelivery = True
    costbenefit = False
    
    def __init__(self, input_file="testinput_short.txt"):
        fp = open(input_file,"r")
        ##fp = open(sys.argv[1],"r")
        self.data = fp.readlines()
        fp.close()

        self.agents =[]
        self.statefeaturelst = {}
        self.actionlst = {}
        self.requestlst = {}
        self.pairactlst = {}
        self.tmpdyn = {}
        self.dynlst = {}

    def process_lines(self):
        for line in self.data:
            ## do not process enpty lines
            line = string.strip(line)
            if len(line) == 0:
                continue
            
            ## do not process header lines
            if string.find(line,'COMMENT')>-1:
                continue
            
            ## strip out extra characters
            line = string.lstrip(line,',')
            line = string.rstrip(line, '\n')
            if string.find(line,'ACTION')==-1:
                line = string.rstrip(line, ',')
            if string.find(line,'AGENT')>-1:
                line = line+','
            linetype = typepat.search(line)

        ### Process AGENT LINE
        ### NOTE THIS SHOULD REALLY BE DONE WITH FCN CALLS
        ### AS OPPOSED TO RE-BUILDING THE CLASSHIERACHY DICTIONARY
            if linetype.group('linetype') == 'AGENT':
                self.buildAgent(linetype.group('rest'))
                
        ### PROCESS RELATION LINES
            elif linetype.group('linetype') == 'RELATIONS':
                self.buildRelation(linetype.group('rest'))
                
        #### PROCESS NEGOTIATOR LINES
            elif linetype.group('linetype') == 'NEGOTIATOR':
                self.buildNegotiator(linetype.group('rest'))
                
        ### PROCESS ACTIONS
            elif linetype.group('linetype') == 'ACTION':
                self.buildAction(linetype.group('rest'))
                
            elif linetype.group('linetype') == 'BELIEF':
                self.buildBelief(linetype.group('rest'))    

        #define static dynamics
        for entity in classHierarchy.keys():
            self.buildStaticActions(entity)

        # Identify non-negotiators
        for agent in self.statefeaturelst.keys():
            if not self.requestlst.has_key(agent):
                classHierarchy[agent]['depth'] = 0

#######     NEXT we need to add state features collected in 
#######    statefeaturelst
#######           to the agent's state
        self.add_stateFeatures()
        self.update_action_rel_dyn()
        

## mei set default feature value to 0
    def add_stateFeatures(self):
        for agent,featureList in self.statefeaturelst.items():
            for statefeature in featureList:
                if self.pairactlst.has_key(agent) and statefeature in self.pairactlst[agent]:
                    classHierarchy[agent.strip()]['state'][statefeature]=1.0
		else:
		    classHierarchy[agent.strip()]['state'][statefeature]=0

    def buildBelief(self,belief_def):
        m = belpat.match(belief_def)
        if not beliefs.has_key(m.group('name')):
            beliefs[m.group('name')] = {}
        if not beliefs[m.group('name')].has_key(m.group('other')):
            beliefs[m.group('name')][m.group('other')]={}
            
        for goal in ["pleasure","health","dummy","SNS","ONS"]:
            weight = m.group(goal)
            if len(weight)>0:
                weight = float(weight)
                beliefs[m.group('name')][m.group('other')][goal] = weight
            

    def buildAgent(self,agent_def):
        m = agtpat.match(agent_def)
        self.agents.append(m.group('name'))
        self.statefeaturelst[m.group('name')]=[]
        self.actionlst[m.group('name')]=[]

        rest = m.group('rest')
        goals = Distribution()
        while len(rest) > 0: ## what we want to do here?
            gw = weightpat.match(rest)
            rest = gw.group('rest')

# Construct the agent's goals
            
            for statekey in ['pleasure', 'health', 'dummy']:
                num = numpat.search(gw.group(statekey))
                if num.group('rest') != '':
                    key = StateKey({'entity': gw.group('entity'),
                                    'feature':statekey})
                    if num.group('sign') == '-':
                        goal = minGoal(key)
                    else:
                        goal = maxGoal(key)
                    goals[goal] = float(num.group('rest'))
        # add goal of obey norm
        #goals.append({
        #                'entity':[gw.group('entity')],
        #                'direction':'max',
        #                'type':'state',
        #                'key':'norm',
        #                'weight':4})
        
        # Create the agent
        name = m.group('name').strip()
        classHierarchy[name] = {
            'parent':['Entity'],
            'depth':3,
            'state':{'pleasure':float(m.group('pleasure')),
                     'health':float(m.group('health')),
                     'dummy':float(m.group('dummy')),
                     'negSatisfaction':0.0,
                     },
            'goals':goals}
        if self.costbenefit:
            classHierarchy[name]['state']['benefit'] = 0.0
            classHierarchy[name]['state']['cost'] = 0.0

# Construct relationships

    def buildRelation(self,relation_def):
        rel = {}
        m = namepat.match(relation_def)
        rest = m.group('rest')
        while len(rest) > 0:
            try:
                ra = relargs.match(rest)
                rest = ra.group('rest')
                rel[ra.group('type')] = [ra.group('arg')]
            except AttributeError:
                ## hopefully only 2 items left
                rel_type, rel_arg =  string.split(rest,',')
                rel[rel_type] = [rel_arg]
                break
        tmpdict = classHierarchy[m.group('name').strip()]
        if tmpdict.has_key('relationships'):
            tmpdict['relationships'].append(rel)
        else:
            tmpdict['relationships'] = rel
        classHierarchy[m.group('name').strip()] = tmpdict

        

# Create generic Negotiation goals, dynamics, lookahead horizon, etc
# for any agent identified as a negotiator

    def buildNegotiator(self,Negotiator_def):
        negmat = negpat.match(Negotiator_def)
        m = negmat.group('entity').strip()
	self.requestlst[m] =  []
        tmpdict = classHierarchy[m]
        # Add negotiation goal
        goal = maxGoal(StateKey({'entity':'negotiateWith',
                                 'feature':'negSatisfaction'}))
	classHierarchy[m]['goals'][goal] = float(negmat.group('otherwt'))
        goal = maxGoal(StateKey({'entity':'self',
                                 'feature':'negSatisfaction'}))
	classHierarchy[m]['goals'][goal] = float(negmat.group('selfwt'))
        # add negotiation features to list of state features
        for act in ['accepted','terminated','doNothingTo']:
            self.statefeaturelst[m].append(act)
        # add accept and reject negotiaton actions            
        for act in ['accept','reject','doNothingTo']:
            self.actionlst[m].append(act)
        # give a agent a long lookahead        
        tmpdict['horizon'] = 6

        try:
            tmpdyn = tmpdict['dynamics']
        except KeyError:
            tmpdyn = tmpdict['dynamics'] = {}
        # make (negotiation) terminated feature dependent on both parties
        # accepting or either party rejecting
        tmpdyn['terminated'] =\
          {'accept':{'class':PWLDynamics,
                     'args':negotiationStatus2('terminated','accepted')},
           'reject':{'class':PWLDynamics,
                     'args':setTo('self','terminated',1.0)},
            'deliver on offers':{'class':PWLDynamics,
                     'args':setTo('self','terminated',1.0)},
           }
        # make agent's accepted dependent on accepting action
        tmpdyn['accepted'] =\
          {'accept':{'class':PWLDynamics,
                     'args':setTo('actor','accepted',1.0)},
           }
        # make agent's accepted dependent on accepting action
        tmpdyn['doNothingTo'] =\
          {'doNothingTo':{'class':PWLDynamics,
                     'args':setTo('actor','doNothingTo',1.0)},
           }
        # Delivering on offers pays off promise of negotiation satisfaction
        assert not tmpdyn.has_key('negSatisfaction')
        key = StateKey({'entity':'self','feature':'negSatisfaction'})
        # The following multiplies negotiation satisfaction by 1.5
        #matrix = ScaleMatrix('negSatisfaction',key,0.5)
        #args = {'tree':ProbabilityTree(matrix)}
        #tmpdyn['negSatisfaction'] = {self.deliverAction:{'class':PWLDynamics,
                                                         #'args':args}}

# negotiation dynamics
# move to the end after all the actions have been processed


    def buildStaticActions(self,entity):
        if classHierarchy[entity]['dynamics'].has_key('negSatisfaction'):
            classHierarchy[entity]['dynamics']['negSatisfaction']['reject'] = {'class':PWLDynamics,'args':setToConstant('negSatisfaction',-1)}
        if self.costbenefit and \
               classHierarchy[entity]['dynamics'].has_key('cost'):
            classHierarchy[entity]['dynamics']['cost']['reject'] = {'class':PWLDynamics,'args':setToConstant('cost',0.0)}

        if self.costbenefit and \
               classHierarchy[entity]['dynamics'].has_key('benefit'):
            classHierarchy[entity]['dynamics']['benefit']['reject'] = {'class':PWLDynamics,'args':setToConstant('benefit',-0.01)}

# Now we buld the specific actions and action dynamics for the actions in this
# negotiation
    def buildAction(self,action_def):
        """we build the specific actions and action dynamics for the
        actions in this negotiation"""
        m = actpat.match(action_def)
        rest = m.group('rest')

        negotfeat = m.group('type') +'-' + m.group('act')
        
        if not m.group('type') == 'threat':
            actionGroups[negotfeat]= m.group('group')
            self.statefeaturelst[m.group('name')].append(negotfeat)

        # Grab (or create) the relevant dynamics dictionaries
        tmpdict = classHierarchy[m.group('name')]
        tmpdyn = tmpdict['dynamics']
        try:
            tmpnegsat = tmpdyn['negSatisfaction']
        except KeyError:
            tmpnegsat = {}
        tmpobjdict = classHierarchy[m.group('recipient')]
        tmpobjdyn = tmpobjdict['dynamics']
        if tmpobjdyn.has_key('negSatisfaction'):
            tmpobjnegsat = tmpobjdyn['negSatisfaction']
        else:
            tmpobjnegsat = {}
            
        self.actionlst[m.group('name')].append(negotfeat)
        if m.group('type') == 'offer':
            if self.aggregateDelivery:
                # Add the aggregate follow up over all offers
                if not self.deliverAction in self.actionlst[m.group('name')]:
                    self.actionlst[m.group('name')].append(self.deliverAction)
            else:
                # Add the individual follow up to this offer
                self.actionlst[m.group('name')].append(m.group('act'))
            dmat = actorpat.search(rest)
            #Mei: this feasure should consider goal weight!
            actorcost = 0
            for statekey in ['pleasure', 'health', 'dummy']:
                if dmat.group(statekey) != '':
                    delta = float(dmat.group(statekey))
                    actorcost = actorcost + delta/2.0
                    if self.aggregateDelivery:
                        # Adjust state dynamics when delivering on this offer
                        self.deliverDynamics(m.group('name'),statekey,
                                             m.group('act'),m.group('name'),
                                             delta)
            dmat = objectpat.search(rest)
            objectcost = 0
            for statekey in ['pleasure', 'health', 'dummy']:
                if dmat.group(statekey) != '':
                    delta = float(dmat.group(statekey))
                    objectcost = objectcost + delta/2.0
                    if self.aggregateDelivery:
                        # Adjust state dynamics when delivering on this offer
                        self.deliverDynamics(m.group('recipient'),statekey,
                                             m.group('act'),m.group('name'),
                                             delta)
                        
        # mei added actor cost for request 12/05/08
        if m.group('type') == 'request':
            #mei use objectpat because the actor is requesting
            dmat = objectpat.search(rest)
            #Mei: this feasure should consider goal weight!
            actorcost = 0
            for statekey in ['pleasure', 'health', 'dummy']:
                if dmat.group(statekey) != '':
                    delta = float(dmat.group(statekey))
                    actorcost = actorcost + delta/2.0
                    if self.aggregateDelivery:
                        # Adjust state dynamics when delivering on this offer
                        self.deliverDynamics(m.group('name'),statekey,
                                             m.group('act'),m.group('name'),
                                             delta)
            #mei use actorpat because the object will deliver the act
            dmat = actorpat.search(rest)
            objectcost = 0
            for statekey in ['pleasure', 'health', 'dummy']:
                if dmat.group(statekey) != '':
                    delta = float(dmat.group(statekey))
                    objectcost = objectcost + delta/2.0
                    if self.aggregateDelivery:
                        # Adjust state dynamics when delivering on this offer
                        self.deliverDynamics(m.group('recipient'),statekey,
                                             m.group('act'),m.group('name'),
                                             delta)
            
######## FIRST the NEGOTIATION DYNAMICS
        if m.group('type') == 'offer' or m.group('type') == 'request':
            if m.group('type') == 'offer':
               otherfeat = 'request' + '-' +m.group('act')
            else:
               otherfeat = 'offer' +'-' + m.group('act')

            self.statefeaturelst[m.group('recipient')].append(otherfeat)
### state feature to keep track of what is on the table
            tmpdyn[negotfeat] =\
                {negotfeat:{
                    'class':PWLDynamics,
                    'args':setTo('actor',negotfeat,1.0)},
###  Remove offers and requests of action when negotiation terminated
		 'reject':{'class':PWLDynamics,
			   'args':setTo('self',negotfeat,0.0)},
                 ###  Remove offers and requests when negotiation is accepted???
                 # how will the agent know which act to deliver?
                 #'accept':symmetricSet(negotfeat,0.,['actor','object'],['accepted'],[])['tree'],
                 'accept':{'class':PWLDynamics,
			   'args':setTo('actor',negotfeat,0.0)},
                 }
            
            
######## Now finish off negotiation satisfaction

# if newly offered and previously requested then requestee should be happy
# if newly requested and previously offered then requestee should be happy
        # 12/05/08 consider 'request' as well, both request and offer affect self NS
        if m.group('type') in ['offer','request']: 
            veryhigh = 0.1
            high = 1.00
            low = 1.50
            verylow = 2.50
            # mei 11/17/08 if newly offered and previously requested then requestee should be happy
            row = ThresholdRow(keys=[{'entity':'object','feature':otherfeat}])
            IncTree = ProbabilityTree(IncrementMatrix('negSatisfaction',keyConstant,.1))
            objTree = createBranchTree(KeyedPlane(row,0.5),identityTree('negSatisfaction'),IncTree)
            # original code
            row = ThresholdRow(keys=[{'entity':'actor','feature':'negSatisfaction'}])
            veryHighIncTree = ProbabilityTree(IncrementMatrix('negSatisfaction',keyConstant,actorcost*veryhigh))
            highIncTree = ProbabilityTree(IncrementMatrix('negSatisfaction',keyConstant,actorcost*high))
            highTree = createBranchTree(KeyedPlane(row,.5),highIncTree,veryHighIncTree)
            lowIncTree = ProbabilityTree(IncrementMatrix('negSatisfaction',keyConstant,actorcost*low))
            lowTree = createBranchTree(KeyedPlane(row,0.25),lowIncTree,highTree)
            veryLowIncTree = ProbabilityTree(IncrementMatrix('negSatisfaction',keyConstant,actorcost*verylow))
            incTree = createBranchTree(KeyedPlane(row,0.0),veryLowIncTree,lowTree)
            identityPlane = makeIdentityPlane('actor')
            tree = createBranchTree(identityPlane,objTree,incTree)
            tmpnegsat[negotfeat] = {'class':PWLDynamics, 'args':{'tree':tree}}
            
            #print m, negotfeat,actorcost
            #print tmpnegsat[negotfeat]
            #print 

### if negot. terminated or negotiation move has already been done, decrement
##### object's negotsatisfaction
### if corresponding move has been taken increment by actorcost
### otherwise increment objectcost/10.0

### suggest we modify 5/14/07
### the actorcost lines are fine but need the nonlinear dynamics

# 11/17/08 commented out, otherwise if actor and object can both offer the same item, obj's dynamics will be overwriten
            #row = ThresholdRow(keys=[{'entity':'object','feature':'negSatisfaction'}])
            #veryHighIncTree = ProbabilityTree(IncrementMatrix('negSatisfaction',keyConstant,objectcost*veryhigh))
            #highIncTree = ProbabilityTree(IncrementMatrix('negSatisfaction',keyConstant,objectcost*high))
            #highTree = createBranchTree(KeyedPlane(row,.5),highIncTree,veryHighIncTree)
            #lowIncTree = ProbabilityTree(IncrementMatrix('negSatisfaction',keyConstant,objectcost*low))
            #lowTree = createBranchTree(KeyedPlane(row,.25),lowIncTree,highTree)
            #veryLowIncTree = ProbabilityTree(IncrementMatrix('negSatisfaction',keyConstant,objectcost*verylow))
            #incTree = createBranchTree(KeyedPlane(row,0.0),veryLowIncTree,lowTree)
            #identityPlane = makeIdentityPlane('object')
            #tree = createBranchTree(identityPlane,identityTree('negSatisfaction'),incTree)
            #tmpobjnegsat[negotfeat] = {'class':PWLDynamics,'args':{'tree':tree}}
            
            
            
            
            if self.costbenefit:
                #We need to do the EXACT same thing for benefit and cost - for the actor it's a cost, and for the object it's a benefit
                #well almost the exact same thing - we need to invert the actorcost
                cost = actorcost * -1
                if not tmpdyn.has_key('cost'):
                    tmpdyn['cost'] = {}
                tmpcost = tmpdyn['cost']
                row = ThresholdRow(keys=[{'entity':'actor','feature':'cost'}])
                veryHighIncTree = ProbabilityTree(IncrementMatrix('cost',keyConstant,cost*veryhigh))
                highIncTree = ProbabilityTree(IncrementMatrix('cost',keyConstant,cost*high))
                highTree = createBranchTree(KeyedPlane(row,.5),highIncTree,veryHighIncTree)
                lowIncTree = ProbabilityTree(IncrementMatrix('cost',keyConstant,cost*low))
                lowTree = createBranchTree(KeyedPlane(row,0.25),lowIncTree,highTree)
                veryLowIncTree = ProbabilityTree(IncrementMatrix('cost',keyConstant,cost*verylow))
                incTree = createBranchTree(KeyedPlane(row,0.0),veryLowIncTree,lowTree)
                identityPlane = makeIdentityPlane('actor')
                tree = createBranchTree(identityPlane,identityTree('cost'),incTree)
                tmpcost[negotfeat] = {'class':PWLDynamics, 'args':{'tree':tree}}

                if not tmpobjdyn.has_key('benefit'):
                    tmpobjdyn['benefit'] = {}
                tmpobjbenefit = tmpobjdyn['benefit']
                row = ThresholdRow(keys=[{'entity':'object','feature':'benefit'}])
                veryHighIncTree = ProbabilityTree(IncrementMatrix('benefit',keyConstant,objectcost*veryhigh))
                highIncTree = ProbabilityTree(IncrementMatrix('benefit',keyConstant,objectcost*high))
                highTree = createBranchTree(KeyedPlane(row,.5),highIncTree,veryHighIncTree)
                lowIncTree = ProbabilityTree(IncrementMatrix('benefit',keyConstant,objectcost*low))
                lowTree = createBranchTree(KeyedPlane(row,.25),lowIncTree,highTree)
                veryLowIncTree = ProbabilityTree(IncrementMatrix('benefit',keyConstant,objectcost*verylow))
                incTree = createBranchTree(KeyedPlane(row,0.0),veryLowIncTree,lowTree)
                identityPlane = makeIdentityPlane('object')
                tree = createBranchTree(identityPlane,identityTree('benefit'),incTree)
                tmpobjbenefit[negotfeat] = {'class':PWLDynamics, 'args':{'tree':tree}}


## unSet unpaired flag when a pairing occus
	   
#            if not self.pairactlst.has_key(m.group('name')):
#                self.pairactlst[m.group('name')] =[]
#
#            unpairact = 'unpaired-%s' % (m.group('act'))
#            self.pairactlst[m.group('name')].append(unpairact)
#            self.statefeaturelst[m.group('name')].append(unpairact)
#                
#	    if not tmpdyn.has_key(unpairact):
#		tmpdyn[unpairact]={}
#
#	    tmpdyn[unpairact][negotfeat] =\
#		{'class':PWLDynamics,
#		 'args':conditionalPairedSet(unpairact,0.0,otherfeat)}
#	    tmpdyn[unpairact][otherfeat] =\
#		{'class':PWLDynamics,
#		 'args':conditionalPairedSet(unpairact,0.0,negotfeat)}

        elif m.group('type') == 'threat':
            tmpobjnegsat['threat-'+m.group('act')]= \
                                               {'class':PWLDynamics,
                                                 'args':increment('negSatisfaction',-.5)}
                                               

        tmpdyn['negSatisfaction'] = tmpnegsat
        #tmpdict['dynamics'] = tmpdyn
        #classHierarchy[m.group('name')] = tmpdict
        #
        tmpobjdyn['negSatisfaction'] = tmpobjnegsat
        #tmpobjdict['dynamics'] = tmpobjdyn
        #classHierarchy[m.group('recipient')] = tmpobjdict
        
#######     PROBLEM: ALL ACTIONS ARE FOR THE CURRENT RECIPIENT!!!
#######           NEXT we need to add actions collected in 
#######	          actionlst
#######           to the agents list of actions
        newvals = []
        entity = m.group('name')
        for i in self.actionlst[m.group('name')]:
            newvals.append({'type':'literal','value':i})
            


        act = {'type':'XOR',
                'key':'object',
                'values':[{'type':'generic','value':m.group('recipient')}],
                 'base': {'type':'XOR',
                         'key':'type',
                         'values':newvals,
                         },
                 }

        tmpdict['actions'] = act
#         classHierarchy[m.group('name')] = tmpdict
            
##### NOW we have to do action dynamics - we do this for a generic entity
##### SO HERE WE JUST COLLECT THE DYNAMICS AND THEN AT THE END WE UPDATE
##### THE GENERIC ENTITY MODEL
            
        self.dynlst['pleasure'] = []
        self.dynlst['health'] = []
        self.dynlst['dummy'] = []
    
        while len(rest) > 0:
            gw = weightpat.match(rest)
            if gw == None:
                gw = weightpat.match(rest+',')
            if gw == None:
                gw = weightpat.match(rest+',,')
            if gw == None:
                gw = weightpat.match(rest+',,,')
            if gw == None:
                print rest
            rest = gw.group('rest')
            for statekey in ['pleasure', 'health', 'dummy']:
              if gw.group(statekey) != '':
                  dyn = {}
                  dyn['relationship'] = gw.group('entity')
                  dyn['value'] = float(gw.group(statekey))
                  self.dynlst[statekey].append(copy.copy(dyn))
                 
# UPDATE GENERIC ENTITY MODEL TO INCLUDE ALL THE BASIC ACTION DYNAMICS
# we add the same dynamics to all entities
        for other in classHierarchy.keys():
            entdict = classHierarchy[other]
            try:
                entdyn = entdict['dynamics']
            except KeyError:
                entdyn = entdict['dynamics'] = {}
        #    for statekey in ['pleasure', 'health', 'dummy']:
        #        try:
        #            featdyn = entdyn[statekey]
        #        except KeyError:
        #            featdyn = entdyn[statekey] = {}
        #        if len(self.dynlst[statekey])>0:
        #            if m.group('type') == 'offer' and \
        #                   not self.aggregateDelivery:
        #                # Modified 8/16/06 so action before termination is penalized
        #                args = modelIncDecK({'entity':'actor',
        #                                     'feature':'terminated'},
        #                                    statekey, self.dynlst[statekey],
        #                                    'negSatisfaction', -.1)
        #                # 11/17/08 Mei Si comment: the folloowing sentence will not take effect because m.group('act') is not an action for the agent
        #                #featdyn[m.group('act')] = {'class':PWLDynamics,
        #                #                           'args':args}
        #                featdyn[self.deliverAction] = {'class':PWLDynamics,
        #                                           'args':args}
        #            elif m.group('type') == 'threat':
        #                args = modelIncK(None,statekey, self.dynlst[statekey])
        #                label = 'threat-'+m.group('act')
        #                featdyn[label] = {'class':PWLDynamics,'args':args}

    def deliverDynamics(self,agent,feature,action,actor,delta):
        """
        Update the dynamics of delivering on offers to account for an individual offer possibility
        @param agent: the agent whose dynamics are being updated
        @type agent: str
        @param feature: the state feature being updated (e.g., pleasure, dummy, health)
        @type feature: str
        @param action: the type of offer
        @type action: str
        @param actor: the name of the agent making the offer
        @type actor: str
        @param delta: the amount to change the state value by
        @type delta: float
        """
        key = StateKey({'entity':'self','feature':feature})
        table = classHierarchy[agent]['dynamics']
        vector = None
        try:
            # Access current dynamics
            dynamics = table[feature][self.deliverAction]
            tree = dynamics['args']['tree']
            while not tree.isLeaf():
                if len(tree.split) == 1:
                    # (is probably always True)
                    plane = tree.split[0]
                    if isinstance(plane.weights,ClassRow) and \
                       plane.weights.specialKeys[0]['value'] == actor:
                        # Here's the branch testing on the desired actor
                        vector = tree.getValue()[1].getValue()[key]
                        break
                tree = tree.getValue()[0]
        except KeyError:
            # Create initial (identity) dynamics
            try: 
                table[feature][self.deliverAction] = {}
            except KeyError:
                table[feature] = {self.deliverAction:{}}
            dynamics = table[feature][self.deliverAction]
            dynamics['class'] = PWLDynamics
            tree = ProbabilityTree(KeyedMatrix())
            tree.getValue()[key] = UnchangedRow(sourceKey=key)
            dynamics['args'] = {'tree':tree}
        if vector is None:
            # We found the end of the tree without any branch for this actor
            weights = ClassRow(keys=[{'entity':'actor','value':actor}])
            plane = KeyedPlane(weights,0.5)
            new = ProbabilityTree(KeyedMatrix())
            tree.branch(plane,copy.deepcopy(tree.getValue()),new)
            vector = KeyedVector({key:1.})
            new.getValue()[key] = vector
        # Check the flag for this offer
        key = StateKey({'entity':'actor','feature':'offer-%s' % (action)})
        vector[key] = delta
        
        # 11/17/08 mei added: deliver action befor object accepted will decrease negSatisfaction
        #row = ThresholdRow(keys=[{'entity':'object','feature':'accepted'}])
        #IncTree = ProbabilityTree(IncrementMatrix('negSatisfaction',keyConstant,-.5))
        #IncTree2 = ProbabilityTree(IncrementMatrix('negSatisfaction',keyConstant,.1))
        #tree1 = createBranchTree(KeyedPlane(row,.5),IncTree,IncTree2)
        #tree2 = createBranchTree(KeyedPlane(row,.5),identityTree('negSatisfaction'),IncTree2)
        #identityPlane = makeIdentityPlane('object')
        #tree = createBranchTree(identityPlane,tree2,tree1)
        #table['negSatisfaction'][self.deliverAction] = {'class':PWLDynamics,'args':{'tree':tree}}       

    def update_action_rel_dyn(self):
        for entity in classHierarchy.keys():
            if classHierarchy[entity].has_key('dynamics'):
                tmpdyn = classHierarchy[entity]['dynamics']
                if tmpdyn.has_key('negSatisfaction'):
                    tmpnegsat = tmpdyn['negSatisfaction']
                else:
                    tmpnegsat = {}
            else:
                tmpdyn = {}
                tmpnegsat = {}
            
            if not entity == "Entity":
                #row = ThresholdRow(keys=[{'entity':'object','feature':'accepted'}])
                #IncTree = ProbabilityTree(IncrementMatrix('norm',keyConstant,-.5))
                #tree1 = createBranchTree(KeyedPlane(row,0.5),IncTree,identityTree('norm'))
                #identityPlane = makeIdentityPlane('actor')
                #tree = createBranchTree(identityPlane,identityTree('norm'),tree1)
                #tmpdyn['norm'][self.deliverAction] = {'class':PWLDynamics,'args':{'tree':tree}}               
                
                #tree2 = createBranchTree(KeyedPlane(row,0.5),identityTree('norm'),IncTree)
                #for act in allActType[entity]:
                #    if act.find('request') ==0 or act.find('offer')==0:
                #        row = ThresholdRow(keys=[{'entity':'self','feature':act}])
                #        tree4 = createBranchTree(KeyedPlane(row,0.5),tree2,IncTree)
                #        tree3 = createBranchTree(identityPlane,identityTree('norm'),tree4)
                #        tmpdyn['norm'][act] = {'class':PWLDynamics,'args':{'tree':tree3}}
        
                # any new offer or request overwrite previous offer or request
                # Mei added for Safe
                allnegotfeat = []
                for key in tmpdyn:
                    if key.find('request')==0 or key.find('offer')==0:
                        allnegotfeat.append(key)
                for negotfeat in allnegotfeat:
                    for key in tmpdyn:
                        if key.find('request')==0 or key.find('offer')==0:
                            if not key == negotfeat:
                                if actionGroups[key] == actionGroups[negotfeat]:
                                    tmpdyn[key][negotfeat]={
                                        'class':PWLDynamics,
                                        'args':setTo('actor',key,0.0)}
                            else:
                                tmpdyn[key][negotfeat]={
                                    'class':PWLDynamics,
                                    'args':setTo('actor',key,1.0)}
                    tmpdyn['accepted'][negotfeat] = {
                            'class':PWLDynamics,
                            'args':setTo('actor','accepted',0.0)}
                    
                
                ## define accept/reject and norn
                #tree1 = None
                #row = ThresholdRow(keys=[{'entity':'object','feature':'accepted'}])
                #treeAccepted = createBranchTree(KeyedPlane(row,0.5),IncTree,identityTree('norm'))
                #for negotfeat in allnegotfeat:
                #    if negotfeat.find('offer')==0:
                #        row = ThresholdRow(keys=[{'entity':'object','feature':negotfeat}])
                #        if tree1 == None:
                #            # if the last negotfeat is also not true, apply penalty
                #            tree1 = createBranchTree(KeyedPlane(row,0.5),treeAccepted,identityTree('norm'))
                #        else:
                #            tree1 = createBranchTree(KeyedPlane(row,0.5),tree1,identityTree('norm'))
                #        
                #row = ThresholdRow(keys=[{'entity':'self','feature':'terminated'}])
                #tree1 = createBranchTree(KeyedPlane(row,0.5),tree1,IncTree)
                #identityPlane = makeIdentityPlane('actor')
                #tree = createBranchTree(identityPlane,identityTree('norm'),tree1)
                #tmpdyn['norm']['accept'] = {'class':PWLDynamics,'args':{'tree':tree}}
                #tmpdyn['norm']['reject'] = {'class':PWLDynamics,'args':{'tree':tree}}   
                
# negSatisfaction (negotiation satisfaction) decreases for the object of an
# accept action if negotiation is already terminated or if there are no 
# negotiations pairs otherwise negSatisfaction increases if the object
# of the accept had previous accepted

# collect all unpaired-action features
            if classHierarchy[entity].has_key('relationships'):
                if classHierarchy[entity]['relationships'].has_key('negotiateWith'):

                    #build nonselect list for negSatisfaction
                    nonselect = []

                    if self.pairactlst.has_key(entity):
                        for feature in self.pairactlst[entity]:
                            statekey = StateKey({'entity':'self',
                                                'feature':feature})
                            nonselect.append(statekey)
                    
# modified 08/16 so multiple accepts are penalized
# if terminated or already accepted by actor then decrement objects negsat.
# if there are no paired actions then decrement objects negsat
# otherwise increment objects negsat if object has accepted

# suggest we comment out 5/14/07
#                         
                    #tmpnegsat['accept']={'class':PWLDynamics,
                    #                     'args':decInc2('object','negSatisfaction',.1,-1.0,
                    #                                    [StateKey({'entity':'object',
                    #                                               'feature':'accepted'})],
                    #                                    [StateKey({'entity':'self',
                    #                                               'feature':'terminated'}),
                    #                                     StateKey({'entity':'actor',
                    #                                               'feature':'accepted'})],
                    #                                    copy.deepcopy(nonselect))
                    #                     }
                    tmpnegsat['accept']={'class':PWLDynamics,
                                         'args':increment('negSatisfaction',amount=.001)
                                         #'args':{'tree':ProbabilityTree(IncrementMatrix('negSatisfaction',keyConstant,.001))}
                                         }
                    
            # negSatisfaction (negotiation satisfaction) decreases for the object and actor
            # of a reject action
#  suggest we comment out 5/14/07 - assume lookahead will handle
                    #tmpnegsat['reject']={'class':PWLDynamics,
                    #                     'args':negotReject('negSatisfaction',copy.deepcopy(nonselect))}
                                       
                    tmpnegsat['reject']={'class':PWLDynamics,
                                         'args':increment('negSatisfaction',amount=-.5)
                                         #'args':{'tree':ProbabilityTree(IncrementMatrix('negSatisfaction',keyConstant,-.5))}
                                         }
## set a penalty for not living up to bargain
## perhaps should get milder penalty if you do-nothing during negotiation
##
## if terminated and there are outsanding commitments then decrease object's negotsat by -0.1
## if not terminated then decrease object's negotsat by -0.01
# suggest we comment out 5/14/07
                    tmpnegsat['doNothingTo']=\
                        {'class':PWLDynamics,
                         'args':andOrInc('object','negSatisfaction',-0.1,-0.01,0.0,
                                         [StateKey({'entity':'self',
                                                    'feature':'accepted'})],
                                         self.requestlst[entity])}
                    
            tmpdyn['negSatisfaction'] = tmpnegsat
            classHierarchy[entity]['dynamics']=tmpdyn
            


# FINALLY INSTANTIATE MODELS AND SET NAMES TO BE NAMES OF CLASS
# SO FOR EXAMPLE THE CLASS Farid IS INSTANTIATED AS AN AGENT OF TYPE
# Farid WITH NAME Farid

if __name__ == "__main__":
    import sys
    try:
        er = elect_reader(sys.argv[1])
    except IndexError:
        er = elect_reader()

    er.process_lines()



    society = GenericSociety()
    society.importDict(classHierarchy)

    for agent in society.members():
        space = agent.actions
        if len(space.getOptions()) == 0:
            # Only agents with no beliefs have no actions
            assert(len(agent.getEntities()) == 0)
        
    xmlDoc = society.__xml__()
    fp = open('ELECTClasses_gen.xml',"w")
    fp.write(xmlDoc.toxml())
    fp.close()
