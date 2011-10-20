## branching tree doesn't work
## specified .8, .6
## resulted in .36 .64
## dyn with branch couldn't be fitted, assert domain() ==1

import string
import sys
import random


from teamwork.shell.PsychShell import *
from teamwork.utils.PsychUtils import *

from teamwork.math.Keys import *
from teamwork.math.probability import *

from ThespianAgent import *
from ThespianAgents import *
from ThespianUtils import *
from appraisalDimentions import *

## use CVXOPT
from cvxopt.base import matrix
from cvxopt.blas import dot 
from cvxopt.solvers import qp

from teamwork.math.probability import Distribution
from teamwork.math.Keys import StateKey,ConstantKey
    
useAppraisalModule = False

##partial order of actions
orders = []
## action should happen only after 10 steps
laterThan = {}
## at step 20, action should already happened
earlierThan = {}

orders = [['wolf-eat-granny','anybody-kill-wolf'],
            ['red-give-cake-granny','wolf-eat-red'],
            ['red-give-cake-granny','wolf-eat-granny'],
            ]

earlierThan = {50:['wolf-eat-red'],80:['wolf-eat-granny']}
earlierThan2 = [('wolf-eat-granny',30,['anybody-kill-wolf'])]
NOearlierThan = {60:['wolf-eat-red']}
laterThan2 = [('wolf-eat-red',10,'wolf-eat-granny')]


def progress(msg,pct):
    if pct > 0.:
        print 'done.'
    elif len(msg) > 0:
        print msg,'...'


class ThespianShell(PsychShell):
    """Shell subclass enhanced for stories."""

    agentClass = ThespianAgent ##this is the module
    multiagentClass = ThespianAgents

    
    entityList={\
##                '3':[('granny','granny'),('hunter','hunter'),('wolf','wolf'),('red','red'),('Entity','fairy')],
                '3':[('granny','granny'),('hunter','hunter'),('wolf','wolf'),('red','red'),('woodcutter','woodcutter')],
##                '3':[('wolf','wolf'),('hunter','hunter')],
##                '3':[('wolf','wolf'),('red','red'),('granny','granny')],
              #'3':[('hunter','hunter'),('wolf','wolf'),('red','red')],
              '31':[('red','red'),('wolf','wolf')],
                    '4':[('usr','usr'),('cha','cha')],
                    '6':[('usr','usr'),('labrat','labrat1'),('labrat','labrat2'),('streetrat','streetrat'),('otherTeam','otherTeam'),('timer','timer')],
##                    '6':[('usr','usr'),('labrat','labrat1'),('labrat','labrat2'),('streetrat','streetrat'),],
#                '6':[('usr','usr'),('labrat','labrat1')],
                '7':[('usr','usr'),('vc','vc')],
                }
     
    # Uncomment the following to support the undo command
##    __UNDO__ = 1
    
    def __init__(self,entities=None,classes=None,scene='3',debug=10):
        
        self.scene = scene
        
        self.loadClasses()
        PsychShell.__init__(self,None,self.classes,self.agentClass,self.multiagentClass,debug=0)
        scenario = self.setupEntities(self.createEntities(),None,
                                      compileDynamics=True,compilePolicies=None)
        self.setupScenario(scenario)
      
        #test func for director agent
        self.handlers['director'] = self.director
        self.handlers['path'] = self.printPath
        self.handlers['locations'] = self.printLocation
        self.handlers['log'] = self.printLogFileName
        
        
        self.helpWolf = 0
        self.wolfMetGranny = False
        
        self.AP = appraisal()
        if useAppraisalModule:
            self.AP.initEntities = copy.deepcopy(self.entities)
            self.AP.setupEntities(self.AP.initEntities)
            self.AP.curEntities = copy.deepcopy(self.entities)
            self.AP.setupEntities(self.AP.curEntities )
        
        self.copyEntities = copy.deepcopy(self.entities)
            
        #    for entityName in self.copyEntities:
        #        self.AP.setupDynamics(entities=self.copyEntities,entity=entityName,copyEntities=self.entities)
            
        self.history = []
        
        self.logfile = None
        self.logfileName = None
        
        while self.logfile == None:
            self.logfileName = 'log'+str(int(100*random.random()))+'.txt'
            try:
                open(self.logfileName,'r')
            except:
                print self.logfileName
                self.logfile = open(self.logfileName,'w')
        
        
        

    # mei 06/30/04 change the param to indicate which scene we working on
    def createEntities(self):
        entities=[]
        for newEntity in self.entityList[self.scene]:
            entity = self.classes.instantiate(newEntity[0],newEntity[1],ThespianAgent)
            
            if entity:
                entities.append(entity)
                
        ## turned off temperately because:
        ## couldn't use lookup
        ## will create too manys state features for obligation keys
##        createObligations(entities,1, 0)
##        ObligationDyns(entities)
##        SatisfyObliPolicies(entities)
        return entities

    def executeCommand(self,cmd):
        start = time.time()
        result = self.execute(cmd)
        diff = time.time()-start
        if result:
            self.displayResult(cmd,`self.debug`)
            self.debug.reset()
            self.displayResult(cmd,result)
            self.displayResult(cmd,'Time: %7.4f' % (diff))
        else:
            self.done = 1
    
    
    def displayResult(self,cmd,result):
        """Terminal version of the output display method.  Uses
        standard output."""
        print result
