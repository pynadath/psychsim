import string
from Tkinter import *
import tkMessageBox
import Pmw
from teamwork.widgets.cookbook import MultiListbox

class ThemeSel:
    commonFields = ['sequence','actor','action','recipient']
    msgFields = ['themes','messageSubj','message','force','overhear']
    cmdFields = ['comact','comrecipient']
    msgTypes = {'InevitableDefeat' : ['Powerful', 'PunishViolence',
                                      'SupportCortinaGov', 'SupportRCNG',
                                      'SupportRCNGandGov','Weak'],
                'PoorSupportGovt': ['SupportCortinaGov',
                                    'SupportRCNG',
                                    'SupportRCNGandGov'],
                'BombingHurtsInnocents':[],
                'GovtPower': ['Powerful'],
                'Integrity' : ['Professional']}
    labels = {'sequence':'Time',
              'actor':'Actor',
              'action':'Action',
              'recipient':'Target',
              'themes':'Theme',
              'messageSubj':'Msg Subj',
              'message':'Msg Verb',
              'force':'Force',
              'overhear':'Overheard',
              'comact':'Cmd Verb',
              'comrecipient':'Cmd Obj'}

    
    def __init__(self, parent, entities=None,balloon=None):
        # Create and pack the widget to be configured.
        #self.target = Label(self,
        #       relief = 'sunken',
        #                padx = 2,
        #       pady = 1,
        # )
        #         self.target.pack(fill=X, padx = 2, pady = 0)
        self.frame = parent
        srcs = map(lambda e:e.name,entities.members())
        self.entities = entities
        group = Pmw.Group(parent,tag_text='New campaign item:')
        self.boxes = {}
        for field in self.commonFields+self.msgFields+self.cmdFields:
            box = Pmw.OptionMenu(group.interior(),labelpos='nw',
                                 label_text=self.labels[field]+':',
                                 menubutton_width=8,
                                 command=lambda str,s=self,f=field:\
                                 s.change(f,str))
            box.pack(side = 'left', anchor = 'n',padx = 0, pady = 0)
            if not field in self.commonFields:
                box.pack_forget()
            if field == 'sequence':
                itemList = map(lambda i:entities.time['macro']+i,range(1,6))
                box.setitems(itemList)
                box.configure(menubutton_width=1)
            elif field == 'force':
                box.configure(menubutton_width=5)
                box.setitems(['none','accept','reject'])
            elif field == 'actor':
                box.setitems(['']+srcs)
            elif field == 'overhear':
                box.setitems(['']+srcs)
            elif field == 'themes':
                box.configure(menubutton_width = 12)
            self.boxes[field] = box
        group.pack(side=TOP,fill=X,expand=1)
        # Display the first colour.

        #def changeColour(self, colour):
        # self.target.configure(background = colour)
        box = Pmw.ButtonBox(parent)
        label = 'Add'
        box.add(label,command=self.addItem)
        if balloon:
            balloon.bind(box.button(label),
                         'Add the above action/message to the current '\
                         +'campaign below')
        label = 'Remove'
        box.add(label,command=self.removeItems)
        if balloon:
            balloon.bind(box.button(label),
                         'Remove the action/message selected below from '\
                         +'the current campaign')
        box.pack(side=TOP,fill=X,expand=1)
        lists = []
        for i in range(len(self.commonFields)):
            l = self.labels[self.commonFields[i]]
            if l == 'sequence':
                lists.append((l,5))
            else:
                lists.append((l,10))
        for i in range(len(self.msgFields)):
            l = self.labels[self.msgFields[i]]
            try:
                l += '/'+self.labels[self.cmdFields[i]]
            except IndexError:
                pass
            if string.lower(l) == 'force':
                lists.append((l,2))
            else:
                lists.append((l,10))
        self.list = MultiListbox(parent,lists)
        self.list.pack(side=TOP,expand=1,fill=BOTH)
        self.campaign = []

    def change(self,field,value):
        if field == 'actor':
            # Update menus based on selection of actor
            if len(value) == 0:
                actList = ['']
            else:
                try:
                    entity = self.entities[value]
                except KeyError:
                    tkMessageBox.showerror('Unknown entity',
                                           'I do not know any entity named "%s"'\
                                           % (value))
                    entity = None
                    actList = ['']
                if entity:
                    actList = ['','message']
                    for act in entity.actions:
                        if not act['type'] in actList:
                            actList.append(act['type'])
            field = 'action'
            self.boxes[field].setitems(actList)
            self.boxes[field].invoke(actList[0])
        elif field == 'action':
            # Update menus based on selection of action type
            name = self.boxes['actor'].getvalue()
            try:
                entity = self.entities[name]
            except KeyError:
                entity = None
            if entity and value == 'message':
                # Update possible target audiences
                targetList = self.entities.members()
                targetList.remove(entity)
                targetList = ['']+map(lambda e:e.name,targetList)
                # Update displayed fields
                for field in self.cmdFields:
                    self.boxes[field].pack_forget()
                for field in self.msgFields:
                    self.boxes[field].pack(side = 'left', anchor = 'n',
                                           expand = 0, padx = 0, pady = 0)
            elif entity:
                # Update list of possible targets of this command/action
                targetList = []
                for act in entity.actions:
                    if act['type'] == value and not act['object'] in targetList:
                        targetList.append(act['object'])
                if len(targetList) > 1:
                    targetList = [''] + targetList
                elif len(targetList) == 0:
                    targetList.append('')
                # Update displayed fields
                for field in self.msgFields:
                    self.boxes[field].pack_forget()
                for field in self.cmdFields:
                    if value == 'command':
                        self.boxes[field].pack(side = 'left', anchor = 'n',
                                               expand = 0, padx = 0, pady = 0)
                    else:
                        self.boxes[field].pack_forget()
            else:
                targetList = ['']
            self.boxes['recipient'].setitems(targetList)
            self.boxes['recipient'].invoke(targetList[0])
        elif field == 'recipient':
            if self.boxes['action'].getvalue() == 'message':
                # Update theme menu based on target
                if len(value) == 0:
                    themeList = ['']
                else:
                    try:
                        entity = self.entities[value]
                    except KeyError:
                        msg = 'I do not know an entity named "%s"'% (value)
                        tkMessageBox.showerror('Unknown entity',msg)
                        return
                    try:
                        entity.susceptibilities
                    except AttributeError:
                        entity.susceptibilities = []
                    if len(entity.susceptibilities) == 0:
                        msg = 'I do not know the susceptibilities of PTA '+\
                              value+'.  I will use my default list of '+\
                              'themes for now, but query susceptibility '+\
                              'agent for more specific information.'
                        tkMessageBox.showwarning('Warning',msg)
                        themeList = self.entities.themes.keys()
                    else:
                        themeList = map(lambda i:i[0],entity.susceptibilities)
                self.boxes['themes'].setitems(themeList)
                self.boxes['themes'].invoke(themeList[0])
            elif self.boxes['action'].getvalue() == 'command':
                # Update command menus based on commandee
                actList = []
                name = self.boxes['actor'].getvalue()
                try:
                    entity = self.entities[name]
                except KeyError:
                    actList.append('')
                    entity = None
                if entity:
                    for act in entity.actions:
                        if act['type'] == 'command' and act['object'] == value:
                            act = act['command']
                            if not act['type'] in actList:
                                actList.append(act['type'])
                    if len(actList) > 1:
                        actList.insert(0,'')
                self.boxes['comact'].setitems(actList)
                self.boxes['comact'].invoke(actList[0])
        elif field == 'comact':
            # Update object of commanded action in response to action type
            objList = []
            name = self.boxes['actor'].getvalue()
            try:
                entity = self.entities[name]
            except KeyError:
                entity = None
            name = self.boxes['recipient'].getvalue()
            try:
                commandee = self.entities[name]
            except KeyError:
                entity = None
            if entity:
                for act in entity.actions:
                    if act['type'] == 'command' and act['object'] == name \
                           and act['command']['type'] == value:
                        if not act['command']['object'] in objList:
                            objList.append(act['command']['object'])
                if len(objList) > 1:
                    objList.insert(0,'')
                elif len(objList) == 0:
                    objList.append('')
            else:
                objList.append('')
            self.boxes['comrecipient'].setitems(objList,0)
            self.boxes['comrecipient'].invoke(objList[0])
        elif field == 'themes':
            # Update message subject and verb fields based on theme
            srcs = map(lambda e:e.name, self.entities.members())
            try:
                self.boxes['message'].setitems(self.msgTypes[value])
                self.boxes['messageSubj'].setitems(['']+srcs)
            except KeyError:
                self.boxes['message'].setitems([''])
                self.boxes['messageSubj'].setitems([''])
            self.boxes['messageSubj'].invoke('')
        else:
