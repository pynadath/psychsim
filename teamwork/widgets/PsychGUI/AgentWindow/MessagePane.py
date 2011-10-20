from Tkinter import Frame,Label
import Pmw
from teamwork.agent.stereotypes import Stereotyper
from teamwork.messages.PsychMessage import Message as PsychMessage
from teamwork.math.Keys import StateKey
from teamwork.math.KeyedVector import SetToConstantRow,UnchangedRow
from teamwork.math.KeyedMatrix import KeyedMatrix
from teamwork.math.probability import Distribution
from teamwork.widgets.pmfScale import PMFScale

class MessageFrame(Pmw.ScrolledFrame):
    resolution = 0.01
    
    def __init__(self,parent,entity,**kw):
        optiondefs = (
            ('send', lambda a,b,c,d,e,f:None, None),
            ('generic',False,Pmw.INITOPT),
            ('society',{},None),
            ('expert', 0, self.setExpert),
            ('balloon',None,Pmw.INITOPT),
            ('options',None,None),
            )
        self.defineoptions(kw, optiondefs)
        self.entity = entity
        self.message = {}
        Pmw.ScrolledFrame.__init__(self,parent)
        # Select the apparent sender of the message
        widget = self.createcomponent('sender',(),None,Pmw.OptionMenu,
                                      (self.interior(),),
                                      items=entity.getEntities(),
                                      labelpos='nw',
                                      label_text='Sender:')
        widget.pack(side='top',fill='x')
        # Select the subject of the message
        widget = self.createcomponent('subject',(),None,Pmw.OptionMenu,
                                      (self.interior(),),
                                      items=entity.getEntities(),
                                      labelpos='nw',
                                      command=self.selectSubject,
                                      label_text='Subject:')
        widget.pack(side='top',fill='x')
        # Select the statement type about that subject
        widget = self.createcomponent('type',(),None,Pmw.OptionMenu,
                                      (self.interior(),),
                                      labelpos='nw',
                                      command=self.selectType,
                                      label_text='Message Type:')
        widget.pack(side='top',fill='x')
        # Select the value to state
        widget = self.createcomponent('value',(),None,PMFScale,
                                      (self.interior(),),
                                      hull_bd=2,hull_relief='groove',
                                      hull_padx=5,hull_pady=5,
                                      distribution=Distribution({0.:1.}),
                                      usePIL=self['options'].get('Appearance','PIL') == 'yes',
                                      )