##        print
        sys.stdout.flush()
    
    
    def printPath(self,result=[]):
        for act in self.history:
            #if not isinstance(act,Message):
            #    continue
            print `act`
    
    
    def printLocation(self,result=[]):
        print 'locations of characters'
        for entity in self.entities:
            tmp = self.entities.__getitem__(entity).getState('location').expectation()
            print entity,tmp,' ',
            
    def printLogFileName(self,result=[]):
        print self.logfileName
    
    def runAppraisal(self, action,lookahead = 1):
        if useAppraisalModule == False:
            return
        try:
            self.AP.lookaheadTest()
        except:
            lookahead = 0
        ## calculate appraisal dimentions
        for entity in self.entities:
            print entity
            for i in range(lookahead+1):
                print 'lookahead level ',i
                print '     novelty: ',self.AP.novelty(entity,action,i)
                preUtility, curUtility = self.AP.calUtilities(entity,action,i)
                relevance = self.AP.Relevance(entity,preUtility, curUtility,i)
                desirability = self.AP.Desirability(entity,preUtility, curUtility,i)
                print '     Relevance:',relevance, '   Desirability:',desirability
                print '     causalAttribution '
                
                if relevance > 0:
                    agents,attr = self.AP.causalAttribution(entity,action,lookahead=i)
                    for i in range(len(agents)):
                        print '     ',agents[i],attr[i]
                
                if relevance > .2 and desirability < 0:
                    print '     self agency', self.AP.Agency(entity,entity, action,i)
                    for other in self.entities:
                        if not other == entity:
                            print '     other agency ', other,'  ',self.AP.Agency(entity,other, action,i)
            print

        self.AP.updateHistory(action)
        print
        print
        
        
    def genObjectives(self, history):
        lastAct = history[len(history)-1]
        objectives = []
        for order in orders:
            check_order_result = self.checkOrder(history,order)
            if check_order_result == -1:
                tmp = order[1]
                tmp = tmp.replace('anybody','')
                tmpAct = `lastAct`
                if  tmpAct.find(tmp)>-1:
                    print 'violate order ',order
                    # we want the first action to happen
                    actor,type,obj = stringToAct(order[0])
                    objectives.append((actor,type,'Maximize',obj))
                    # we want the second action to not happen
                    actor,type,obj = stringToAct(order[1])
                    objectives.append((actor,type,'Minimize',obj))        
                        
        tmpact = `lastAct`
        for key in laterThan:
            tmp = key
            if tmp.find('anybody')>-1:
                tmp = key.replace('anybody','')
            if tmpact.find(tmp)>-1:
                if laterThan[`lastAct`] > len(history):
                    print `lastAct`, ' should happen after ',laterThan[`lastAct`],' steps'
                    objectives.append((lastAct['actor'],lastAct['type'],'Minimize',lastAct['object']))
                    
                         
        for key in earlierThan:
            if len(history) >= key:
                for act in earlierThan[key]:
                    if self.searchPath(history,act) == -1:
                        #if the only constaints are certain actions need to happen in the future, i will let it be?
                        actor,type,obj = stringToAct(act)
                        print act, ' should happen before ',key,' steps'
                        objectives.append((actor,type,'Maximize',obj))
        return objectives
        
    def getLastAct(self,history,changeEntity):
        for act in self.history:
            if isinstance(act,Message):
                continue
            if act['actor'] == changeEntity:
                return act
        

    #def director2(self, result=[]):
    #    receivers = ['woodcutter','hunter','wolf','red','granny']
    #    for i in range(4):
    #        next = self.entities.next()
    #        delta = self.entities.microstep(next,hypothetical=True,explain=False)
    #        for key in delta['decision'].keys():
    #            res = delta['decision'][key][0]
    #            #print res
    #            tmp = copy.copy(self.history)
    #            tmp.append(res)
    #            objectives = self.genObjectives(tmp)
    #            if len(objectives)>0:
    #                options = self.entities.__getitem__(next[0]['name']).actions.getOptions()
    #                options = self.entities.__getitem__(next[0]['name']).updateActionChoices(options,includeLocation = True)
    #                bestAct = options[0] 
    #                minObj = 100
    #                for option in options:
    #                    tmp = copy.copy(self.history)
    #                    tmp.append(option[0])
    #                    obj = self.genObjectives(tmp)
    #                    if obj < minObj:
    #                        minObj = obj
    #                        bestAct = option
    #                next[0]['choices']=[bestAct]
    #                
    #                if minObj>0:
    #                    newMsg = self.change_characters_state(next[0]['name'],delta['decision'],objectives)
    #                    messages = []
    #                    for msg in newMsg:
    #                        if not msg in messages:
    #                            messages.append(msg)
    #                    
    #                    factor = {}
    #                    factor['topic'] = 'state'
    #                    factor['relation'] = '='
    #                    for msg in messages:
    #                        if msg[1] in ['being-enquired']:        
    #                            factor['lhs'] = ['entities', msg[0], 'state', msg[1]]
    #                            factor['value'] = msg[2]
    #                            self.entities.__getitem__(msg[0]).setState(msg[1],factor['value'])
    #                            msg = Message({'factors':[factor]})                            
    #                            print msg
    #                            self.history.append(copy.deepcopy(msg))   
    #                            self.entities.performMsg(msg,'granny',receivers,[],self.debug)
    #                        else:
    #                            res, act = self.make_story_false(msg[0],msg[1],msg[2],self.entities,self.history,next[0]['name'])
    #                            if res:
    #                                next[0]['choices']=[act]
    #                            else:
    #                                nextLocation = self.entities.__getitem__(next[0]['name']).getState('location').expectation()
    #                                msgLocation = self.entities.__getitem__(msg[0]).getState('location').expectation()
    #                                if not nextLocation == msgLocation:
    #                                    factor['lhs'] = ['entities', next[0]['name'], 'state', 'location']
    #                                    factor['value'] = msgLocation
    #                                    msg1 = Message({'factors':[factor]})
    #                                    self.entities.performMsg(msg1,'granny',receivers,[],self.debug)
    #                                    res, act = self.make_story_false(msg[0],msg[1],msg[2],self.entities,self.history,next[0]['name'])
    #                                    if res:
    #                                        next[0]['choices']=[act]
    #                                        print msg1
    #                                        self.logfile.write(str(msg1))
    #                                        self.logfile.write('\n')
    #                                        self.history.append(copy.deepcopy(msg1))
    #                                        self.entities.__getitem__(next[0]['name']).setState('location',factor['value'])
    #                                    else:
    #                                        factor['value'] = nextLocation
    #                                        msg1 = Message({'factors':[factor]})
    #                                        self.entities.performMsg(msg1,'granny',receivers,[],self.debug)
    #                                    
    #        
    #            break
    #            
    #        delta = self.entities.microstep(next,hypothetical=False,explain=False)
    #        for key in delta['decision'].keys():
    #            res = delta['decision'][key][0]
    #            self.history.append(res)
    #            print res
    #            self.logfile.write(str(res))
    #            self.logfile.write('\n')
    #            
    #            
    #            
    #             
            
            
    def director2(self, result=[]):        
        lookaheadstep = 10
        acturalLookaheadSteps = 4
        totalTests = 9
        
        receivers = ['woodcutter','hunter','wolf','red','granny']
        changeCharacter = 0
        characters = ['red','woodcutter','granny','hunter','wolf']
        objectives = []
        satObjective = []
        decision = {}

        # moveToCharacter: 0   relacate changeCharacter to the location of targetEntity before targetEntity act
        # moveToCharacter: 1   relacate changeCharacter to the location of targetEntity before changeCharacter act
        # set initial value to 0 because the first test will increase it to 1 while not perform any character realocation
        moveToCharacter = 0
        
        #best result among the test
        bestPath=[]
        minViolation = 100
        
        for testNum in range(totalTests):
            if changeCharacter == 0 and testNum >2:
                break
            print
            print 'test',testNum
            
            entities = copy.deepcopy(self.entities)
            history = copy.deepcopy(self.history)
            wolfMetGranny = self.wolfMetGranny 
            actions = []
            nochange = True
            moveToCharacter = (moveToCharacter+1)%2
            moveOnce = True
            
            
            if len(objectives)>0:
                messages = []
                testMessages = []
                
                for cha in characters:
                    newMsg = self.change_characters_state(cha,decision,objectives)
                    for msg in newMsg:
                        if not msg in messages:
                            messages.append(msg)
                
                for msg in messages:
                    if not msg[1] in ['being-enquired']:
                        testMessages.append(msg)
                        continue
                    factor = {}
                    factor['topic'] = 'state'
                    factor['relation'] = '='
                    factor['lhs'] = ['entities', msg[0], 'state', msg[1]]
                    factor['value'] = msg[2]
                    entities.__getitem__(msg[0]).setState(msg[1],factor['value'])
                    msg = Message({'factors':[factor]})                            
                    print msg
                    actions.append(copy.deepcopy(msg))
                    history.append(copy.deepcopy(msg))   
                    entities.performMsg(msg,'granny',receivers,[],self.debug)
                    msg = None
                    
            finishedMsg = []
            for i in range(lookaheadstep):
                next = entities.next()
                entity = next[0]['name']
                searchNextAction = False
                
                for tmp in satObjective:
                    try:
                        objectives.remove(tmp)
                    except:
                        pass
                satObjective = []
                
                if len(objectives)>0:
                    searchNextAction = True
                    # try fit characters' actions first
                    for objective in objectives:
                        tmpAct =objective[0]+'-'+objective[1]+'-'+objective[3]
                        if self.searchPath(history,tmpAct) > -1:
                            continue
                        if (not entity == 'wolf') and (entity == objective[0] or (objective[0] == 'anybody' and not entity == objective[3])):
                            actorLocation = entities.__getitem__(entity).getState('location').expectation()
                            objectLocation = entities.__getitem__(objective[3]).getState('location').expectation()
                            if not actorLocation == objectLocation:
                                continue
                            if objective[2] == 'Maximize':
                                actNext = Action({'actor':entity,'type':objective[1],'object':objective[3]})
                                options = entities.__getitem__(entity).actions.getOptions()
                                options = entities.__getitem__(entity).updateActionChoices(options,includeLocation = True)
                                if [actNext] in options:
                                    searchNextAction = False
                                    # don't need to fit since we don't care about character motivation
                                    next[0]['choices'] = [[actNext]]
                                    # take care of the 1st objective only
                                    break
                            elif objective[2] == 'Minimize':
                                options = entities.__getitem__(entity).actions.getOptions()
                                options = entities.__getitem__(entity).updateActionChoices(options,includeLocation = True)
                                
                                for option in options:
                                    if not option[0]['type'] == objective[1]:
                                        searchNextAction = False
                                        # don't need to fit since we don't care about character motivation
                                        next[0]['choices'] = [option]
                                        # take care of the 1st objective only
                                        break    
                                        
                    
                    if searchNextAction:
                        #only move one chanracter once during each lookahead
                        reLocate = False
                        if moveOnce:
                            objectEntity = objectives[0][0]
                            # change the location of one character at a time
                            changeEntity = characters[changeCharacter]
                            
                            # idnore characters whose locations can't be changed
                            if entities.__getitem__(changeEntity).getState('eaten').expectation() >.5:
                                changeCharacter = (changeCharacter+1)%len(characters)
                                changeEntity = characters[changeCharacter]
                                
                            # anybody-kill-wolf -> hunter-kill-wolf ->move hunter's location
                            if objectEntity == 'anybody':
                                objectEntity = changeEntity
                            #the character is within the sight of wolf, i can't make it disppear
                            if entities.__getitem__(changeEntity).getState('location').expectation() == entities.__getitem__('wolf').getState('location').expectation():
                                wolfLastAct = self.getLastAct(history,'wolf')
                                changeEntityLastAct = self.getLastAct(history,changeEntity)
                                # I can change their locations if the wolf just moved or the current chracter just moved
                                if not (`wolfLastAct`.find('move') >-1 or not `changeEntityLastAct`.find('move') >-1) :
                                    changeCharacter = (changeCharacter+1)%len(characters)
                                    changeEntity = characters[changeCharacter]
                                
                            reLocate = True
                            if changeEntity == objectEntity:
                                if changeEntity == entity:
                                    moveToCharacter = 1
                                    changeCharacter = (changeCharacter+1)%len(characters)
                                else:
                                    reLocate = False
                            elif moveToCharacter == 0:
                                if not objectEntity == entity:
                                    reLocate = False
                            elif moveToCharacter == 1:
                                if not changeEntity == entity:
                                    reLocate = False
                                else:
                                    changeCharacter = (changeCharacter+1)%len(characters)
                            else:
                                reLocate = False
                        
                        if reLocate:
                            moveOnce = False
                            changeEntityLocation = entities.__getitem__(changeEntity).getState('location').expectation()
                            if changeEntity == objectEntity:
                                #change my location to affect my own behavior
                                # e.g. hunter kills wolf
                                objobj = objectives[0][3]
                                objectEntityLocation = entities.__getitem__(objobj).getState('location').expectation()
                            else:
                                #change my location to affect other characters' behaviors
                                #e.g.woodcutter move to wolf
                                objectEntityLocation = entities.__getitem__(objectEntity).getState('location').expectation()
                            
                            
                            #if not (objectEntityLocation == 0.25 and changeEntity == 'granny'):
                            if changeEntity == 'granny':
                                if objectEntityLocation == 0.25 or wolfMetGranny == True:
                                    # we won't move the character and will abonden this test
                                    continue
                                
                            factor = {}
                            factor['topic'] = 'state'
                            factor['relation'] = '='
                            factor['lhs'] = ['entities', changeEntity, 'state', 'location']
                            if objectEntityLocation == changeEntityLocation:
                                #granny moves away from Red to prevent cake being delivered too soon
                                factor['value'] = objectEntityLocation -.2
                            else:
                                factor['value'] = objectEntityLocation   
                            msg = Message({'factors':[factor]})                                            
                            print msg
                            actions.append(copy.deepcopy(msg)) 
                            history.append(copy.deepcopy(msg)) 
                            entities.performMsg(msg,'granny',receivers,[],self.debug)
                            entities.__getitem__(changeEntity).setState('location',factor['value'])
                            
                            finishedMsg = []
                            for msg in testMessages:
                                if self.make_story_false(msg[0],msg[1],msg[2],entities,history,next[0]['name']):
                                    factor = {}
                                    factor['topic'] = 'state'
                                    factor['relation'] = '='
                                    factor['lhs'] = ['entities', msg[0], 'state', msg[1]]
                                    factor['value'] = msg[2]
                                    entities.__getitem__(msg[0]).setState(msg[1],factor['value'])
                                    msg1 = Message({'factors':[factor]})                            
                                    print msg1
                                    actions.append(copy.deepcopy(msg1)) 
                                    history.append(copy.deepcopy(msg1))   
                                    entities.performMsg(msg1,'granny',receivers,[],self.debug)
                                    finishedMsg.append(msg)
                            for tmp in finishedMsg:
                                testMessages.remove(tmp)
                    
                            for objective in objectives:
                                tmpAct =objective[0]+'-'+objective[1]+'-'+objective[3]
                                if self.searchPath(history,tmpAct) > -1:
                                    continue
                                if (not entity == 'wolf') and (entity == objective[0] or (objective[0] == 'anybody' and not entity == objective[3])):
                                    actorLocation = entities.__getitem__(entity).getState('location').expectation()
                                    objectLocation = entities.__getitem__(objective[3]).getState('location').expectation()
                                    if not actorLocation == objectLocation:
                                        continue
                                    if objective[2] == 'Maximize':
                                        actNext = Action({'actor':entity,'type':objective[1],'object':objective[3]})
                                        options = entities.__getitem__(entity).actions.getOptions()
                                        options = entities.__getitem__(entity).updateActionChoices(options,includeLocation = True)
                                        if [actNext] in options:
                                            searchNextAction = False
                                            next[0]['choices'] = [[actNext]]
                                                # take care of the 1st objective only
                                            break
                                        
                                    elif objective[2] == 'Minimize':
                                        options = entities.__getitem__(entity).actions.getOptions()
                                        options = entities.__getitem__(entity).updateActionChoices(options,includeLocation = True)
                                        
                                        for option in options:
                                            if not option[0]['type'] == objective[1]:
                                                searchNextAction = False
                                                next[0]['choices'] = [option]
                                                    # take care of the 1st objective only
                                                break
                                                
                                if searchNextAction == False:
                                    break
                                
                delta = entities.microstep(next,hypothetical=False,explain=False)
                for key in delta['decision'].keys():
                    res = delta['decision'][key][0]
                    print `res`
                    actions.append(res)
                    history.append(res)
                    if not decision.has_key(key):
                        decision[key]=delta['decision'][key]
                
                if abs(entities.__getitem__('wolf').getState('location').expectation()-entities.__getitem__('granny').getState('location').expectation())<=.2\
                and entities.__getitem__('wolf').getState('know-granny').expectation()>.5:
                    wolfMetGranny = True
                    
            tmpHistory = copy.deepcopy(self.history)
            objectives = []
            
            # test simulation results
            actionCount = -1
            for i in range(len(actions)):
                tmpHistory.append(actions[i])
                
                # don't consider messages when testing
                if isinstance(actions[i],Message):
                    continue
                
                actionCount = actionCount+1
                
                # lookahead 15 steps, but only use the first 5 steps for these two check
                # the rest are for lookahead to see if certain event will happen
                if actionCount <= acturalLookaheadSteps:
                #if i < lookaheadstep:
                    for order in orders:
                        check_order_result = self.checkOrder(tmpHistory,order)
                        if check_order_result == -1:
                            tmp = order[1]
                            tmp = tmp.replace('anybody','')
                            tmpAct = `actions[i]`
                            if  tmpAct.find(tmp)>-1:
                                nochange = False
                                print 'violate order ',order
                                # we want the first action to happen
                                actor,type,obj = stringToAct(order[0])
                                objectives.append((actor,type,'Maximize',obj))
                                # we want the second action to not happen
                                actor,type,obj = stringToAct(order[1])
                                objectives.append((actor,type,'Minimize',obj))        
                                
                    tmpact = `actions[i]`
                    for key in laterThan:
                        tmp = key
                        if tmp.find('anybody')>-1:
                            tmp = key.replace('anybody','')
                        if tmpact.find(tmp)>-1:
                            if laterThan[`actions[i]`] > len(tmpHistory):
                                nochange = False
                                print `actions[i]`, ' should happen after ',laterThan[`actions[i]`],' steps'
                                objectives.append((actions[i]['actor'],actions[i]['type'],'Minimize',actions[i]['object']))
                            
                        
                # only add the constraints once    
                if i == len(actions)-1:                   
                    for key in earlierThan:
                        if len(history) >= key:
                            for act in earlierThan[key]:
                                if self.searchPath(tmpHistory,act) == -1:
                                    for key in NOearlierThan:
                                        if not act in NOearlierThan[key]:    
                                            actor,type,obj = stringToAct(act)
                                            print act, ' should happen before ',key,' steps'
                                            objectives.append((actor,type,'Maximize',obj))
                
                 
            if len(objectives)-len(finishedMsg)< minViolation:
                minViolation = len(objectives)
                bestPath=[]
                bestPath=copy.deepcopy(actions)
                
            if nochange and len(objectives) == 0:       
                break
            
        
        print
        print 'real steps'
        resolvedE = []
        resolvedL = []
        i = 0
        for desired in bestPath:
            if i < acturalLookaheadSteps:
                print desired
                self.logfile.write(str(desired))
                self.logfile.write('\n')
                self.history.append(desired)
                if isinstance(desired,Message):
                    self.entities.performMsg(desired,'granny',receivers,[],self.debug)
                    self.entities.__getitem__(desired['factors'][0]['lhs'][1]).setState(desired['factors'][0]['lhs'][3],desired['factors'][0]['value'])
                else:
                    self.entities.microstep([{'name':desired['actor'],'choices':[[desired]]}],hypothetical=False,explain=False)
                    i = i+1
                    for unresolved in earlierThan2:
                        if unresolved[0] == `desired`:
                            resolvedE.append(unresolved)
                            earlierThan[len(self.history)+unresolved[1]] = unresolved[2]
                    for unresolved in laterThan2:
                        if unresolved[0] == `desired`:
                            resolvedL.append(unresolved)
                            laterThan[unresolved[2]] = len(self.history)+unresolved[1]
                        
            if i == acturalLookaheadSteps and isinstance(desired,Message):
                print desired
                self.logfile.write(str(desired))
                self.logfile.write('\n')
                self.history.append(desired)
                self.entities.performMsg(desired,'granny',receivers,[],self.debug)
                self.entities.__getitem__(desired['factors'][0]['lhs'][1]).setState(desired['factors'][0]['lhs'][3],desired['factors'][0]['value'])
            
            if abs(self.entities.__getitem__('wolf').getState('location').expectation()-self.entities.__getitem__('granny').getState('location').expectation())<=.2\
                and self.entities.__getitem__('wolf').getState('know-granny').expectation()>.5:
                    self.wolfMetGranny = True
            
            if i == acturalLookaheadSteps and isinstance(desired,Message):
                break
            
        for tmp in resolvedE:
            earlierThan2.remove(tmp)
        for tmp in resolvedL:
            laterThan2.remove(tmp)







    def director(self, result=[]):        
        lookaheadstep = 10
        acturalLookaheadSteps = 4
        totalTests = 9
        
        receivers = ['woodcutter','hunter','wolf','red','granny']
        changeCharacter = 0
        characters = ['red','woodcutter','granny','hunter']
        objectives = []
        satObjective = []
        decision = {}

        # moveToCharacter: 0   relacate changeCharacter to the location of targetEntity before targetEntity act
        # moveToCharacter: 1   relacate changeCharacter to the location of targetEntity before changeCharacter act
        # set initial value to 0 because the first test will increase it to 1 while not perform any character realocation
        moveToCharacter = 0
        
        #best result among the test
        bestPath=[]
        minViolation = 100
        
        for testNum in range(totalTests):
            if changeCharacter == 0 and testNum >2:
                break
            
            print
            print 'test',testNum
            
            entities = copy.deepcopy(self.entities)
            history = copy.deepcopy(self.history)
            wolfMetGranny = self.wolfMetGranny 
            actions = []
            nochange = True
            moveToCharacter = (moveToCharacter+1)%2
            moveOnce = True
            
            
            if len(objectives)>0:
                messages = []
                testMessages = []
                
                for cha in characters:
                    newMsg = self.change_characters_state(cha,decision,objectives)
                    for msg in newMsg:
                        if not msg in messages:
                            messages.append(msg)
                
                for msg in messages:
                    if not msg[1] in ['being-enquired']:
                        testMessages.append(msg)
                        continue
                    factor = {}
                    factor['topic'] = 'state'
                    factor['relation'] = '='
                    factor['lhs'] = ['entities', msg[0], 'state', msg[1]]
                    factor['value'] = msg[2]
                    entities.__getitem__(msg[0]).setState(msg[1],factor['value'])
                    msg = Message({'factors':[factor]})                            
                    print msg
                    actions.append(copy.deepcopy(msg))
                    history.append(copy.deepcopy(msg))   
                    entities.performMsg(msg,'granny',receivers,[],self.debug)
                    msg = None
                    
            finishedMsg = []
            for i in range(lookaheadstep):
                next = entities.next()
                entity = next[0]['name']
                searchNextAction = False
                
                for tmp in satObjective:
                    try:
                        objectives.remove(tmp)
                    except:
                        pass
                satObjective = []
                
                if len(objectives)>0:
                    searchNextAction = True
                    # try fit characters' actions first
                    for objective in objectives:
                        tmpAct =objective[0]+'-'+objective[1]+'-'+objective[3]
                        if self.searchPath(history,tmpAct) > -1:
                            continue
                        if (not entity == 'wolf') and (entity == objective[0] or (objective[0] == 'anybody' and not entity == objective[3])):
                            actorLocation = entities.__getitem__(entity).getState('location').expectation()
                            objectLocation = entities.__getitem__(objective[3]).getState('location').expectation()
                            if not actorLocation == objectLocation:
                                continue
                            if objective[2] == 'Maximize':
                                actNext = Action({'actor':entity,'type':objective[1],'object':objective[3]})
                                options = entities.__getitem__(entity).actions.getOptions()
                                options = entities.__getitem__(entity).updateActionChoices(options,includeLocation = True)
                                if [actNext] in options:
                                    fitPath = history+[actNext]
                                    newGoals = self.easyFit(entity, fitPath)
                                    if newGoals:
                                        print 'fit succeed ',fitPath
                                        searchNextAction = False
                                        satObjective.append(objective)
                                        entities.__getitem__(entity).setGoals(newGoals)
                                        next[0]['choices'] = [[actNext]]
                                        # take care of the 1st objective only
                                        break
                            elif objective[2] == 'Minimize':
                                options = entities.__getitem__(entity).actions.getOptions()
                                options = entities.__getitem__(entity).updateActionChoices(options,includeLocation = True)
                                
                                for option in options:
                                    if not option[0]['type'] == objective[1]:
                                        fitPath = history+option
                                        newGoals = self.easyFit(entity, fitPath)
                                        if newGoals:
                                            print 'fit succeed ',fitPath
                                            searchNextAction = False
                                            satObjective.append(objective)
                                            entities.__getitem__(entity).setGoals(newGoals)
                                            next[0]['choices'] = [option]
                                            # take care of the 1st objective only
                                            break
                                        
                    
                    if searchNextAction:
                        #only move one chanracter once during each lookahead
                        reLocate = False
                        if moveOnce:
                            objectEntity = objectives[0][0]
                            # change the location of one character at a time
                            changeEntity = characters[changeCharacter]
                            
                            # idnore characters whose locations can't be changed
                            if entities.__getitem__(changeEntity).getState('eaten').expectation() >.5:
                                changeCharacter = (changeCharacter+1)%len(characters)
                                changeEntity = characters[changeCharacter]
                            
                            # anybody-kill-wolf -> hunter-kill-wolf ->move hunter's location
                            if objectEntity == 'anybody':
                                objectEntity = changeEntity
                            #the character is within the sight of wolf, i can't make it disppear
                            if entities.__getitem__(changeEntity).getState('location').expectation() == entities.__getitem__('wolf').getState('location').expectation():
                                wolfLastAct = self.getLastAct(history,'wolf')
                                changeEntityLastAct = self.getLastAct(history,changeEntity)
                                # I can change their locations if the wolf just moved or the current chracter just moved
                                if not (`wolfLastAct`.find('move') >-1 or not `changeEntityLastAct`.find('move') >-1) :
                                    changeCharacter = (changeCharacter+1)%len(characters)
                                    changeEntity = characters[changeCharacter]
                                
                            reLocate = True
                            if changeEntity == objectEntity:
                                if changeEntity == entity:
                                    moveToCharacter = 1
                                    changeCharacter = (changeCharacter+1)%len(characters)
                                else:
                                    reLocate = False
                            elif moveToCharacter == 0:
                                if not objectEntity == entity:
                                    reLocate = False
                            elif moveToCharacter == 1:
                                if not changeEntity == entity:
                                    reLocate = False
                                else:
                                    changeCharacter = (changeCharacter+1)%len(characters)
                            else:
                                reLocate = False
                        
                        if reLocate:
                            moveOnce = False
                            changeEntityLocation = entities.__getitem__(changeEntity).getState('location').expectation()
                            if changeEntity == objectEntity:
                                #change my location to affect my own behavior
                                # e.g. hunter kills wolf
                                objobj = objectives[0][3]
                                objectEntityLocation = entities.__getitem__(objobj).getState('location').expectation()
                            else:
                                #change my location to affect other characters' behaviors
                                #e.g.woodcutter move to wolf
                                objectEntityLocation = entities.__getitem__(objectEntity).getState('location').expectation()
                            
                            
                            #if not (objectEntityLocation == 0.25 and changeEntity == 'granny'):
                            if changeEntity == 'granny':
                                if objectEntityLocation == 0.25 or wolfMetGranny == True:
                                    # we won't move the character and will abonden this test
                                    continue
                                
                            factor = {}
                            factor['topic'] = 'state'
                            factor['relation'] = '='
                            factor['lhs'] = ['entities', changeEntity, 'state', 'location']
                            if abs(objectEntityLocation - changeEntityLocation)<.01:
                                #granny moves away from Red to prevent cake being delivered too soon
                                factor['value'] = objectEntityLocation -.2
                            else:
                                factor['value'] = objectEntityLocation   
                            msg = Message({'factors':[factor]})                                            
                            print msg
                            actions.append(copy.deepcopy(msg)) 
                            history.append(copy.deepcopy(msg)) 
                            entities.performMsg(msg,'granny',receivers,[],self.debug)
                            entities.__getitem__(changeEntity).setState('location',factor['value'])
                            
                            finishedMsg = []
                            for msg in testMessages:
                                if self.make_story(msg[0],msg[1],msg[2],entities,history):
                                    factor = {}
                                    factor['topic'] = 'state'
                                    factor['relation'] = '='
                                    factor['lhs'] = ['entities', msg[0], 'state', msg[1]]
                                    factor['value'] = msg[2]
                                    entities.__getitem__(msg[0]).setState(msg[1],factor['value'])
                                    msg1 = Message({'factors':[factor]})                            
                                    print msg1
                                    actions.append(copy.deepcopy(msg1)) 
                                    history.append(copy.deepcopy(msg1))   
                                    entities.performMsg(msg1,'granny',receivers,[],self.debug)
                                    finishedMsg.append(msg)
                            for tmp in finishedMsg:
                                testMessages.remove(tmp)
                    
                            for objective in objectives:
                                tmpAct =objective[0]+'-'+objective[1]+'-'+objective[3]
                                if self.searchPath(history,tmpAct) > -1:
                                    continue
                                if (not entity == 'wolf') and (entity == objective[0] or (objective[0] == 'anybody' and not entity == objective[3])):
                                    actorLocation = entities.__getitem__(entity).getState('location').expectation()
                                    objectLocation = entities.__getitem__(objective[3]).getState('location').expectation()
                                    if not actorLocation == objectLocation:
                                        continue
                                    if objective[2] == 'Maximize':
                                        actNext = Action({'actor':entity,'type':objective[1],'object':objective[3]})
                                        options = entities.__getitem__(entity).actions.getOptions()
                                        options = entities.__getitem__(entity).updateActionChoices(options,includeLocation = True)
                                        if [actNext] in options:
                                            fitPath = history+[actNext]
                                            newGoals = self.easyFit(entity, fitPath)
                                            if newGoals:
                                                print 'fit succeed ',fitPath
                                                searchNextAction = False
                                                satObjective.append(objective)
                                                entities.__getitem__(entity).setGoals(newGoals)
                                                next[0]['choices'] = [[actNext]]
                                                # take care of the 1st objective only
                                                break
                                        
                                    elif objective[2] == 'Minimize':
                                        options = entities.__getitem__(entity).actions.getOptions()
                                        options = entities.__getitem__(entity).updateActionChoices(options,includeLocation = True)
                                        
                                        for option in options:
                                            if not option[0]['type'] == objective[1]:
                                                fitPath = history+option
                                                #print 'easyFit ',fitPath
                                                newGoals = self.easyFit(entity, fitPath)
                                                if newGoals:
                                                    print 'fit succeed ',fitPath
                                                    searchNextAction = False
                                                    satObjective.append(objective)
                                                    entities.__getitem__(entity).setGoals(newGoals)
                                                    next[0]['choices'] = [option]
                                                    # take care of the 1st objective only
                                                    break
                                                #else:
                                                #    print 'fit failed '
                                if searchNextAction == False:
                                    break
                                
                delta = entities.microstep(next,hypothetical=False,explain=False)
                for key in delta['decision'].keys():
                    res = delta['decision'][key][0]
                    print `res`
                    actions.append(res)
                    history.append(res)
                    if not decision.has_key(key):
                        decision[key]=delta['decision'][key]
                
                if abs(entities.__getitem__('wolf').getState('location').expectation()-entities.__getitem__('granny').getState('location').expectation())<=.2\
                and entities.__getitem__('wolf').getState('know-granny').expectation()>.5:
                    wolfMetGranny = True
                    
            tmpHistory = copy.deepcopy(self.history)
            objectives = []
            
            # test simulation results
            actionCount = -1
            for i in range(len(actions)):
                tmpHistory.append(actions[i])
                
                # don't consider messages when testing
                if isinstance(actions[i],Message):
                    continue
                
                actionCount = actionCount+1
                
                # lookahead 15 steps, but only use the first 5 steps for these two check
                # the rest are for lookahead to see if certain event will happen
                if actionCount <= acturalLookaheadSteps:
                #if i < lookaheadstep:
                    for order in orders:
                        check_order_result = self.checkOrder(tmpHistory,order)
                        if check_order_result == -1:
                            tmp = order[1]
                            tmp = tmp.replace('anybody','')
                            tmpAct = `actions[i]`
                            if  tmpAct.find(tmp)>-1:
                                nochange = False
                                print 'violate order ',order
                                # we want the first action to happen
                                actor,type,obj = stringToAct(order[0])
                                objectives.append((actor,type,'Maximize',obj))
                                # we want the second action to not happen
                                actor,type,obj = stringToAct(order[1])
                                objectives.append((actor,type,'Minimize',obj))        
                                
                    tmpact = `actions[i]`
                    for key in laterThan:
                        tmp = key
                        if tmp.find('anybody')>-1:
                            tmp = key.replace('anybody','')
                        if tmpact.find(tmp)>-1:
                            if laterThan[`actions[i]`] > len(tmpHistory):
                                nochange = False
                                print `actions[i]`, ' should happen after ',laterThan[`actions[i]`],' steps'
                                objectives.append((actions[i]['actor'],actions[i]['type'],'Minimize',actions[i]['object']))
                            
                        
                # only add the constraints once    
                if i == len(actions)-1:                   
                    for key in earlierThan:
                        if len(history) >= key:
                            for act in earlierThan[key]:
                                if self.searchPath(tmpHistory,act) == -1:
                                    for key in NOearlierThan:
                                        if not act in NOearlierThan[key]:    
                                            actor,type,obj = stringToAct(act)
                                            print act, ' should happen before ',key,' steps'
                                            objectives.append((actor,type,'Maximize',obj))
                
                 
            if len(objectives)-len(finishedMsg)< minViolation:
                minViolation = len(objectives)
                bestPath=[]
                bestPath=copy.deepcopy(actions)
                
            if nochange and len(objectives) == 0:       
                break
            
        
        print
        print 'real steps'
        resolvedE = []
        resolvedL = []
        i = 0
        for desired in bestPath:
            if i < acturalLookaheadSteps:
                print desired
                self.logfile.write(str(desired))
                self.logfile.write('\n')
                self.history.append(desired)
                if isinstance(desired,Message):
                    self.entities.performMsg(desired,'granny',receivers,[],self.debug)
                    self.entities.__getitem__(desired['factors'][0]['lhs'][1]).setState(desired['factors'][0]['lhs'][3],desired['factors'][0]['value'])
                else:
                    self.entities.microstep([{'name':desired['actor'],'choices':[[desired]]}],hypothetical=False,explain=False)
                    i = i+1
                    for unresolved in earlierThan2:
                        if unresolved[0] == `desired`:
                            resolvedE.append(unresolved)
                            earlierThan[len(self.history)+unresolved[1]] = unresolved[2]
                    for unresolved in laterThan2:
                        if unresolved[0] == `desired`:
                            resolvedL.append(unresolved)
                            laterThan[unresolved[2]] = len(self.history)+unresolved[1]
                        
            if i == acturalLookaheadSteps and isinstance(desired,Message):
                print desired
                self.logfile.write(str(desired))
                self.logfile.write('\n')
                self.history.append(desired)
                self.entities.performMsg(desired,'granny',receivers,[],self.debug)
                self.entities.__getitem__(desired['factors'][0]['lhs'][1]).setState(desired['factors'][0]['lhs'][3],desired['factors'][0]['value'])
            
            if abs(self.entities.__getitem__('wolf').getState('location').expectation()-self.entities.__getitem__('granny').getState('location').expectation())<=.2\
                and self.entities.__getitem__('wolf').getState('know-granny').expectation()>.5:
                    self.wolfMetGranny = True
            
            if i == acturalLookaheadSteps and isinstance(desired,Message):
                break
            
        for tmp in resolvedE:
            earlierThan2.remove(tmp)
        for tmp in resolvedL:
            laterThan2.remove(tmp)
    
        
        
    def make_story(self,entity, state, target,entities,history):
        curValue = entities.__getitem__(entity).getState(state).expectation()
        diff = target-curValue
        for actor in ['woodcutter','hunter','red','wolf']:
            options = entities.__getitem__(actor).actions.getOptions()
            options = entities.__getitem__(actor).updateActionChoices(options,includeLocation = True)
            for option in options:
                if actor == 'wolf':
                    if not option[0]['type']=='help':
                        continue
                actionDict = {}
                actionDict[actor] = option
                result = entities.hypotheticalAct(actionDict)
                for value,prob in result['state'].items():
                    for key in value:
                        try:
                            if key['entity'] == entity and key['feature']== state:
                                if abs(diff-value[key][keyConstant]) <=.2 :
                                    path = history+option
                                    #print 'make story fit ',path
                                    if self.easyFit(actor,path):
                                        print 'make story',option,entity,state
                                        if option[0]['type']=='help' and actor == 'wolf':
                                            print 'show option for helpping the wolf'
                                            self.helpWolf = 1
                                        return 1
                        except:
                            pass
        return 0
    
    
    def make_story_false(self,entity, state, target,entities,history,actor):
        res = False
        act = None
        curValue = entities.__getitem__(entity).getState(state).expectation()
        diff = target-curValue
        
        options = entities.__getitem__(actor).actions.getOptions()
        options = entities.__getitem__(actor).updateActionChoices(options,includeLocation = True)
        for option in options:
            actionDict = {}
            actionDict[actor] = option
            result = entities.hypotheticalAct(actionDict)
            for value,prob in result['state'].items():
                for key in value:
                    try:
                        if key['entity'] == entity and key['feature']== state:
                            if abs(diff-value[key][keyConstant]) <=.2 :
                                return True,option
                    except:
                        pass
        return 0,act            

                    
    def change_characters_state(self,character,choices,objectives):   
        messages = []
        topics = []
        
        for objective in objectives:
            if character == 'red' and objective[0]=='wolf' and objective[1] == 'eat':
                continue
            if objective[0]=='wolf' and objective[1] == 'enquiry':
                continue
            if character == 'wolf' and not objective[0]=='wolf':
                continue
                    
            #print objective[0],objective[1]
            #replace suggest function
            if (objective[0] in ['red','granny']) and (objective[1] == 'kill'):
                topic = [objective[0]+'power']
                returnRes = [(objective[0],'power',1.0)]
            elif (objective[0] == 'anybody') and (objective[1] == 'kill'):
                topic = []
                returnRes = []
            elif (objective[3] == 'anybody') and (objective[1] == 'eat'):
                topic = []
                returnRes = []
            elif (objective[0] in ['red']) and (objective[1] == 'give-cake')and (objective[2] == 'Minimize'):
                topic = []
                returnRes = []
            elif (objective[0] in ['red']) and (objective[1] == 'give-cake')and (objective[2] == 'Maximize'):
                topic = [objective[0]+'eaten',objective[0]+'has-cake']
                returnRes = [(objective[0],'eaten',0.0),(objective[0],'has-cake',1.0)]
            elif (objective[0] in ['wolf']) and (objective[1] == 'give-cake'):
                topic = [objective[0]+'has-cake']
                returnRes = [(objective[0],'has-cake',1.0)]
            elif (objective[0] in ['wolf']) and (objective[1] == 'eat') and (objective[2] == 'Minimize')and (objective[3] == 'granny'):
                topic = [objective[0]+'know-granny']
                returnRes = [(objective[0],'know-granny',0.0)]
            elif (objective[0] in ['wolf']) and (objective[1] == 'eat') and (objective[2] == 'Minimize')and (objective[3] == 'red'):
                topic = []
                returnRes = []
            elif (not character == 'wolf') and (objective[0] in ['wolf']) and (objective[1] == 'eat') and (objective[2] == 'Maximize')and (objective[3] == 'granny'):
                topic = [objective[0]+'know-granny',character+'being-enquired','wolfSD','wolfhas-cake']
                returnRes = [(objective[0],'know-granny',1.0),(character,'being-enquired',1.0),('wolf','SD',1.0),('wolf','has-cake',1.0)]
            elif (objective[3] == 'wolf') and (objective[1] == 'talkabout-granny') and (objective[2] == 'Maximize'):
                topic = ['wolfSD','wolfhas-cake']
                returnRes = [('wolf','SD',1.0),('wolf','has-cake',1.0)]
            else:  
                res = self.entities.suggest(character,choices[character][0],objective[:3])
                topic,returnRes = self.formMessage(res)
            
            for i in range(len(topic)):
                if topic[i] in topics:
                    continue
                topics.append(topic[i])
                messages.append(returnRes[i])
            
        #print   messages 
        return messages
        
        
        
    def formMessage(self,res):       
        returnRes = []
        topic = []
        for choice in res:
            if choice == {}:
                continue
            for item in choice:
                entity = item['entity']
                state = item['feature']
                
                if state == 'location':
                    continue
                else:
                    content = choice[item]
                    for item1 in content:
                        if item1 == 'max':
                            value = content[item1]
                        #elif item1 == 'min':
                        #    value = -content[item1]+self.entities.__getitem__(entity).getState(state).expectation()
                
                if not entity+state in topic:
                    topic.append(entity+state)
                    returnRes.append((entity,state,value))

        return topic,returnRes
                        
                        
                        
                
    def step(self,length='100',results=[]):
        try:
            length = int(length)
        except TypeError:
            results = length
            length = 1
            
        sequence, res = self._step(length)
        return sequence
    
            
    def _step(self,length=100,results=[]):
        """Steps the simulation the specified number of micro-steps
        into the future (default is 1)"""
        
        sequence = []
        for t in range(length):
            sequence = []
            res=None
