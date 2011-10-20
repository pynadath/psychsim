import copy
import operator
import os
import string
from threading import *
import time
from Tkinter import *
import tkMessageBox
import Pmw

def multiply(x,y):
    return x*y

from teamwork.widgets.images import getImage
from teamwork.widgets.WizardShell import WizardShell
from teamwork.widgets.cookbook import MultiListbox
from teamwork.utils.PsychUtils import load
from teamwork.messages.PsychMessage import *
from teamwork.math.probability import *

class AnalysisWizard(WizardShell):
    wizname         = 'Message Analysis'
    wizimage        = 'analyzing_computer_tv_head_md_wht.gif'
##    busyimage       = os.path.dirname(__file__)+\
##                      '/../../images/animate.gif'
    frameWidth      = 600
    frameHeight     = 500
    phases = ['sender','receivers','overhearers','models','messages',
              'progress','results']

    def __init__(self, entities, sender=None, receivers=[],
                 messages=[], parent=None, **kw):
        self.sequence = self.phases[:]
        self.entities = entities
        self.sender = sender
        self.messages = {}
        for msg in messages:
            self.messages[msg['label']] = msg
        # Determine which phases are necessary
        if self.sender or len(self.messages) == 0:
            self.sequence.remove('sender')
        self.receivers = receivers
        if self.receivers or len(self.messages) == 0:
            self.sequence.remove('receivers')
        for agent in self.entities.members():
            if len(agent.models) > 0:
                break
        else:
            # No agents have possible stereotypes to vary
            self.sequence.remove('models')
        if len(self.messages) == 0:
            # We're not looking at messages at all
            self.sequence.remove('overhearers')
            self.sequence.remove('messages')
        self.panes = len(self.sequence)
        self.handlers = {'sender':self.createSelectSender,
                         'receivers':self.createSelectReceivers,
                         'overhearers':self.createSelectOverhearers,
                         'models':self.createSelectModels,
                         'messages':self.createSelectMessages,
                         'progress':self.createShowProgress,
                         'results':self.createShowResults,
                         }
        self.columns = []
        self.models = {}
        WizardShell.__init__(self,parent,**kw)
        self['image'] = getImage(self.wizimage)

    def createInterface(self):
        WizardShell.createInterface(self)
        # Add buttons
        self.buttonAdd('Cancel', command=self.done, state=1) 
        self.nextB = self.buttonAdd('Next', command=self.next, state=1)
        self.nextB.configure(default=ACTIVE)
        self.prevB = self.buttonAdd('Prev', command=self.prev, state=0)
        # Add main content of panes
        for index in range(self.panes):
            apply(self.handlers[self.sequence[index]],(index,))

    ## Pane for selecting sender(s)
    def createSelectSender(self,pane):
        senders = filter(lambda n:len(self.entities[n].entities) > 0 ,
                         self.entities.keys())
        widget = self.createcomponent('senders', (), None,
                                      Pmw.RadioSelect,
                                      (self.pInterior(pane),),
                                      labelpos='n',
                                      label_text='Select sender:',
                                      buttontype='radiobutton',
                                      orient='vertical',
                                      command=self.selectSender,
                                      )
        for name in senders:
            widget.add(name)
        if self.sender:
            widget.invoke(self.sender)
        widget.pack(fill='both',expand='yes')

    def selectSender(self,name):
        """Precludes the selected sender from being a potential receiver"""
        try:
            widget = self.component('receivers')
            if self.sender and self.sender != name:
                widget.component(self.sender).configure(state='normal')
            widget.component(name).configure(state='disabled')
            widget = self.component('hearers')
            if self.sender and self.sender != name:
                widget.component(self.sender).configure(state='normal')
            widget.component(name).configure(state='disabled')
            self.sender = name
        except KeyError:
            pass

    def getSender(self):
        return self.sender

    ## Pane for selecting receiver(s)
    def createSelectReceivers(self,pane):
        receivers = filter(lambda n:len(self.entities[n].entities) > 0,
                           self.entities.keys())
        widget = self.createcomponent('receivers', (), None,
                                      Pmw.RadioSelect,
                                      (self.pInterior(pane),),
                                      labelpos='n',
                                      label_text='Select receiver(s):',
                                      buttontype='checkbutton',
                                      orient='vertical',
                                      command=self.selectReceiver,
                                      )
        for name in receivers:
            widget.add(name)
            if name == self.getSender():
                widget.component(name).configure(state='disabled')
        widget.pack(fill='both',expand='yes')

    def selectReceiver(self,name,value):
        """Updates the availability of the selected receiver as a possible sender/overhearer"""
        if 'sender' in self.components():
            widget = self.component('sender')
            if value:
                self.nextB['state'] = 'normal'
                widget.component(name).configure(state='disabled')
            else:
                if len(self.getReceivers()) == 0:
                    self.nextB['state'] = 'disabled'
                widget.component(name).configure(state='normal')
        if 'hearers' in self.components():
            widget = self.component('hearers')
            if value:
                widget.component(name).configure(state='disabled')
            else:
                widget.component(name).configure(state='normal')
            
    def getReceivers(self):
        if self.receivers:
            return self.receivers
        else:
            return list(self.component('receivers').getvalue())

    ## Pane for selecting overhearer(s)
    def createSelectOverhearers(self,pane):
        receivers = filter(lambda n:len(self.entities[n].entities) > 0,
                           self.entities.keys())
        widget = self.createcomponent('hearers', (), None,
                                      Pmw.RadioSelect,
                                      (self.pInterior(pane),),
                                      labelpos='n',
                                      label_text='Select overhearer(s):',
                                      buttontype='checkbutton',
                                      orient='vertical',
                                      command=self.selectHearer,
                                      )
        for name in receivers:
            widget.add(name)
            if name == self.getSender() or name in self.getReceivers():
                widget.component(name).configure(state='disabled')
        widget.pack(fill='both',expand='yes')

    def selectHearer(self,name,value):
        """Updates the availability of the selected overhearer as a possible sender/receiver"""
        if 'sender' in self.components():
            # Make this hearer unavailable as a sender
            widget = self.component('sender')
            if value:
                self.nextB['state'] = 'normal'
                widget.component(name).configure(state='disabled')
            else:
                if len(self.getHearers()) == 0:
                    self.nextB['state'] = 'disabled'
                widget.component(name).configure(state='normal')
        if 'receivers' in self.components():
            # Make this hearer unavailable as a sender
            widget = self.component('receivers')
            if value:
                widget.component(name).configure(state='disabled')
            else:
                widget.component(name).configure(state='normal')
            
    def getHearers(self):
        return list(self.component('hearers').getvalue())

    ## Pane for selecting messages
    def createSelectMessages(self,pane):
        if len(self.messages) > 0:
            widget = self.createcomponent('messages',(),None,Pmw.RadioSelect,
                                          (self.pInterior(pane),),
                                          labelpos='n',
                                          label_text='Select message(s):',
                                          buttontype='checkbutton',
                                          orient='vertical',
                                          )
            for msg in self.messages.keys():
                widget.add(msg)
                widget.component(msg).invoke()
            widget.pack(fill='both',expand='yes')
        else:
            self.createSelectModels(pane)

    def getMessages(self):
        selection = self.component('messages').getvalue()
        return filter(lambda m:m in selection,self.messages.keys())
    
    ## Pane for selecting which mental model variations to explore
    def createSelectModels(self,pane):
        book = self.createcomponent('modelbook',(),None,Pmw.NoteBook,
                                    (self.pInterior(pane),))
        book.pack(fill=BOTH,expand=YES)

    def setupModels(self):
        """Configures model selection pane based on current selections"""
        book = self.component('modelbook')
        # add any new entities
        for entity in self.entities.members():
            if len(entity.models) == 0:
                continue
            try:
                page = book.add(entity)
            except ValueError:
                # Already have a page for this entity
                continue
            widget = Pmw.Group(page,tag_text='Select the model variations for this agent:')
            try:
                entry = self.models[entity]
            except KeyError:
                entry = self.models[entity] = {}
            # Add checkbuttons for each action
            for label,model in self.entities[entity].models.items():
                if not entry.has_key(label):
                    # Create new variable
                    var = BooleanVar()
                    entry[label] = {'variable':var,
                                    'model':model}
                # Create new button
                button = Checkbutton(widget.interior(),variable=var,
                                     text=label,anchor=W,justify='left')
                button.pack(fill=X,expand=YES)
                # Select by default
                var.set(1)
            widget.pack(fill=BOTH)

    def getModels(self):
        """Returns a dictionary of available models for each entity"""
        models = {}
        for entity in self.entities.members():
            if self.models.has_key(entity.name):
                models[entity.name] = []
                for label,entry in self.models[entity.name].items():
                    if entry['variable'].get():
                        models[entity.name].append(label)
            elif len(entity.models) > 0:
                models[entity.name] = []
        return models

    ## Pane for showing partial progress
        
    def createShowProgress(self,pane):
        pass

    def setupProgress(self,pane):
        """Set up the table of variations and the progress through them"""
        try:
            self.destroycomponent('progress')
        except KeyError:
            # Haven't created them yet (this must be the first time through)
            pass
        # Figure out what the columns look like
        columns = map(lambda n:(n,8),self.models.keys())
        columns.sort()
        self.columns = map(lambda c:{'type':'model',
                                     'name':c,
                                     'values':self.models[c]},columns)
        for msg in self.getMessages():
            columns.append((msg,16))
            self.columns.append({'type':'message',
                                 'name':msg,
                                 'values':[True,False]})
        for hearer in self.getHearers():
            label = '%s Hears' % (hearer)
            columns.append((label,12))
            self.columns.append({'type':'hearer',
                                 'name':'%s hears' % (hearer),
                                 'values':[True,False]})
        columns.append(('Status',6))
        # Create the listbox
        widget = self.createcomponent('progress',(),None,MultiListbox,
                                      (self.pInterior(pane),columns))
        widget.pack(fill='both',expand='yes')
        count = reduce(operator.mul,map(lambda c:len(c['values']) ,
                                        self.columns))
        for index in xrange(count):
            variation = self.getVariation(index)
            item = ['Pending']
            for column in self.columns:
                entry = variation[column['name']]
                if isinstance(entry,bool):
                    if entry:
                        entry = 'Yes'
                    else:
                        entry = 'No'
                item.insert(0,entry)
            self.root.after(10,lambda w=widget,i=item:w.insert(END,i))

    def getVariation(self,index):
        variation = {}
        for column in self.columns:
            subIndex = index % len(column['values'])
            variation[column['name']] = column['values'][subIndex]
            index /= len(column['values'])
        return variation        

    ## Pane for showing the results of the exploration
            
    def createShowResults(self,pane):
        self.createcomponent('Overall',(),None,Label,
                             (self.pInterior(pane),),
                             text='Overall Analysis').pack(fill=X,expand=YES)
        self.result = self.createcomponent('Results',(),None,
                                           Pmw.ScrolledText,
                                           (self.pInterior(pane),),
                                           usehullsize=1,
                                           hull_height=280)
        self.result.pack(fill=BOTH,expand=YES)
    
    def next(self):
        """Handle context-sensitive transitions from pane to pane"""
        WizardShell.next(self)
        last = self.sequence[self.pCurrent-1]
        phase = self.sequence[self.pCurrent]
        if phase == 'actions':
            self.setupActions()
        elif phase == 'models':
            self.setupModels()
        elif phase == 'progress':
            self.setupProgress(self.pCurrent)
            self.results = []
            thread = Thread(target=self.analyze)
            thread.start()
        elif phase == 'receiver':
            pass
        elif phase == 'messages':
            pass
