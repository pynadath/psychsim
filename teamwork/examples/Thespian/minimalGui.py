
"""
__version__ = "$Revision: 1.10 $"
__date__ = "$Date: 2004/04/24 22:13:31 $"
"""

from PythonCard import model

from ThespianShell import ThespianShell

import string
import sys



class MinimalGui(model.Background):
    ratInTeam = []
    
    #actionitems = ['request-match', 'request-exercise',  'accept', 'reject', 'eshock', 'feedV','buyLR', 'catchSR']
    actionitems = ['request-match', 'request-exercise', 'eshock', 'feedV']
    actionitems1 = ['request-match', 'request-exercise', 'eshock']
    object = ['labrat1', 'labrat2', 'streetrat'] 
    terminal = None
        
    def on_initialize(self, event):
        self.terminal = ThespianShell(scene='6')
        nextturn = self.terminal.entities.next()
        actor = nextturn[0]['name']
        while not actor == 'usr':
            self.terminal._step(1)
            nextturn = self.terminal.entities.next()
            actor = nextturn[0]['name']


    def on_object_select(self, event):
        self.update_action_choice()

    def update_action_choice(self):
        object = self.components.object.stringSelection
        
        if self.terminal.entities[object].getState('ThespianType').expectation() < .5:
            if (object == 'labrat1' or object == 'labrat2'):
                if self.terminal.entities['usr'].getState('money').expectation() > .99:
                    self.components.actionchoice.items=['buyLR']
                else:
                    self.components.actionchoice.items=[]
            else:
                self.components.actionchoice.items=['catchSR']
        elif self.terminal.entities[object].getState('requested-to-match').expectation() > .5:
            self.components.actionchoice.items=['accept', 'reject']
        elif self.terminal.entities['usr'].getState('money').expectation() > .05:
            self.components.actionchoice.items = self.actionitems
        else:
            self.components.actionchoice.items = self.actionitems1
            
        self.components.actionchoice.stringSelection = self.components.actionchoice.items[0]
        
        
    def update_agent_state(self):
        
        ratInTeam = []
        if self.terminal.entities['labrat1'].getState('ThespianType').expectation() >= .5:
            ratInTeam.append(self.components.labrat1)
        if self.terminal.entities['labrat2'].getState('ThespianType').expectation() >= .5:
            ratInTeam.append(self.components.labrat2)
        if self.terminal.entities['streetrat'].getState('ThespianType').expectation() >= .5:
            ratInTeam.append(self.components.streetrat)
        
        
        for rat in ratInTeam:
            rat.DeleteAllItems()
            root = rat.addRoot(rat.name)
            rat.setItemHasChildren(root, 1)
            rat.appendItem(root, "health "+str(self.terminal.entities[rat.name].getState('health').expectation()))
            rat.appendItem(root, "raport "+str(self.terminal.entities[rat.name].getState('SD').expectation()))    
            rat.selectItem(root)
            
        self.components.money.text = 'Your Money left: '+str(int(max(0,self.terminal.entities['usr'].getState('money').expectation()*1000)))
        self.components.day.text = 'Day '+str(int(self.terminal.entities['timer'].getState('day').expectation()+1))
        
        
    def on_Submit_mouseClick(self, event):
        object = self.components.object.stringSelection
        act = self.components.actionchoice.stringSelection
        self.terminal.execute('act usr '+act+' '+object)
        
        i = 0
        nextturn = self.terminal.entities.next()
        actor = nextturn[0]['name']
        while not actor == 'usr':
            sequence, res = self.terminal._step(1)
            if actor in ['labrat1', 'labrat2', 'streetrat'] :
                self.components.conversation.AppendText(`res`+'\n')
            i = i+1
            nextturn = self.terminal.entities.next()
            actor = nextturn[0]['name']
        
        if i<4 :
            self.terminal.execute('act usr wait')
            i = i+1
            nextturn = self.terminal.entities.next()
            actor = nextturn[0]['name']
            while (not actor == 'usr') and i<4:
                sequence, res = self.terminal._step(1)
                if actor in ['labrat1', 'labrat2', 'streetrat'] :
                    self.components.conversation.AppendText(`res`+'\n')
                i = i+1
                nextturn = self.terminal.entities.next()
                actor = nextturn[0]['name']
            
        self.update_agent_state()
        self.update_action_choice()
        

if __name__ == '__main__':
    
    app = model.Application(MinimalGui)
    
    app.MainLoop()