##            self.director(result=[])
            self.director2(result=[])
            #nextturn = self.entities.next()
            ##actor = nextturn[0]['name']
            ##entity = self.entities.__getitem__(actor)
            ##print entity.updateActionChoices(entity.actions.getOptions(),entity.getAllBeliefs())
            #
            #delta = self.entities.microstep(turns=nextturn,explain=False, debug=self.debug)
            #
            #if delta['decision']:
            #    for key in delta['decision'].keys():
            #        res = delta['decision'][key][0]
            #        print `res`
            #        sequence.append(delta['decision'][key][0])
            #
            #        # appraisal
            #        self.runAppraisal(res)
            #        self.history.append(res)
                                    
        return sequence, res


    def send(self,sender,receiver,*content):
        print content
        try:
            if receiver == '*':
                # Message sent to all
                receivers = ['wolf','red','hunter','woodcutter','granny']
            else:
                receivers = [receiver]
            if type(content[len(content)-1]) is ListType:
                results = content[len(content)-1]
                msg = string.join(content[:len(content)-1])
            elif type(content[0]) is StringType:
                results = []
                msg = content[0]
            else:
                results = []
                msg = string.join(content)
        except IndexError:
            return 'Usage: message <sender> <receiver> <content>'
        
        msg = Message(msg)
        msg['type'] = '_message'
        
        self.history.append(msg) 

        result = self.entities.performMsg(msg,sender,receivers,[],self.debug)
        
              
        
    def __act__(self,actList,results):
        action = extractAction(actList,self.entities,self.actionFormat,
                               self.debug)
        resolved = []
        for unresolved in earlierThan2:
            if unresolved[0] == `action`:
                resolved.append(unresolved)
                earlierThan[len(self.history)+unresolved[1]] = unresolved[2]
        for tmp in resolved:
            earlierThan2.remove(tmp)
        
        resolved = []
        for unresolved in laterThan2:
            if unresolved[0] == `action`:
                resolved.append(unresolved)
                laterThan[unresolved[2]] = len(self.history)+unresolved[1]
        for tmp in resolved:
            laterThan2.remove(tmp)
            
                
        if action:
            if self.__UNDO__:
                self.lastStep=copy.deepcopy (self.entities)
            return self.doActions(actions={action['actor']:[action]},
                                  detailLevel=0,
                                  results=results)
        else:
            results.append('Usage: act <entity> <type> <obj>')
            return {}

    def doActions(self,actions,detailLevel=10,results=[],entities=None,isRealStep = 1):
        
        """Performs the actions, provided in dictionary form
        @param actions: dictionary of actions to be performed, indexed by actor, e.g.:
           - I{agent1}: [I{act11}, I{act12}, ... ]
           - I{agent2}: [I{act21}, I{act22}, ... ]
           - ...
        @type actions: C{dict:strS{->}L{Action}[]}
        @param detailLevel: the level of detail requested for the explanation, where higher numbers mean more detail.  The default level is 10 (the maximum level of detail)
        @type detailLevel: C{int}
        """
        
        if entities == None:
            entities = self.entities
        
            
        turns = []
        for actor,actList in actions.items():
            turns.append({'name':actor,'choices':[actList]})

        ##appraisal
        #isRealStep = 0
        if isRealStep == 1:
            self.runAppraisal(actList[0])
            self.history.append(actList[0]) 
            
        delta = entities.microstep(turns,hypothetical=False,
                                        explain=False,
                                        debug=self.debug)
        
        return {}


    
    def loadClasses(self):
        if self.scene == '3':
            import RedRidingHoodClasses_director
            self.classes = RedRidingHoodClasses_director.classHierarchy
        
        elif self.scene == '31':
            import RedRidingHoodClasses_test
            self.classes = RedRidingHoodClasses_test.classHierarchy