##             if len(self.messages) == 0:
##                 # Hello.  I am a hack.
##                 entity = self.entities[self.entity]
##                 if entity.name == 'FirstResponder':
##                     theme = ('Specific',)
##                     self.messages.append(theme)
##                     theme = ('Average',)
##                     self.messages.append(theme)
##                     theme = ('General',)
##                     self.messages.append(theme)
##                 # Sorry for the interruption, we now return you to your
##                 # regulary scheduled high-quality programming
        elif phase == 'results':
            self.results.sort(lambda x,y:
                              cmp(x['count'],y['count']))
            content = ''
            for result in self.results:
                variation = self.getVariation(result['variation'])
                hearers = []
                for name in self.entities.keys():
                    try:
                        model = variation[name]
                        content += '%s: %s\n' % (name,model)
                    except KeyError:
                        pass
                    try:
                        if variation['%s hears' % (name)]:
                            hearers.append(name)
                    except KeyError:
                        pass
                msgList = []
                for msg in self.getMessages():
                    if variation[msg]:
                        msgList.append(msg)
                if len(msgList) > 0:
                    content += 'Messages: \n\t%s\n' % ('\n\t'.join(msgList))
                    if len(hearers) > 0:
                        content += 'Overheard by: '
                        content += ', '.join(hearers)
                        content += '\n'
                else:
                    content += 'No message\n'
                content += '\tViolations: %d\n\n' % (result['count'])
            self.result.settext(content)

    def describeObjective(self,value):
        if value < 0.0:
            return 'Fail'
        elif value < 0.2:
            return 'Neutral'
        else:
            return 'Succeed'
        
    def analyze(self):
        """Explore the selected variations and store results"""
        self.root.after(10,lambda w=self.nextB:w.__setitem__('state',DISABLED))
        count = reduce(operator.mul,map(lambda c:len(c['values']) ,
                                        self.columns))
        self.root.after(10,self.busyStart)
        for index in xrange(count):
            variation = self.getVariation(index)
            self.simulate(variation,index)
        self.root.after(10,self.busyEnd)
        self.root.after(10,lambda w=self.nextB:w.__setitem__('state',NORMAL))

    def changeStatus(self,index,status):
        """Changes status entry of the indexed row to be the given string"""
        self.root.after(100,lambda s=self,i=index,st=status:
                        s._changeStatus(i,st))

    def _changeStatus(self,index,status):
        item = self.component('progress').get(index)
        item[-1] = status
        self.component('progress').delete(index)
        self.component('progress').insert(index,item)

    def simulate(self,variation,index):
        """Simulates the result of the current configuration"""
        self.changeStatus(index,'Projecting')
        if len(self.models) > 0:
            sim = copy.deepcopy(self.entities)
        else:
            sim = self.entities
        messages = []
        hearers = []
        for column in self.columns:
            key = column['name']
            if column['type'] == 'model':
                sim[key].setModel(variation[key])
            elif column['type'] == 'message':
                if variation[key]:
                    messages.append(self.messages[key])
            elif column['type'] == 'hearer':
                if variation[key]:
                    hearers.append(key[:-6])
        self.processMsg(messages,hearers,index,sim)
        self.changeStatus(index,'Done')
            
    def processMsg(self,messages,hearers,index,sim=None):
        if sim == None:
            self.changeStatus(index,'Projecting')
            sim = copy.deepcopy(self.entities)
        self.changeStatus(index,'Sending')
        factors = []
        for msg in messages:
            factors.append({'topic':'state',
                            'lhs':['entities',msg['subject'],'state',
                                   msg['type']],
                            'value':msg['value'],
                            'relation':'='})
        message = Message({'factors':factors})
        receivers = self.getReceivers() + hearers
        violations = {'variation':index,'count':0,'total':0}
        for name in receivers:
            # Apply the message
            receiver = self.entities[name]
            beliefs = receiver.getAllBeliefs()
            if len(factors) > 0:
                delta,explanation = receiver.incorporateMessage(message)
                receiver.entities.applyChanges(delta,beliefs=beliefs)
            # Figure out what the agent will do
            self.changeStatus(index,'Evaluating')
            actions = receiver.actions.getOptions()
            decision,explanation = receiver.applyPolicy(beliefs,actions)
            violations[name] = decision
            # Identify any violations
            for action in decision:
                violations['total'] += len(self.entities.objectives)
                result = self.entities.detectViolations(action)
                for objective in result:
                    violations['count'] += 1
                    try:
                        violations[str(objective)] += 1
                    except KeyError:
                        violations[str(objective)] = 1
        self.results.append(violations)

    def done(self):
        self.quit()
        self.root.destroy()

if __name__ == '__main__':
        test = AnalysisWizard()
        test.run()
