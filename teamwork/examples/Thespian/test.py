from ThespianShell import ThespianShell

import string
import sys
import random

from teamwork.utils.PsychUtils import *
from teamwork.messages.PsychMessage import *
from teamwork.action.PsychActions import *

from ThespianAgent import *
from ThespianAgents import *
from ThespianUtils import *

from cvxopt.base import matrix




if __name__ == '__main__':
    start = time.time()
    
    terminal = ThespianShell(scene='3')

    diff = time.time()-start
    print
    print 'Time: %7.4f' % (diff)
    
    ##start = time.time()
    storyPath = [\
                 #Action({'actor':'usr','type':'buyLR','object':'labrat1'}),
                 #Action({'actor':'labrat1','type':'exercise'}),
                 #Action({'actor':'usr','type':'request-match','object':'labrat1'}),
                 #Action({'actor':'labrat1','type':'accept','object':'usr'}),
                 #Action({'actor':'labrat1','type':'match'}),
                 #Action({'actor':'otherTeam','type':'lose'}),
                 #Action({'actor':'usr','type':'request-match','object':'labrat1'}),
                 #Action({'actor':'labrat1','type':'reject','object':'usr'}),
                 #Action({'actor':'usr','type':'eshock','object':'labrat1'}),
                 #Action({'actor':'usr','type':'request-match','object':'labrat1'}),
                 #Action({'actor':'labrat1','type':'accept','object':'usr'}),
                 #Action({'actor':'labrat1','type':'match'}),
                 #Action({'actor':'labrat1','type':'request-match','object':'usr'}),
                 Action({'actor':'red','type':'moveto-granny'}),
                 Action({'actor':'red','type':'move1'}),
                ]    
    #print terminal.fitSequence(storyPath,'red',['sameLocation','redAlive','wolfAlive'],-0.000001)
    #
    #diff = time.time()-start
    #print
    #print 'Time: %7.4f' % (diff)
    #
    #goals ={}
    #goals['labrat1'] = terminal.entities['chacha'].goals()
    #    
    #terminal.reSetSceneWithGoals(goals)

##    delta = terminal.entities['red'].entities.hypotheticalAct({'red':[Action({'actor':'red','type':'move'})]})

    #terminal.execute('act usr catchSR streetrat')
    #terminal.execute('director')
    #terminal.execute('step')



## teting for suggest functions
    #fixedgoals=['alive','sameLocation','actAlive','resp-norm','specialRule']
    #msg = Message('entities:red:state:location = .2')
    #msg['type'] = '_message'
    #msg.forceAccept('red')
#    path = [\
#            Action({'actor':'red','type':'move2','object':'wolf'}),
###            Action({'actor':'wolf','type':'wait','object':'red'}),
###        
###            Action({'actor':'red','type':'greet-init','object':'wolf'}),
###            Action({'actor':'wolf','type':'greet-resp','object':'red'}),
###            
###            Action({'actor':'wolf','type':'enquiry-about-granny','object':'red'}),
###            Action({'actor':'red','type':'inform-about-granny','object':'wolf'}),
###            Action({'actor':'red','type':'wait'}),
###            Action({'actor':'wolf','type':'wait'}),
###            
#        ]
##    terminal.executeCommand('step')
    #terminal.FitToPlotPoint(path,fixedgoals)
    #terminal.findSuggestion2([],Action({'actor':'red','type':'move2','object':'wolf'}),exclude=[{'feature': 'location', 'entity': 'red'},
    #                                                                   {'feature': 'alive', 'entity': 'red'}])
## testing for suggest functions ends here
    
    #path = [\
    #        Action({'actor':'granny','type':'wait'}),
    #        Action({'actor':'hunter','type':'wait'}),
    #        Action({'actor':'red','type':'moveto-granny'}),
    #        Action({'actor':'wolf','type':'move1'}),
    #        #Action({'actor':'wolf','type':'enquiry','object':'red'}),
    #        
    #    ]   
    #
    #path = ['hunter-kill-wolf']
    #print terminal.searchPath(path,'anybody-kill-wolf')
    #terminal.make_story('red','power',1.0,terminal.entities,path)
    #print terminal.entities.suggest('wolf',Action({'actor':'wolf','type':'move2'}),('wolf','inform','Maximize'))
    #print terminal.entities.suggest('granny',Action({'actor':'granny','type':'wait'}),('granny','kill','Maximize'))
    #print terminal.change_characters_state('red',{'red':[Action({'actor':'red','type':'wait'})]},[('red','kill','Maximize')])
    #
    #
    #
    terminal.execute('act granny wait')
    terminal.execute('act hunter wait')
    terminal.execute('act red wait')
    #terminal.execute('act wolf move-2')
    #terminal.execute('act wolf move-2')
    #terminal.execute('act wolf move-2')
    #terminal.execute('act wolf move-2')
    
    #terminal.execute('act wolf help woodcutter')
    #terminal.execute('step ')
    #terminal.execute('act wolf enquiry woodcutter')
    #terminal.execute('step ')
    #terminal.execute('act wolf enquiry woodcutter')
    #terminal.execute('step ')
    #terminal.execute('act wolf enquiry woodcutter')
    #terminal.execute('step ')
    
    #print terminal.entities.suggest('usr',Action({'actor':'usr','type':'offer-safesex','object':'vc'}),('usr','accept-drink','Maximize'))


    terminal.mainloop()