##        widget.scale.configure(command=widget._doCommand)
        widget.pack(side='top',fill='x')
        # Select the receiver of the message
        frame = Frame(self.interior())
        for other in entity.getEntityBeliefs():
            subframe = Frame(frame,relief='sunken',borderwidth=2)
            name = other.ancestry().replace('_','')
            # Create label for this agent
            widget = Label(subframe,text=other.name)
            widget.pack(side='left',fill='x',expand=1)
            name = other.name.replace('_','')
            # Create receive/overhear/none flag for this agent
            widget = self.createcomponent('%s Receiver' % (name),
                                          (),'receiver',Pmw.OptionMenu,
                                          (subframe,),
                                          menubutton_width=12,
                                          items=('Hears nothing',
                                                 'Receives',
                                                 'Overhears'))
            widget.configure(command=lambda val,s=self,n=name:\
                             s.receiver(n,val))
            widget.pack(side='left')
            rcvFlag = widget.getvalue()
            # Create force flag for this agent
            widget = self.createcomponent('%s Force' % (name),
                                          (),'force',Pmw.OptionMenu,
                                          (subframe,),
                                          menubutton_width=12,
                                          items=('Unforced',
                                                 'Must accept',
                                                 'Must reject'),
                                          menubutton_state='disabled')
            widget.pack(side='left')
            self.message[other.name] = {'receives':rcvFlag,
                                        'force':widget.getvalue()
                                        }
            subframe.pack(side='top',fill='x')
        frame.pack(side='top',fill='both')
        # Button box
        box = self.createcomponent('actions',(),None,Pmw.ButtonBox,
                                   (self.interior(),),orient='horizontal')
        # Send button
        widget = box.add('Send',command=self.send)
        widget = box.add('Add',command=self.add)
        widget = box.add('Query',command=self.query)
        widget = box.add('Evaluate',command=self.evaluate)
        if self['balloon']:
            self['balloon'].bind(box.component('Send'),'Simulate the communication of the current message from the specified sender to all of the hearers and overhearers')
            self['balloon'].bind(box.component('Add'),'Add the current message to the options for the agent to consider along with its current set of possible actions.')
            self['balloon'].bind(box.component('Query'),'Ask the sending agent to determine whether it perceives the message as being beneficial to send.')
            self['balloon'].bind(box.component('Evaluate'),'Simulate whether the message is really beneficial to the sender, using the ground truth model.')
        box.pack()
        if len(entity.getEntities()) > 0:
            widget = self.component('sender')
            if entity.name in widget.cget('items'):
                widget.invoke(entity.name)
            widget = self.component('subject')
            widget.invoke(entity.getEntities()[0])
        self.initialiseoptions()

    def setExpert(self):
        """Sets the expert mode on the value scale"""
        nameList = ['Add','Query','Evaluate']
        for index in range(len(nameList)):
            widget = self.component('actions_%s' % (nameList[index]))
            if self['expert']:
                widget.grid(column=index+2,row=0)
                widget.configure(state='disabled')
            else:
                widget.grid_forget()

    def selectSubject(self,name):
        """Callback for subject OptionMenu"""
        entity = self.entity.getEntity(name)
        self.subjects = {}
        self.contents = []
        # Messages about states
        itemList = entity.getStateFeatures()
        itemList.sort()
        for feature in itemList:
            label = 'has a %s value of ' % (feature)
            self.subjects[label] = len(self.contents)
            self.contents.append({'lhs':['entities','_subject',
                                         'state',feature],
                                  'topic':'state'})
        # Messages about observations
##        for action in entity.actions.getOptions():
##            cmd = lambda act:'%s %s' % (act['type'],act['object'])
##            label = 'did %s' % (string.join(map(cmd,action),' and '))
##            self.subjects[label] = len(self.contents)
##            self.contents.append({'action':action,
##                                  'actor':name,
##                                  'topic':'observation'})
        # Messages about mental models
        if isinstance(entity,Stereotyper):
            itemList = entity.models.keys()
            itemList.sort()
            for model in itemList:
                label = 'is %s' % (model)
                self.subjects[label] = len(self.contents)
                self.contents.append({'topic':'model',
                                      'entity':[name],
                                      'value':model})
        widget = self.component('type')
        itemList = self.subjects.keys()
        itemList.sort()
        widget.setitems(itemList)
        if len(self.subjects) > 0:
            widget.invoke()
        self.message['_subject'] = name

    def selectType(self,name):
        """Callback for statement type OptionMenu"""
        # Identify the subject of  the message
        widget = self.component('subject')
        entity = self.entity.getEntity(widget.getvalue())
        widget = self.component('value')
        content = self.contents[self.subjects[name]]
        if content['topic'] == 'state':
            widget.configure(state='normal')
            feature = name[6:-10]
            widget.configure(distribution=entity.getState(feature))
##            widget.configure(scale_from=-1)
##            widget.configure(color=1)
        elif content['topic'] in ['observation','model']:
            widget.configure(state='disabled')
