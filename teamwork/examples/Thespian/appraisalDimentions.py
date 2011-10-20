import string
import sys
import copy
from ThespianAgents import * 

fixedgoals=['sameLocation','actAlive','specialRule','resp-norm']
##fixedgoals=['resp-norm','conversation-flow-norm']

class appraisal():
    initEntities = None
    curEntities = None
    history = []

    def setupEntities(self,entities):
        for entityName in entities:
            self.setupDynamics(entities,entityName)
                            
        

    def setupDynamics(self,entities,entity,copyEntities=None):
        if copyEntities == None:
            copyEntities=self.initEntities
        entity = entities__getitem__(entity)
        if len(entity.entities)>0:
            for entityName in entity.entities:
                self.setupDynamics(entity.entities,entityName,copyEntities)
        if entity.parent:
            ##print entity.ancestry()
            entity.dynamics = copy.deepcopy(copyEntities__getitem__(entity.name).dynamics)
        

    
    def lookaheadTest(self,lookahead = 2):
        entities = copy.deepcopy(self.curEntities)
        self.setupEntities(entities)
        
        while lookahead>0:
            nextturn = entities.next()
            delta = entities.microstep(turns=nextturn,explain=False,hypothetical=False)
            #print delta['decision']
            lookahead = lookahead-1
            
        
            
    def updateHistory(self,action):
        self.history.append(action)
        turns = [{'name':action['actor'],'choices':[[action]]}]
        self.curEntities.microstep(turns,explain=False,hypothetical=False)


    def simulatePath(self, history = None):
        if history == None:
            history = self.history
            
        entities = copy.deepcopy(self.initEntities)
        self.setupEntities(entities)
        

        for preAction in history:
            turns = [{'name':preAction['actor'],'choices':[[preAction]]}]
            entities.microstep(turns,hypothetical=False,
                                            explain=False,
                                            )
        return entities
        

    def calUtilities(self,myname,action,lookahead = 0):
        # calculate what the utility will be without doing this action
        entities = copy.deepcopy(self.curEntities)
        self.setupEntities(entities)
        entities = entities[myname].entities
        
        preUtility = entities[myname].applyRealGoals(fixedgoals=fixedgoals).expectation()
        
        
        # calculate what the utility will be after doing this action
        # include lookahead

        turns = [{'name':action['actor'],'choices':[[action]]}]
        entities.microstep(turns,hypothetical=False, explain=False,)
        
        while lookahead > 0:
            nextturn = entities.next()
            delta = entities.microstep(turns=nextturn,hypothetical=False,explain=False)
            print delta['decision']
            #print delta['delta']
            lookahead = lookahead - 1
            
        curUtility = entities[myname].applyRealGoals(fixedgoals=fixedgoals).expectation()
##        print preUtility, curUtility

        return preUtility, curUtility
        
        

    def Relevance(self,myname,preUtility=-999, curUtility=-999,lookahead = 0):

        if preUtility == -999:
            preUtility, curUtility = self.calUtilities(myname,action,lookahead)
        
##        print preUtility, curUtility
        
        if preUtility == 0 and not curUtility == 0:
            return 1
        elif preUtility == 0 and curUtility == 0:
            return 0
        else:
            delta = abs ((curUtility - preUtility)/preUtility)
            return delta



    def Desirability(self,myname,preUtility=-999, curUtility=-999,lookahead = 0):
        
        if preUtility == -999:
            preUtility, curUtility = self.calUtilities(myname,action,lookahead)

        if preUtility == 0 and curUtility > 0:
            return 1
        elif preUtility == 0 and curUtility < 0:
            return -1
        elif preUtility == 0 and curUtility == 0:
            return 0
        else:
            return (curUtility - preUtility)/abs(preUtility)
        
    
    def novelty(self,myname,action,lookahead = 0):
        pass