##            import RedRidingHoodClassesStage
##            self.classes = RedRidingHoodClassesStage.classHierarchy

        elif self.scene == '4':
            import ChatClasses
            self.classes = ChatClasses.classHierarchy
        elif self.scene == '6':
            import RatClasses
            self.classes = RatClasses.classHierarchy
        elif self.scene == '7':
            import UAIClasses
            self.classes = UAIClasses.classHierarchy
        else:
            raise "wrong scene ID"

## mei 07/12/05
        if isinstance(self.classes,GenericSociety):
            pass
        elif isinstance(self.classes,dict):
            society = GenericSociety()
##            society.importDict(self.classes,ThespianGenericModel)
            society.importDict(self.classes)
            self.classes = society


        
    def setScene(self,scene,results=[]):
        self.scene = scene
        ThespianAgents.sceneID = scene
        
        self.loadClasses()

        scenario = self.setupEntities(self.createEntities(),None,
                                      compileDynamics=True,compilePolicies=None)
        self.setupScenario(scenario)

        

    def reSetScene(self,results=[],entities=None,copyEntities=None):
        if entities == None:
            entities = self.entities
        if copyEntities == None:
            copyEntities = self.copyEntities
        entities = copy.deepcopy(copyEntities)
        #for entityName in entities:
        #    self.AP.setupDynamics(entities,entityName,self.copyEntities)
        self.history=[]


    def reSetSceneWithGoals(self,goals={},entities=None,copyEntities=None):
        if entities == None:
            entities = self.entities
        if copyEntities == None:
            copyEntities = self.copyEntities
        self.reSetScene([],entities,copyEntities)
        for entity in entities:
            if goals.has_key(entity):
                entities.__getitem__(entity).setGoals(goals[entity])
        

    
    def getCommand(self):
        """Terminal version of command entry.  Prints a prompt
        (currently assumes turn-based execution) and reads the command
        entry from the input file."""
        if self.phase == 'setup':
            prompt = '?'
        else:
            next = self.entities.next()
            if next[0]['name'] == 'wolf':
                indoor = self.entities.__getitem__('wolf').getState('indoor').expectation()
                wolfLocation = self.entities.__getitem__('wolf').getState('location').expectation()
                        
                print 'wolf SD ',self.entities.__getitem__('wolf').getState('SD').expectation(),' ',
                self.logfile.write('wolf SD '+str(self.entities.__getitem__('wolf').getState('SD').expectation())+' \n')
                print
                
                if not indoor >0.5:
                    print 'characters closeby:  ',
                    self.logfile.write('characters closeby:  ')
                    for entity in self.entities:
                        if entity == 'wolf':
                            continue
                        tmp = self.entities.__getitem__(entity).getState('location').expectation()
                        if abs(tmp-wolfLocation)<=.01:
                            if entity == 'granny':
                                if self.entities.__getitem__('wolf').getState('know-granny').expectation() <.5:
                                    continue
                            if entity in ['granny','red']:
                                if self.entities.__getitem__(entity).getState('eaten').expectation() >.5:
                                    continue
                            print entity,tmp-wolfLocation,' ',
                            self.logfile.write(entity+str(0)+' ')
                            
                            if entity in ['red','granny']:
                                print '(power ',self.entities.__getitem__(entity).getState('power').expectation(),') ',
                                self.logfile.write('(power '+str(self.entities.__getitem__(entity).getState('power').expectation())+') ')
                        #can detect hunter in a distance
                        elif abs(tmp-wolfLocation)<=.2:
                            if entity == 'hunter':
                                print entity,tmp-wolfLocation,' ',
                                self.logfile.write(entity+str(tmp-wolfLocation)+' ')
                                
                print 'available actions'
                self.logfile.write('available actions')
                entity = self.entities.__getitem__(next[0]['name'])
                options = entity.actions.getOptions()
                options = entity.updateActionChoices(options,includeLocation = True)
                for option in options:
                    # unless the wolf already know where granny is, there may randomly appear houses on side of the road for the wolf to enter
                    if option[0]['type'] == 'enter-house':
                        if self.entities.__getitem__('wolf').getState('location').expectation() == self.entities.__getitem__('granny').getState('location').expectation() \
                        and self.entities.__getitem__('wolf').getState('know-granny').expectation() >.5:
                            pass
                        else:
                            continue
                        
                    # only occationally the woodcutter needs help
                    if option[0]['type'] == 'help':
                        # if decided by the director agent to help wolf, show this option
                        if self.helpWolf:
                            pass
                        elif random.random()  < .8:
                            continue
                    
                    if option[0].has_key('object'):
                        if indoor > 0.5:
                            if not option[0]['object'] in ['granny','red']:
                                continue
                            
                    print option
                    self.logfile.write(str(option))
                    self.logfile.write('\n')
                    
                
            prompt = '%s (%d)> ' % (next[0]['name'],
                                    self.entities.time)
        print prompt,
        
        try:
            cmd = string.strip(sys.stdin.readline())
            self.logfile.write(cmd)
            self.logfile.write('\n')
        except KeyboardInterrupt:
            cmd = 'quit'
        return cmd
    
    