##            widget.configure(scale_from=0)
##            widget.configure(color=0)
        else:
            raise NotImplementedError,'No callback for message of type %s' % \
                  content['topic']
        widget.setDistribution()
        self.message['_type'] = name

    def receiver(self,name,value):
        """Callback for selecting a receiver/overhearer"""
        widget = self.component('%s Force' % (name))
        if value == 'Hears nothing':
            widget.configure(menubutton_state='disabled')
        else:
            widget.configure(menubutton_state='normal')
            
    def extractMsg(self):
        """Constructs the Message object from the current widget state"""
        widget = self.component('sender')
        self.message['_sender'] = widget.getvalue()
        widget = self.component('value')
        self.message['_value'] = widget['distribution']
        receivers = []
        overhears = []
        for other in self.entity.getEntityBeliefs():
            widget = self.component('%s Receiver' % (other.name))
            value = widget.getvalue()
            self.message[other.name]['receives'] = value
            if value == 'Receives':
                receivers.append(other.name)
            elif value == 'Overhears':
                overhears.append(other.name)
            widget = self.component('%s Force' % (other.name))
            value = widget.getvalue()
            self.message[other.name]['force'] = value
        # Specialize the content to the selected field values
        factor = self.contents[self.subjects[self.message['_type']]]
        if factor['topic'] == 'state':
            factor['lhs'] = map(lambda s:s.replace('_subject',
                                                   self.message['_subject']),
                                factor['lhs'])
            factor['value'] = self.message['_value']
            factor['relation'] = '='
            # Create a linear representation of this belief change
            keyList = self.entity.entities.state.expectation().keys()
            distribution = self.component('value')['distribution']
            factor['matrix'] = Distribution()
            for element,prob in distribution.items():
                matrix = KeyedMatrix()
                for key in keyList:
                    matrix[key] = UnchangedRow(sourceKey=key)
                key = StateKey({'entity': self.message['_subject'],
                                'feature': factor['lhs'][-1]})
                matrix[key] = SetToConstantRow(sourceKey=key,
                                               value=element)
                matrix.fill(keyList)
                factor['matrix'][matrix] = prob
        elif factor['topic'] == ['observation']:
            # Nothing to do here?
            pass
        msg = PsychMessage({'factors':[factor]})
        for name in receivers+overhears:
            if self.message[name]['force'] == 'Must accept':
                msg.forceAccept(name)
            elif self.message[name]['force'] == 'Must reject':
                msg.forceReject(name)
        self.message['content'] = msg
        self.message['receivers'] = receivers
        self.message['overhearers'] = overhears
        return self.message
        
    def send(self):
        self.extractMsg()
        self['send'](self.message['_sender'],self.message['receivers'],
                    self.message['_subject'],self.message['content'],
                    'none',self.message['overhearers'])

    def evaluate(self):
        msg = self.extractMsg()
        self['send'](self.message['_sender'],self.message['receivers'],
                     self.message['_subject'],self.message['content'],
                     'none',self.message['overhearers'],'objective')

    def add(self):
        """Adds the specified message to the decision space of the entity"""
        msg = self.extractMsg()
        self.entity.actions.directAdd([msg])
        
    def query(self):
        msg = self.extractMsg()
        self['send'](self.message['_sender'],self.message['receivers'],
                     self.message['_subject'],self.message['content'],
                     'none',self.message['overhearers'],'subjective')

    def seedMessage(self,msg):
        """Sets up the menus to send the specified message"""
        self.component('sender').invoke(msg['sender'])
        self.component('subject').invoke(msg['subject'])
        # Set the state features selector
        for index in range(len(self.contents)):
            content = self.contents[index]
            if content['topic'] == 'state' and len(content['lhs']) == 4 \
               and content['lhs'][1] == '_subject' \
               and content['lhs'][3] == msg['type']:
                self.component('type').invoke(index)
                break
        else:
            # Shouldn't happen
            print 'Unable to find message type:',msg['type']
        self.component('value').updateNew(msg['value'])
        self.component('value').update()
        # Update receivers/overhearers
        for name in self.components():
            if self.componentgroup(name) == 'receiver':
                if name[:-9] == msg['receiver']:
                    self.component(name).invoke('Receives')
                else:
                    self.component(name).invoke('Hears nothing')
                    
                    