####        turnNovelty = 1
####        expectedTurn = self.entities[character].entities.next()
####        for nextTurn in expectedTurn:
####            if action['actor'] == nextTurn['name']:
####                turnNovelty = 0

        entities = copy.deepcopy(self.curEntities)
        self.setupEntities(entities)
        entities = entities__getitem__(myname).entities
        
        
        utiList = []
        actionUtility = -9999999999
        higherUtility = 0.0
        
        actor = action['actor']
        if type(actor) == str:
            actor = entities[actor]
        
 
        for actionList in entities[actor.name].actions.getOptions():
            
            entitiesTmp = copy.deepcopy(entities)
            self.setupEntities(entitiesTmp)
            
            turns = [{'name':action['actor'],'choices':[actionList]}]
            entitiesTmp.microstep(turns,hypothetical=False, explain=False)
            
            lookaheadCount = lookahead
            while lookaheadCount > 0:
                nextturn = entitiesTmp.next()
                delta = entitiesTmp.microstep(turns=nextturn,hypothetical=False,explain=False)
                lookaheadCount = lookaheadCount - 1
           
            utility = entitiesTmp__getitem__(action['actor']).applyGoals().expectation()
            
            if actionList == [action]:
                actionUtility = utility
            else:
                utiList.append(utility)
        
        for utility in utiList:
            if utility - actionUtility > 0:
                higherUtility = higherUtility+1
        
        return higherUtility/(len(utiList)+1)

        
        
        
            
    def causalAttribution(self,myname,action,lookback = 3,lookahead = 0):
        responsibleAgent = []
        responsibility = []
        
        responsibleAgent.append(action['actor'])

        entities = copy.deepcopy(self.curEntities)
        entities = entities__getitem__(myname).entities

        #actorPreUtility = entities[action['actor']].applyGoals().expectation()
        #myPreUtility = entities[myname].applyGoals().expectation()
        actorUtility =0.0
        myUtility =0.0
        actorUtilityList=[]
        myUtilityList=[]
        
        actor = entities[action['actor']]
        hasGoalAboutMe = 0
        excludeList = []
        relatedPreUti = 0.0
        relatedUti = 0.0
        
        if action['actor'] == myname:
            hasGoalAboutMe = 1
        else:
            for goal in actor.getGoals():
                if goal.entity == [myname]:
                    hasGoalAboutMe = 1
                else:
                    excludeList.append(goal.key)

        if hasGoalAboutMe:
            relatedPreUti = entities__getitem__(action['actor']).applyRealGoals(fixedgoals=excludeList).expectation()

        # choices that both the actor and I will not lose in utility
        ggChoice = 0.0

        for actionList in entities__getitem__(action['actor']).actions.getOptions():
            #if lookahead>0:
            #    print actionList,
            entitiesTmp = copy.deepcopy(entities)
            self.setupEntities(entitiesTmp)
            
            turns = [{'name':action['actor'],'choices':[actionList]}]
            entitiesTmp.microstep(turns,hypothetical=False, explain=False)

            lookaheadCount = lookahead
            while lookaheadCount > 0:
                nextturn = entitiesTmp.next()
                delta = entitiesTmp.microstep(turns=nextturn,hypothetical=False, explain=False)
                #print delta['decision'],
                lookaheadCount = lookaheadCount - 1
            #print
            
            actorCurUtility = entitiesTmp__getitem__(action['actor']).applyGoals().expectation()
            myCurUtility = entitiesTmp__getitem__(myname).applyGoals().expectation()

            if actionList == [action]:
                if hasGoalAboutMe:
                    relatedUti = entitiesTmp__getitem__(action['actor']).applyRealGoals(fixedgoals=excludeList).expectation()
                    if relatedUti > relatedPreUti:
                        responsibility.append('Actor has goals about me, and get benifited though his/her action')
                        return responsibleAgent, responsibility
                actorUtility = actorCurUtility
                myUtility = myCurUtility
            else:
                actorUtilityList.append(actorCurUtility)
                myUtilityList.append(myCurUtility)
        
        for i in range(len(actorUtilityList)):
            if (actorUtilityList[i] >= actorUtility) and (myUtilityList[i] >= myUtility):
                ggChoice = ggChoice+1
        
        #actorBeliefMyUtility = 
                
        if ggChoice >0:
            responsibility.append('not coerced, but do not care about me and accidentally choose the action that hurts my utility')
        else:
            responsibility.append('coerced to do the action')


        ## look back one step, is the actor forced to act this way?
        if lookback > 0 and ggChoice == 0:
            historyTmp = copy.copy(self.history)
            
            for i in range(1,lookback):
                if len(historyTmp)<= 0:
                    break
                
                lastAct = historyTmp.pop()
                responsibleAgent.append(lastAct['actor'])
    
                entities = self.simulatePath(historyTmp)
                entities = entities__getitem__(myname).entities
                
                actorUtility =0.0
                myUtility =0.0
                actorUtilityList=[]
                myUtilityList=[]
    
                actor = entities[lastAct['actor']]
                hasGoalAboutMe = 0
                excludeList = []
                relatedPreUti = 0.0
                relatedUti = 0.0
                for goal in actor.getGoals():
                    if goal.entity == [myname]:
                        hasGoalAboutMe = 1
                    else:
                        excludeList.append(goal.key)
                if hasGoalAboutMe:
                    relatedPreUti = entities__getitem__(lastAct['actor']).applyRealGoals(fixedgoals=excludeList).expectation()
        
                # choices that both the actor and I will not lose in utility
                ggChoice = 0.0
    
                for actionList in entities__getitem__(lastAct['actor']).actions.getOptions():
            
                    entitiesTmp = copy.deepcopy(entities)
                    self.setupEntities(entitiesTmp)
                    
                    turns = [{'name':lastAct['actor'],'choices':[actionList]}]
                    entitiesTmp.microstep(turns,hypothetical=False, explain=False)
    
                    lookaheadCount = lookahead+i
                    while lookaheadCount > 0:
                        nextturn = entitiesTmp.next()
                        delta = entitiesTmp.microstep(turns=nextturn,hypothetical=False, explain=False)
                        lookaheadCount = lookaheadCount - 1
                    
                    actorCurUtility = entitiesTmp__getitem__(lastAct['actor']).applyGoals().expectation()
                    myCurUtility = entitiesTmp__getitem__(myname).applyGoals().expectation()
                       
                    if actionList == [lastAct]:
                        if hasGoalAboutMe:
                            relatedUti = entitiesTmp__getitem__(lastAct['actor']).applyRealGoals(fixedgoals=excludeList).expectation()
                            if relatedUti > relatedPreUti:
                                responsibility.append('Actor has goals about me, and get benifited though his/her action')
                                return responsibleAgent, responsibility
                        actorUtility = actorCurUtility
                        myUtility = myCurUtility
                    else:
                        actorUtilityList.append(actorCurUtility)
                        myUtilityList.append(myCurUtility)
                
                for i in range(len(actorUtilityList)):
                    if (actorUtilityList[i] >= actorUtility) and (myUtilityList[i] >= myUtility):
                        ggChoice = ggChoice+1
                        
                if ggChoice >0:
                    responsibility.append('not coerced, but do not care about me and accidentally choose the action that hurts my utility')
                else:
                    responsibility.append('coerced to do the action')



        return responsibleAgent, responsibility
            
            
    def Agency(self,myname,agent, action,lookahead = 0,fixSteps = 2):
        
        entities = copy.deepcopy(self.curEntities)
        entities = entities[myname].entities

        if len(entities[agent].actions.getOptions()) == 0:
            return 0
        
        preUtility = entities__getitem__(myname).applyGoals().expectation()
                 
        turns = [{'name':action['actor'],'choices':[[action]]}]
        entities.microstep(turns,hypothetical=False,explain=False,)

        lookaheadCount = lookahead
        while lookaheadCount > 0:
            turns = entities.next()
            entities.microstep(turns,hypothetical=False, explain=False,)
            lookaheadCount = lookaheadCount - 1
        
        curUtility = entities__getitem__(myname).applyGoals().expectation()
        
        # test if in the next i steps I can fix the problem
        Choice1 = 0.0
        Choice2 = 0.0

        for actionList in entities__getitem__(agent).actions.getOptions():
            entitiesTmp = copy.deepcopy(entities)
            self.setupEntities(entitiesTmp)
            
            lookaheadCount = fixSteps
            while lookaheadCount > 0:
                turns = entitiesTmp.next()
                for turn in turns:
                    if turn['name'] == agent:
                        turn['choices']=[actionList]
                entitiesTmp.microstep(turns,hypothetical=False, explain=False,)
                lookaheadCount = lookaheadCount - 1

            ## need to apply fixed goal first to make sure this is a possible move
            furUtility = entitiesTmp__getitem__(myname).applyGoals().expectation()

            if furUtility >= preUtility:
                Choice1 +=1
                print 'choice1    ',actionList
            elif furUtility > curUtility:
                Choice2 +=1
                print 'choice2    ',actionList
        
##        print Choice1,Choice2
        if Choice1/len(entities__getitem__(agent).actions.getOptions()) >= .5:
            agency = 1
        elif (Choice1+Choice2)/len(entities__getitem__(agent).actions.getOptions()) >= .5:
            agency = .5
        elif (Choice1+Choice2)/len(entities__getitem__(agent).actions.getOptions()) >= .3:
            agency = .3
        elif Choice1+Choice2 > 0:
            agency = .1
        else:
            agency = 0

        return agency
        
        