## the exclude list contains list of agents whose model WILLNOT be adjusted in this function
    def varyModel(self,actor,exclude=[],models=[],entities=None):
        
        if entities == None:
            entities = self.entities
        
        entity = entities.__getitem__(actor)
        fixedgoals = ['sameLocation','actAlive','resp-norm','specialRule']

        origoals = entity.getGoals()
        adjgoals = copy.deepcopy(origoals)
        removeList = []
        for goal in adjgoals:
            if goal.key in fixedgoals:
                removeList.append(goal)
        for goal in removeList:
            adjgoals.remove(goal)

        adjgoalKeys = []
        for goal in adjgoals:
            adjgoalKeys.append(goal.toKey())

        n = len(adjgoals)
        ## construct the P matrix
        P = matrix (0.0,(n,n),tc = 'd')
        P [::n+1]+=2

        for other in entities:
            if other in exclude:
                continue
            beliefAboutOther = entity.getEntity(other)
            for model in models:
                beliefAboutOther.setModel(model)
                print actor,"'s belief about ",other," is set to ",model
                self.generateAllPosPath(actor,['sameLocation','actAlive','resp-norm','specialRule'],5,
                                        adjgoals=adjgoals, adjgoalKeys=adjgoalKeys, P=P, entities=entities)
                self.reSetScene(entities)
                print
                print

                

    def varyInitialState(self,actor,varyList={},entities=None):
        
        if entities == None:
            entities = self.entities
        
        entity = entities.__getitem__(actor)
        fixedgoals = ['sameLocation','actAlive','resp-norm','specialRule']
        
        origoals = entity.getGoals()
        adjgoals = copy.deepcopy(origoals)
        removeList = []
        for goal in adjgoals:
            if goal.key in fixedgoals:
                removeList.append(goal)
        for goal in removeList:
            adjgoals.remove(goal)

        adjgoalKeys = []
        for goal in adjgoals:
            adjgoalKeys.append(goal.toKey())

        n = len(adjgoals)
        ## construct the P matrix
        P = matrix (0.0,(n,n),tc = 'd')
        P [::n+1]+=2


        for other in varyList:
            state = varyList[other]
            for value in [-1,0,1]:
                entity.setBelief(other,state,value)
                print actor,"'s belief about ",other,"\'s ",state," is set to ",value
                self.generateAllPosPath(actor,['sameLocation','actAlive','resp-norm','specialRule'],5,
                                        adjgoals=adjgoals, adjgoalKeys=adjgoalKeys, P=P, entities=entities)
                self.reSetScene(entities)
                print
                print


    def varyGoal(self,actor,fixedgoals=[],entities=None):
        
        if entities == None:
            entities = self.entities
            
        entity = entities.__getitem__(actor)
        origoals = copy.deepcopy(entity.goals)

        allGoalNames = []
        for goal in origoals:
            allGoalNames.append(goal.key)
        
        ## the goals we will play with
        adjgoals = copy.deepcopy(origoals)
        
        for goal in adjgoals:
            if goal.key in fixedgoals:
                adjgoals.remove(goal)

        for i in range(min(5,len(adjgoals))):
            for value in [-5,5]:
                entity.setGoalWeight(adjgoals[i],value,None)
                for j in range(len(fixedgoals)):
                    for fullGoal in origoals:
                        ## find out the corresponding goal
                        if fixedgoals[j] == fullGoal.key:
                            entity.setGoalWeight(fullGoal,1000,None)
                            break
                entity.normalizeGoals()
                print actor,' goal ',adjgoals[i].name,' weight set to ',value
    ##            self.executeCommand('step 20')
                self.generateAllPosPath(actor,allGoalNames,5,entities)
                self.reSetSceneWithGoals(entities,{actor:copy.deepcopy(origoals)})
                print
                print


    def searchPath(self, path, act):
        index = -1
        
        if not isinstance((path[0]),str):
            newPath = []
            for tmp in path:
                newPath.append(`tmp`)
        else:
            newPath = copy.copy(path)
        
        try:
            index = newPath.index(act)
        except:
            if act.find('anybody')>-1:
                tmp = act.replace('anybody','')
                for tact in newPath:
                    if tact.find(tmp)>-1:
                        return newPath.index(tact)
                
            if act.find('talk')>-1:
                tmp = act.replace('talk','inform')
            try:
                index = newPath.index(tmp)
            except:
                tmp = act.replace('talk','enquiry')
                try:
                    index = newPath.index(tmp)
                except:
                    pass
        return index
                            

    def checkOrder(self,path,order):
        index1 = self.searchPath(path, order[0])
        index2 = self.searchPath(path, order[1])
               
        if index2 > -1 and index2 < index1:
            return -1
        
        if index2 > -1 and index1 == -1:
            return -1
        
        if index2 == -1 and index1 == -1:
            return 0
        
        return 1
    

    def checkComplete(self,path,complete):
        actPath = []
        for action in path:
            if not isinstance(action,Message):
                actPath.append(action)
            
        for act in complete:
            if act in actPath:
                pass
            else:
