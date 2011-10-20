goals = {}

def testFitting():
    storyPath = [\
##                 Action({'actor':'granny','type':'wait'}),
##                 Action({'actor':'red','type':'escape','object':'wolf'}),
##                 Action({'actor':'wolf','type':'move2'}),
                
                 Action({'actor':'granny','type':'wait'}),
                 Action({'actor':'red','type':'greet-init','object':'wolf'}),
                 Action({'actor':'wolf','type':'greet-resp','object':'red'}),
                 Action({'actor':'granny','type':'wait'}),
                 Action({'actor':'red','type':'wait'}),
                 Action({'actor':'wolf','type':'enquiry','object':'red'}),
                 Action({'actor':'granny','type':'wait'}),
##
##                 Action({'actor':'granny','type':'wait'}),
##                 Action({'actor':'red','type':'move2'}),
##                 Action({'actor':'wolf','type':'move2'}),
##                 Action({'actor':'granny','type':'wait'}),
##                 Action({'actor':'red','type':'tell-about-granny','object':'wolf'}),
##
####                 Action({'actor':'red','type':'enquiry','object':'wolf'}),
####                 Action({'actor':'wolf','type':'inform','object':'red'}),
####                 Action({'actor':'granny','type':'wait'}),
####                 Action({'actor':'red','type':'move2'}),
####                 Action({'actor':'wolf','type':'move2'}),
                 ]
##    print
    res = terminal.fitSequence(storyPath,'wolf',['alive','sameLocation','actAlive','resp-norm','specialRule'])
    if res == 1:
        goals['wolf'] = terminal.entities['wolf'].getGoals()
        pass
    else:
        print "path can not be fitted"
        print storyPath
        print

    terminal.reSetScene()
    
    res = terminal.fitSequence(storyPath,'red',['alive','sameLocation','actAlive','resp-norm','specialRule'])
    if res == 1:
        goals['red'] = terminal.entities['red'].getGoals()
    
## construct necessory variables    
    fixedgoals=['alive','sameLocation','actAlive','resp-norm','specialRule']
##    entity = terminal.entities['red']
##    origoals = entity.getGoals()
##    adjgoals = copy.deepcopy(origoals)
##    removeList = []
##    for goal in adjgoals:
##        if goal.key in fixedgoals:
##            removeList.append(goal)
##    for goal in removeList:
##        adjgoals.remove(goal)
##
##    adjgoalKeys = []
##    for goal in adjgoals:
##        adjgoalKeys.append(goal.toKey())
##
##    n = len(adjgoals)
##    ## construct the P matrix
##    P = matrix (0.0,(n,n),tc = 'd')
##    P [::n+1]+=2
    
##    terminal.executeCommand('step 15')
##    terminal.reSetScene()
    

## test "FitToPlotPoint"
##    msg = Message('entities:red:state:location = .2')
##    msg['type'] = '_message'
##    msg.forceAccept('red')
##
##    path = [\
##            Action({'actor':'red','type':'move2'}),
####            msg,
####            Action({'actor':'wolf','type':'wait'}),
####        
####            Action({'actor':'red','type':'greet-init','object':'wolf'}),
####            Action({'actor':'wolf','type':'greet-resp','object':'red'}),
####            
####            Action({'actor':'wolf','type':'enquiry-about-granny','object':'red'}),
####            Action({'actor':'red','type':'inform-about-granny','object':'wolf'}),
####            Action({'actor':'red','type':'wait'}),
####            Action({'actor':'wolf','type':'wait'}),
####            
##        ]
##    terminal.executeCommand('step')
##    terminal.FitToPlotPoint(path,fixedgoals)
    
##    testFitting()
##
##    terminal.reSetSceneWithGoals(goals)
    
##    print "generating all possible path"
##    terminal.generateAllPosPath('red',fixedgoals=fixedgoals,maxstep=5,
##                                adjgoals=adjgoals,adjgoalKeys=adjgoalKeys,P=P)

##    terminal.reSetSceneWithGoals(goals)
##    
####    print "vary model"    
####    terminal.varyModel('red',['hunter','granny','red'],models=['evil','good'])
####
####    terminal.reSetSceneWithGoals(goals)
##    
##    print "vary goal weights"
##    terminal.varyGoal('red',fixedgoals)
##
##    terminal.reSetSceneWithGoals(goals)
    
##    print "vary beliefs about initial state"
##    terminal.varyInitialState('red',varyList)
##
##    terminal.reSetSceneWithGoals(goals)
##    terminal.reSetScene()


##    start = ['red-wait', 'red-bye-init-wolf', 'red-enquiry-wolf', 'red-enquiry-hunter', 'red-enquiry-hunter']
##    print 'red\'s belief about wolf is set to evil and red wants to be alive'
##    terminal.generateAllPosPath('red',fixedgoals,5,adjgoals=adjgoals, adjgoalKeys=adjgoalKeys, P=P, start=start )
##    terminal.reSetSceneWithGoals(goals)

## testing what belief change to the agent is needed to maximize the objectives
## however can not changed agent's beliefs about other 

## test "suggest" for wolf to choose wait instead of eatting red    
##    terminal.execute('act red move2')
##    entity = terminal.entities['wolf']
##    terminal.entities.objectives = [('wolf','wait','Maximize')]

##    turn = [{'name':'wolf'}]
##
##    result = terminal.entities.microstep(turn,hypothetical=True,explain=True)
##        
##    for key,observed in result.items():
##        if key != 'explanation':
##            try:
##                actor = terminal.entities[key]
##            except KeyError:
##                continue
##            
##            terminal.suggest(actor,observed['decision'])
    

## testing for red to move even though wolf may eat her
## now automated
    
##    terminal.entities.objectives = [('red','move2','Maximize')]
##    turn = [{'name':'red'}]
##
##    result = terminal.entities.microstep(turn,hypothetical=True,explain=True)
##        
##    for key,observed in result.items():
##        if key != 'explanation':
##            try:
##                actor = terminal.entities[key]
##            except KeyError:
##                continue
##            
##            terminal.suggest(actor,observed['decision'])



    red = terminal.entities['red']
    wolfred = red.entities['wolf']

## this part just tests the "multistepForSuggest" function, which supply
## a fixed set of actions for agents in other agent's lookahead process
    
##    wolfred.actions.values = []
##    wolfred.actions.extra = [Action({'actor':'wolf','type':'wait'})]
##    wolfred.actions._generated = None

##    action = Action({'actor':'red','type':'wait'})
##    sequence = red.multistepForSuggest(2,
##                            start={'red':action},
##                            state=copy.deepcopy(red.getAllBeliefs()))

##    sequence = red.multistep(2,
##                            start={'red':action},
##                            state=copy.deepcopy(red.getAllBeliefs()))


## this part tests if "red" can be fitted to an action with the speciall lookahead process "multistepForSuggest"
##    allConstraints = red.fitAllAction(suggest=True)
##    tmp = allConstraints['[red-move2]']
##
##    res = terminal.adjustGoalWeights(tmp,'red',fixedgoals)
##    print res

##    msg = PsychMessage('entities:red:state:location = .2')
##    msg['type'] = '_message'
##    msg.forceAccept('red')
##    result = terminal.entities.performMsg(msg,'wolf',['red'],[],terminal.debug)


##    terminal.executeCommand('act red move2')
##    wolfred.applyPolicy()