##            print field,value
            pass
        
    def addItem(self):
        """Takes the item currently indicated by the option menus and
        adds it to the current campaign"""
        label = ''
        item = ()
        error = None
        itemType = self.boxes['action'].getvalue()
        fieldList = self.commonFields[:]
        if itemType == 'message':
            fieldList += self.msgFields
        elif itemType == 'command':
            fieldList += self.cmdFields
        for field in fieldList:
            value = self.boxes[field].getvalue()
            item += (value,)
            if len(value) > 0:
                label += field+':'+value + '; '
            elif not field in ['force','overhear']:
                if field == 'recipient':
                    if self.boxes['action'].getvalue() != 'wait':
                        error = 1
                elif field == 'comrecipient':
                    if self.boxes['comact'].getvalue() != 'wait':
                        error = 1
                else:
                    error = 1
            if error:
                break
        if error:
            tkMessageBox.showwarning('Warning',
                                     'You have not specified the '+field)
        else:
            if label in self.campaign:
                tkMessageBox.showwarning('Warning',
                                         'You have already added that action')
            else:
                self.campaign.append(label)
                while len(item) < len(self.commonFields)+len(self.msgFields):
                    item += ('',)
                self.list.insert(END,item)
##                self.list.setlist(self.campaign)
                # Should we reset the pulldown menus?

    def removeItems(self):
        for index in self.list.curselection():
            if len(index) > 0:
                index = int(index)
                del(self.campaign[index])
                self.list.delete(index)
                break
##         self.list.setlist(self.campaign)

    def getCampaign(self):
        result = []
        for item in self.campaign:
            action = {}
            fields = string.split(item,'; ')
            for pair in fields:
                if len(pair) > 0:
                    entry = string.split(pair,':')
                    action[entry[0]] = entry[1]
            result.append(action)
        return result