##                print act,'(',type(act),') is not in ',actList
                return False

        return True
    
        
        
    def FitToPlotPoint(self,storyPath,fixedgoals=[],delta=0,entities=None):
        
        if entities == None:
            entities = self.entities
            
        newStoryPath = copy.copy(storyPath)
##  only loop once for now
        for i in range(0,1):
            for actor in entities.members():
##                print newStoryPath
                name = actor.name
                self.reSetScene(entities)
                res = self.fitSequence(newStoryPath,name,fixedgoals,delta,entities)
                if not res == 1:
                    pathWithGap = self.incrementalFitSequence(newStoryPath,fixedgoals,delta,entities)
                    break
            else:
                print "result" ,newStoryPath
                return True
            
            if len(pathWithGap)>=2:
                islands = [pathWithGap[len(pathWithGap)-2],pathWithGap[len(pathWithGap)-1]]
                actors = [0]*2
                actors [0] = string.split(`islands[0]`,'-')
                actors [0] = actors [0][0]
                actors [1] = string.split(`islands[1]`,'-')
                actors [1] = actors [1][0]
                path = pathWithGap[0:len(pathWithGap)-2]
            else:
                islands = [pathWithGap[0]]
                path = []
                actors = []
                for actor in self.entities.members():
                    actors.append(actor.name)
                
            print 'filling in Gap ',islands
            print 'path is ',path
            res = self.fillGap(fixedgoals,4,path,islands,actors,entities)

            if res == None:
                print 'can not use social normative actions to fill in the gap between: ',islands
                if len(islands) == 1:
                    res = self.findSuggestion(path,islands[0],exclude=[{'feature': 'location', 'entity': 'red'},
                                                                       {'feature': 'alive', 'entity': 'red'}],entities=entities)
                else:
                    res = self.findSuggestion(path+[islands[0]],islands[1],exclude=[
                        {'feature': 'location', 'entity': 'red'},
                        {'feature': 'alive', 'entity': 'red'}],entities=entities)

                if not res == None and len(res)>0:
                    res = self.formMessage(res)
                    print 'suggestion for actor\'s believe change: ',res
                else:
                    print 'can not use msg to actor\'s own beliefs to fill in the gap between: ',islands
                    if len(islands) == 1:
                        res = self.findSuggestion2(path,islands[0],exclude=[{'feature': 'location', 'entity': 'red'},
                                                                       {'feature': 'alive', 'entity': 'red'}],entities=entities)
                    else:
                        res = self.findSuggestion2(path+[islands[0]],islands[1],exclude=[{'feature': 'location', 'entity': 'red'},
                                                                       {'feature': 'alive', 'entity': 'red'}],entities=entities)

                    if not res == None and len(res)>0:
                        res = self.formMessage(res)
                        print 'suggestion for actor\'s believe change: ',res
                    else:
                        print 'cannot fill the gap'
                        
                
            if not res == None:
                index = storyPath.index(islands[0])
                path1 = storyPath[0:index]
                if index+1 > len(storyPath)-1:
                    path2 = []
                else:
                    path2 = storyPath[index+1:len(storyPath)]

                if type(res) ==  list:
                    ## by default, we use the first result
                    res = res[0]
                if isinstance(res,Message):
                    res = [res,storyPath[index]]
                newStoryPath = path1+res+path2
                

        return False            

##{{'feature': 'location', 'entity': 'red'}: {'max': 1.0, 'key': {'feature': 'location', 'entity': 'red'}, 'min': 0.9}, {'feature': 'alive', 'entity': 'red'}: {'max': 1.0, 'key': {'feature': 'alive', 'entity': 'red'}, 'min': 0.001}}
    def searchResult(self,res,exclude):
        if exclude == []:
            return res
        
        for choice in res:
            delList = []
            for msg in choice:
                for key in exclude:
                    if msg == key or msg == {}:
                        delList.append(msg)
            
            for delItem in delList:
                try:
                    del choice[delItem]
                except:
                    print choice

        while 1:
            try:
                res.remove({})
            except:
                break
            
        return res

                
    def findSuggestion(self,path,obj,exclude=[{'feature': 'location', 'entity': 'red'}],entities=None):
        
        if entities == None:
            entities = self.entities
            
        self.reSetScene(entities)

        if len(path)>0:
            for action in path:
                if not isinstance(action,Message):
                    res = self.doActions(actions={action['actor']:[action]},
                                  detailLevel=0,entities=entities)

        actorName = obj['actor']
        try:
            actorName = actorName.name
        except:
            pass
        print 'actorName ',actorName
        entities.objectives = [(actorName,obj['type'],'Maximize')]
        turn = [{'name':actorName}]

        result = entities.microstep(turn,hypothetical=True,explain=False)
        for key,observed in result.items():
            if key != 'explanation':
                try:
                    actor = self.entities.__getitem__(key)
                except KeyError:
                    continue
                print 'actor ',actor
                res = entities.suggest(actor.name,observed['decision'],entities.objectives,entities)
                print res
                res = self.searchResult(res,exclude)
                if not res == {}:
                    return res
                else:
                    return None



    def findSuggestion2(self,path,obj,exclude,entities=None):
        
        if entities == None:
            entities = self.entities
            
        self.reSetScene(entities)

        if len(path)>0:
            for action in path:
                if not isinstance(action,Message):
                    res = self.doActions(actions={action['actor']:[action]},
                                  detailLevel=0,entities=entities)

        actorName = obj['actor']
        
        nextturn = entities.next() 

        try:
            actorName = actorName.name
        except:
            pass

        actor = entities.__getitem__(actorName)
        
        otherObj = None

        for other in entities:
            if other == actorName:
                continue

            otherEntity = entities.__getitem__(other)

            for option in otherEntity.actions.getOptions():
##                [{'red-move2':[Action({'actor':'wolf','type':'wait'})]}]
                if option[0]['object']:               
                    actor.fixedActions=[{`obj`:[Action({'actor':other,'type':option[0]['type'],
                                                                           'object':option[0]['object']})]}]
                else:
                    actor.fixedActions=[{`obj`:[Action({'actor':other,'type':option[0]['type']})]}]
                    
                result = entities.microstep(nextturn,hypothetical=True,explain=False)
        
                for key in result['decision'].keys():
                    if obj == result['decision'][key][0]:
                        otherObj = option[0]
                        break
                
            actor.fixedActions = []
            if not otherObj == None:
                break
        
        
        #actor.entities.objectives = [(otherObj['actor'],otherObj['type'],'Maximize')]
        actor.entities.objectives = [('wolf','move2','Maximize')]
        #turn = [{'name':otherObj['actor']}]
        turn = [{'name':'wolf'}]

        #self.execute('act '+actorName+' '+obj['type'])
        self.execute('act red move2 wolf')

        result = actor.entities.microstep(turn,hypothetical=True,explain=False)

        for key,observed in result.items():
            if key != 'explanation':
                #try:
                #    actorSuggest = entities.__getitem__(key]                  
                #except KeyError:
                #    continue
                
                #res = entities.suggest(actorSuggest.name,observed['decision'],entities.objectives)
                res = actor.entities.suggest('wolf',result['decision'],actor.entities.objectives)
                print res
                res = self.searchResult(res,exclude)
                if not res == {}:
                    return res
                else:
                    return None
                

    def incrementalFitSequence(self,storyPath,fixedgoals=[],delta=0,entities=None):
        if entities == None:
            entities = self.entities
        
        self.reSetScene(entities)
        for i in range(-1,len(storyPath)):
            path = storyPath[0:i+1]
            for actor in entities.members():
                name = actor.name
                self.reSetScene(entities)
                res = self.fitSequence(path,name,fixedgoals,delta,entities)
                if not res == 1:
                    return path
        return []
                        


    
    def fillGap(self,fixedgoals=[],maxstep=4,path=[],
               islands = [],actors = ['wolf','red'],entities=None):
        
        if entities == None:
            entities = self.entities
        
        entityname = '' 

        self.reSetScene(entities)
        
        if len(path)>0:
            for action in path:
                if action['actor']== actors[0]:
                    entityname = actors[1]
                else:
                    entityname = actors[0]
        else:           
            nextturn = entities.next()
            for turn in nextturn:
                entityname = turn['name']

        entity = entities.__getitem__(entityname)
        options = entity.actions.getOptions()
        options = entity.updateActionChoices(options,includeLocation = True)
        for action in options:
##            if action[0]['type']in['move2'] and path ==[]:
            #if action[0]['type']in['move2']:
            #    continue
            pathnew = copy.copy(path)    
            pathnew.append(action[0])
            if self.checkOrder(pathnew,islands):
                if self.checkComplete(pathnew,islands):                    
                    for actor in actors:
                        self.reSetScene(entities)
                        print 'fillGap, try: ',pathnew
                        res = self.fitSequence(pathnew,actor,fixedgoals,delta=-.000001,entities=entities)
                        if not res == 1:
                            break
                    else:
                        return pathnew
                else:
                    maxstepnew = maxstep-1
                    if maxstepnew >= 0:
                        res = self.fillGap(fixedgoals,maxstepnew,pathnew,islands,actors,entities)
                        if (not res == None):
                            return res
    
        return None
                    
                

            

    def generateAllPosPath(self,actor,fixedgoals=[],maxstep=20,path=[],delta=-.000001,
                           constraints=[],adjgoals=None, adjgoalKeys=None, P=None, start=[],entities=None):
        
        if entities == None:
            entities = self.entities
            
        entity = entities.__getitem__(actor)

        ## bring the simulation to the state as specified in path
        self.reSetScene(entities)
        if len(path)>0:
            for action in path:
                res = self.doActions(actions={action['actor']:[action]},
                                  detailLevel=0,entities=entities)
                                            

        ## now start generating process
        allConstraints = entity.fitAllAction()

        allActionString = []
        for action in entity.actions.getOptions():
            allActionString.append(`action[0]`) 

        i = 0
        if start == []:
            finiedIndex = -1
        else:
            finiedIndex = allActionString.index(start[5-maxstep])
        for action in entity.actions.getOptions():
            if i < finiedIndex:
                i += 1
                continue
            i += 1
            
            pathnew = copy.copy(path)    
            pathnew.append(action[0])

            myConstraints = copy.copy(constraints)
            for newConstraints in allConstraints[str(action)]:
                myConstraints.append(newConstraints)
            
            ## note myConstraints will be updated in this step
            res = self.adjustGoalWeights(myConstraints,actor,fixedgoals,delta,entities)
            if res == 1:
                res1 = self.doActions(actions={action[0]['actor']:[action[0]]},
                              detailLevel=0,entities=entities)
                while (1):
                    actorHasTurn = 0
                    nextturn = entities.next()
                    for turn in nextturn:
                        if turn['name'] == actor:
                            actorHasTurn = 1
                            break
                    if actorHasTurn == 1:
                        break
                    else:
                        res2 = self.step()
                        pathnew.append(copy.deepcopy(res2[0]))
            
                
                maxstepnew = maxstep-1
                if maxstepnew >= 0:
                    self.generateAllPosPath(actor,fixedgoals,maxstepnew,pathnew,delta,myConstraints,adjgoals, adjgoalKeys, P, start,entities)
                else:
                    print pathnew


    def easyFit(self,actor,storyPath):
        #print 'fit path: ',storyPath
        entities = copy.deepcopy(self.copyEntities)
        # delta -0.01 allows wolf to help woodcutter, but also granny to kill wolf
        # delta -0.001 can fit woodcutter to not kill wolf
        if self.fitSequence(storyPath,actor,fixedgoals=['alive','eaten'],delta=0,entities=entities) == 1:
            entity = entities.__getitem__(actor)
            return entity.goals
        #receivers = ['woodcutter','hunter','wolf','red','granny']
        #entity = self.entities.__getitem__(actor)
        #    
        #for feature in ['likeTalk','likeMove','has-cake','full','redEaten','wolfAlive']:
        #    for goal,weight in entity.goals.items():
        #        key = goal.toKey()
        #        if key['feature'] == feature:
        #            break
        #        
        #    for weight in [0.00000000000000000001,0.001,0.01]:
        #        success = 1
        #        entities = copy.deepcopy(self.copyEntities)        
        #        entity = entities.__getitem__(actor)                
        #        entity.setGoalWeight(goal,weight,False)
        #        
        #        for desired in storyPath:
        #            #next = entities.next()
        #            #print next[0]['name']
        #            if not isinstance(desired,Message):
        #                if desired['actor']==actor:
        #                    try:
        #                        #delta = entities.microstep(hypothetical=False,explain=False)
        #                        #for key in delta['decision'].keys():
        #                        #    res = delta['decision'][key][0]
        #                        #    print res
        #                        #    if not res == desired:                    
        #                        #        # except may be generated when try to fit an action that is not possible, e.g. not at the same places
        #                        #        constraints = entity.generateConstraints([desired])
        #                        #        
        #                        #        for constraint in constraints:
        #                        #            #break the tie
        #                        #            if constraint['delta'] <0:
        #                        #                print res,constraint['delta']
        #                        #            if constraint['delta'] <= -0.01:
        #                        #                success = 0
        #                        #                break
        #                        constraints = entity.generateConstraints([desired])
        #                        for constraint in constraints:
        #                            #break the tie
        #                            #if constraint['delta'] <0:
        #                            #    print constraint['delta']
        #                            if constraint['delta'] <= -0.01:
        #                                success = 0
        #                                break
        #                        if success:
        #                            #print desired
        #                            entities.microstep([{'name':desired['actor'],'choices':[[desired]]}],hypothetical=False,explain=False)
        #    
        #                    except:
        #                        #print 'generateConstraints error'
        #                        success = 0
        #            
        #            if success == 0:
        #                break
        #            
        #            
        #            if isinstance(desired,Message):
        #                #print 'message'
        #                entities.performMsg(desired,'granny',receivers,[],self.debug)
        #            else:
        #                #print desired
        #                entities.microstep([{'name':desired['actor'],'choices':[[desired]]}],hypothetical=False,explain=False)
        #        
        #        if success == 1:
        #            #print entity.goals
        #            return entity.goals
        return None
                    
        
    def fitSequence(self,storyPath,actor,fixedgoals=[],delta=0,entities=None):
        receivers = ['woodcutter','hunter','wolf','red','granny']
        if entities == None:
            entities = self.entities
            
        constraints = []
        entity = entities.__getitem__(actor)
        for desired in storyPath:
            if not isinstance(desired,Message):
                if desired['actor']==actor:
                    try:
                        # except may be generated when try to fit an action that is not possible, e.g. not at the same places
                        newConstraints = entity.generateConstraints([desired])
                    except:
                        return -1   
                    for new in newConstraints:
                        constraints.append(new)

            if isinstance(desired,Message):
                entities.performMsg(desired,'granny',receivers,[],self.debug)
            else:
                entities.microstep([{'name':desired['actor'],'choices':[[desired]]}],hypothetical=False,explain=False)
        res = self.adjustGoalWeights(constraints,entity,fixedgoals,delta)
        #print 'adjustGoalWeights result',res
        
        #if res == -1 or res == 0:
        #    return -1
        #else:
        #    return 1
        return res


    def adjustGoalWeights(self,constraints,entity,fixedgoals=[],delta=0):
        origoals = copy.deepcopy(entity.goals)

        initViolation = 0
        for constraint in constraints:
            # break the tie here, only fit if action acturally gets a lower utility
            # don't need delta anymore
            if constraint['delta'] < 0:
                initViolation +=1

        if initViolation == 0:
            return 1
        
        
        if len(fixedgoals) >= len(origoals):
            return 0

        Violation = self.satisfyConstraints(constraints,entity,fixedgoals,delta)
            
        if Violation > initViolation:
            entity.setGoals(origoals)

        
        if Violation > initViolation or Violation == -1:
            return -1
        elif Violation == 0:
            return 1
        else:
            print Violation
            return 0

      
            
    ## fixedgoals: a list of goals whose weights will not be adjusted
    ## delta: threshold for constraint, default to be 0 in fitting, e.g., the value of the selected action
    ## must be bigger than all other actions
    ## when generating possible path, delta is set to -.00000001, so that actions with equal utility are all
    ## possible actions for the character
    ## returns the number of violated constraints afer fitting
    def satisfyConstraints(self,constraints,entity,fixedgoals=[], delta = 0,):
        origoals = entity.getGoals()

        ## the goals we will play with, if not success in fitting, will set back to original setting
        adjgoals = copy.deepcopy(origoals)

        removeList = []
        for goal in adjgoals:
            if goal.key in fixedgoals:
                #if goal.entity[0] == 'wolf':
                #    continue
                removeList.append(goal)
        for goal in removeList:
            adjgoals.remove(goal)

        adjgoalKeys = []
        for goal in adjgoals:
            adjgoalKeys.append(goal.toKey())

        n = len(adjgoals)
        ## construct the P matrix
        P = matrix (0.0,(n,n),tc = 'd')
        P [::n+1]+=2

        ## construct the Q matrix
        Q = matrix (0.0, (n,1),tc = 'd')
        for i in range(n):
            Q[i] = entity.getGoalWeight(adjgoals[i])*(-2)

        ## construct G,h        
        h = [delta]*(len(constraints)+2*n)
        g = [[]]*n
        j = 0
        for constraint in constraints:
            for goal in constraint['slope']:
                if goal in adjgoalKeys:
##                    if goal['feature'] == 'alive':
##                        print 'alive is adjustable',goal
                    i =  adjgoalKeys.index(goal)
                    if g[i] == []:
                        g[i] = [-constraint['slope'][goal]]
                    else:
                        g[i].append(-constraint['slope'][goal])
                else:
                    for fullGoal in origoals:
                        ## find out the corresponding goal
                        if goal == fullGoal.toKey():
                            ## assume goals not entering the fitting process have high weight
                            if goal['feature'] == 'alive':
##                                print 'alive set to 10',goal
                                value = constraint['slope'][goal]*1000
                            else:
                                value = constraint['slope'][goal]*1000
                            if fullGoal.direction == 'min':
                                value = -1*value
                            h[j]+= value
                            #print goal,value
                            break
            j=j+1

        ## add inequations that each of the goal weight is in [-5 5]
        for i in range(n):
            for j in range(n):
                if j == i:
                    g[j].append(1)
                else:
                    g[j].append(0)
                    
        for i in range(n):
            for j in range(n):
                if j == i:
                    g[j].append(-1)
                else:
                    g[j].append(0)

        for i in range (len(constraints),len(h)):
            index = i - len(constraints) -n
            if index >= 0:
                if string.find(adjgoals[index].key,'norm')>-1:
                    ## all the norm related goals should have weight >=0
                    h[i] = 0.0000001
                else:
                    h[i] = 5
            else:
                h[i] = 5
        
        G = matrix(g,tc='d')
    
        h = matrix(h,tc='d')
        
        res = None
        ## there is no solution
        try:
            res = qp(P,Q,G,h)
        except StandardError:
            print 'fitting result: StandardError'
            return -1
    
        if not res['status']=='optimal':
            print 'fitting result: not optimal'
            return -1
        
        
        for i in range(len(adjgoals)):
            entity.setGoalWeight(adjgoals[i],res['x'][i],None)
            
        for fullGoal in origoals:
            for i in range(len(fixedgoals)):
                ## find out the corresponding goal
                if fixedgoals[i] == fullGoal.key:
                    if fixedgoals[i] == 'alive':
                        entity.setGoalWeight(fullGoal,5,None)
                    else:
                        entity.setGoalWeight(fullGoal,5,None)
                    break
                        
        
        entity.normalizeGoals()
        print entity.name
        print entity.goals

        Violation=0
        excludeList = []
        notfitted = []
        #for constraint in constraints:
        #    actgoals = entity.getGoalVector()['total'].domain()[0]
        #    actgoals.fill(constraint['plane'].keys())
        #    if actgoals*constraint['plane'] > delta:
        #        ## if constraint is satisfied
        #        continue
        #    Violation += 1
##
##            for goal in adjgoals:
##                if constraint['slope'][goal.toKey()] == 0.0:
##                    excludeList.append(goal.name)
##                
##            if len(excludeList) == len(adjgoals):
##                notfitted.append(constraint)
##                continue

##        print 'number of violations that could not be fitted: ',len(notfitted)     
##        print 'number of violations after fitting: ',Violation


        #return Violation
        return 0





if __name__ == '__main__':
    import getopt
    import sys

    try:
        import psyco
        psyco.full()
    except ImportError:
        print 'Unable to find psyco module for maximum speed'

    script = None
    scenario = None
    society = None
    domain = None
    display = 'tk'
    debug = 0
    error = None
    agentClass = ThespianAgent ##this is the module
    multiagentClass = ThespianAgents

    ThespianAgents.sceneID = '3'
    
    try:
        optlist,args = getopt.getopt(sys.argv[1:],'hf:s:d:v',
				     ['file=','shell=','domain=','society=',
                                      'debug=','help','version'])
    except getopt.error:
        error = 1
        optlist = []
        args = []

    for option in optlist:
        if option[0] == '--file' or option[0] == '-f':
	        script = option[1]
        elif option[0] == '--shell' or option[0] == '-s':
	        display = option[1]
        elif option[0] == '--domain' or option[0] == '-d':
            domain = option[1]
            exec('import teamwork.examples.%s as classModule' % (domain))
            # Convert any old-school hierarchies
            if isinstance(classModule.classHierarchy,dict):
                society = GenericSociety()
                society.importDict(classModule.classHierarchy)
            else:
                society = classModule.classHierarchy
        elif option[0] == '--society':
            society = option[1]
        elif option[0] == '--help' or option[0] == '-h':
            error = 1
        elif option[0] == '--debug':
            debug = int(option[1])
        elif option[0] == '--version' or option[0] == '-v':
            print 'PsychSim %s' % (PsychShell.__VERSION__)
            sys.exit(0)
        else:
            error = 1
        
    if len(args) > 0:
        if len(args) > 1:
            error = 1
        else:
            scenario = args[0]

    if error:
        print 'PsychShell.py',\
              '[--domain|-d <domain>]',\
              '[--file|-f <script filename>]',\
              '[--shell|-s tk|terminal]',\
              '[--society <filename>]',\
              '<scenario filename>'
        print
        print '--domain|-d\tIndicates the class path to the generic society definition'
        print '--society\tIndicates the file name containing the generic society'
        print '--file|-f\tIndicates the file containing a script of commands to execute'
        print '--shell|-s\tIf "tk", use GUI; if "terminal", use interactive text (default is "tk")'
        print '--version|-v\tPrints out version information'
        print '--help|-h\tPrints out this message'
        print
        sys.exit(-1)

    if domain:
        pass
    else:
        domain = 'Thespian.RedRidingHoodClasses'
        exec('import teamwork.examples.%s as classModule' % (domain))
        # Convert any old-school hierarchies
        if isinstance(classModule.classHierarchy,dict):
            society = GenericSociety()
            society.importDict(classModule.classHierarchy)
        else:
            society = classModule.classHierarchy

    
                
    if display == 'tk':
        from teamwork.widgets.PsychGUI.Gui import *
        shell = GuiShell(scenario=scenario,
                         classes=society,
                         agentClass=agentClass,
                         multiagentClass=multiagentClass,
                         debug=debug)
        

    else:
        from teamwork.shell.TerminalShell import TerminalShell
        shell = TerminalShell(entities=scenario,
                              classes=society,
                              file=script,
                              agentClass=agentClass,
                              multiagentClass=multiagentClass,
                              debug=debug)

    if society and not domain:
        shell.loadSociety(society,overwrite=True)
    shell.mainloop()
    
