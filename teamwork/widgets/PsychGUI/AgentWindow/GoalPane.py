from Tkinter import Frame
import tkMessageBox
import Pmw
from teamwork.math.Keys import StateKey,ActionKey
from teamwork.widgets.pmfScale import PMFScale
from teamwork.widgets.images import loadImages,makeButton
from teamwork.reward.goal import PWLGoal,maxGoal,minGoal
from teamwork.agent.Generic import GenericModel
from teamwork.widgets.TreeBuilder import TreeBuilder

class GoalFrame(Pmw.ScrolledFrame):
    resolution = 0.01
    
    def __init__(self,parent,entity,balloon,**kw):
        self.selected = None
        optiondefs = (
            ('balloon',None,Pmw.INITOPT),
            ('society',None,None),
            ('expert',0,self.setExpert),
            ('generic',False,None),
            ('options',None,None),
            )
        self.defineoptions(kw, optiondefs)
        self.normalizing = {}
        self.entity = entity
        self.features = {}
        Pmw.ScrolledFrame.__init__(self,parent)
        self.images = loadImages({'del': 'icons/trophy--minus.gif',
                                  'new': 'icons/trophy--plus.gif',
                                  'lock': 'icons/lock.gif',
                                  'unlock': 'icons/lock-unlock.gif',},
                                 self['options'].get('Appearance','PIL') == 'yes')
        self.interior().grid_columnconfigure(0,weight=1)
        # Toolbar
        toolbar = self.createcomponent('toolbar',(),None,Frame,(self.interior(),),
                                       bd=2,relief='raised')
        toolbar.grid(row=0,column=0,sticky='ew')
        if self['generic']:
            # Button for adding new goal
            button = makeButton(toolbar,self.images,'new',
                                self.promptNew,'+')
            button.pack(side='left',ipadx=5,ipady=3)
            if self['balloon']:
                self['balloon'].bind(button,'Add new goal')
            # Button for deleting goal
            button = makeButton(toolbar,self.images,'del',
                                self.delete,'-')
            button.pack(side='left',ipadx=5,ipady=3)
            if self['balloon']:
                self['balloon'].bind(button,'Delete selected goal')
        # Button for normalizing
        button = makeButton(toolbar,self.images,'lock',self.lock,'lock',self,'lock','<Double-Button-1>')
        button.pack(side='right',ipadx=5,ipady=3)
        if self['balloon']:
            self['balloon'].bind(button,'Control normalization of goal weights')
        # Sliders for goal weights
        if len(entity.goals) == 0:
            normalize = True
        else:
            normalize = abs(sum(entity.goals.values())-1.)<1e-8
        widget = self.createcomponent('scale',(),None,PMFScale,(self.interior(),),
                                      distribution=entity.goals,editable=False,
                                      expand=self.expand,
                                      collapse=self.collapse,
                                      normalize=normalize,
                                      viewprobs=True,floatdomain=False,
                                      usePIL=self['options'].get('Appearance','PIL') == 'yes',
                                      select=self.select,deleteIfZero=False)
        widget.grid(row=1,column=0,sticky='news')
        self.initialiseoptions()

    def promptNew(self,event=None):
        try:
            dialog = self.component('dialog')
        except KeyError:
            dialog = self.createDialog()
        # Set up the possible entity references for the new goal
        options = self['society'].keys()
        options.sort()
        options.append('self')
        if isinstance(self.entity,GenericModel):
            options += self.entity.getRelationships()
        else:
            options += self.entity.relationships.keys()
        if len(options) == 0:
            raise UserWarning,self.entity.ancestry()
        dialog.component('entity_listbox').delete(0,'end')
        for option in options:
            dialog.component('entity_listbox').insert('end',option)
        dialog.component('feature').configure(menubutton_state='normal')
        dialog.activate()
        
    def setState(self,state='normal'):
        for name in self.components():
            if 'Goal' in name:
                self.component(name).configure(state=state)

    def invert(self):
        widget = self.component('scale')
        label = widget.deleteScale()
        for goal in self.entity.getGoals():
            if str(goal) == label:
                break
        else:
            raise KeyError,'Agent %s has no goal %s' % \
                  (self.entity.ancestry(),label)
        weight = self.entity.goals[goal]
        del self.entity.goals[goal]
        if goal.direction == 'min':
            direction = 'max'
        else:
            direction = 'min'
        goal = goal.__class__(goal.entity,direction,goal.type,
                              goal.key,goal.value)
        goal.weight = weight
        self.entity.setGoalWeight(goal,weight,False)
        self.recreate_goals()
        widget.reorder()
        widget.component('select%s' % (goal.key)).invoke()
        
    def lock(self,event=None):
        if str(event.widget.cget('image')) == str(self.images['lock']):
            self.component('scale').configure(normalize=False)
            event.widget.configure(image=self.images['unlock'])
        else:
            # We're locking up, so normalize first
            self.entity.normalizeGoals()
            self.recreate_goals()
            event.widget.configure(image=self.images['lock'])
            self.component('scale').configure(normalize=True)
        
    def recreate_goals(self):
        """Redraws all of the goal widgets"""
        widget = self.component('scale')
        disabled = widget.cget('state') == 'disabled'
        widget.configure(state='normal')
        widget.configure(distribution=self.entity.goals)
        if disabled:
            widget.configure(state='disabled')

    def setExpert(self):
        """Updates the display in response to the current expert mode"""
        pass
        
    def selectEntity(self,name=None):
        if not name:
            name = self.component('dialog_entity').get()
            if not name:
                return
        self.features = {}
        if name == 'self':
            eList = [self.entity.name]
        else:
            if isinstance(self.entity,GenericModel):
                remaining = self.entity.ancestors()
            else:
                remaining = [self.entity.name]
            for agent in remaining:
                try:
                    eList = self['society'][agent].relationships[name][:]
                    break
                except KeyError:
                    pass
            else:
                eList = [name]
        if isinstance(self.entity,GenericModel):
            while len(eList) > 0:
                entity = self['society'][eList.pop()]
                features = entity.getStateFeatures()
                if self.component('dialog_direction').getvalue().lower() != 'complex':
                    features.append(PWLGoal.goalFeature)
                for feature in features:
                    if not self.features.has_key(feature):
                        self.features[feature] = {'type':'state',
                                                  'key':feature}
                for option in entity.actions.getOptions():
                    for action in option:
                        if not self.features.has_key(action['type']):
                            entry = {'type':'actActor',
                                     'key':action['type']}
                            self.features[action['type']] = entry
                eList += entity.parentModels
        elif self['society']:
            for feature in self['society'][name].getStateFeatures():
                self.features[feature] = {'type':'state','key':feature}
        features = self.features.keys()
        features.sort(lambda x,y: cmp(x.lower(),y.lower()))
        self.component('dialog_feature_menu').delete(0,'end')
        self.component('dialog_feature').setitems(features)
        if len(features) > 0:
            self.component('dialog_feature').invoke(features[0])
        
    def add(self,button='OK'):
        self.component('dialog').deactivate()
        if button == 'OK':
            direction = self.component('dialog_direction').getvalue().lower()
            entity = self.component('dialog_entity').get()
            feature = self.features[self.component('dialog_feature').getvalue()]
            if len(feature) == 0:
                tkMessageBox.showerror('No Feature','The selected entity has no state features to min/maximize.')
                return
            if feature['type'] == 'state':
                key = StateKey({'entity': entity, 'feature': feature['key']})
            elif feature['type'] == 'actActor':
                key = ActionKey({'entity': entity, 'type': feature['key'],
                                 'object': None})
            else:
                raise NotImplementedError,'Unable to put goals on %s' % \
                (feature['type'])
            if direction == 'complex':
                goal = PWLGoal()
                goal.keys.append(key)
            elif direction == 'minimize':
                goal = minGoal(key)
            else: # direction == 'maximize':
                goal = maxGoal(key)
            for other in self.entity.getGoals():
                if goal.keys == other.keys:
                    msg = '%s already has a goal for %s' % \
                        (self.entity.ancestry(),','.join(map(str,(goal.keys))))
                    tkMessageBox.showerror('Goal exists',msg)
                    break
            else:
                if len(self.entity.getGoals()) == 0:
                    self.entity.setGoalWeight(goal,1.,False)
                else:
                    self.entity.setGoalWeight(goal,0.,False)
                self.component('scale').setDistribution()

    def createDialog(self):
        # Draw the goal adding box
        palette = Pmw.Color.getdefaultpalette(self.interior())
        dialog = self.createcomponent('dialog',(),None,Pmw.Dialog,
                                      (self.interior(),),
                                      buttons=('OK','Cancel'),
                                      command=self.add,defaultbutton=0)
        dialog.withdraw()
        options = ['Maximize','Minimize','Complex']
        widget = dialog.createcomponent('direction',(),'New Goal',
                                        Pmw.OptionMenu,(dialog.interior(),),
                                        items=options,
                                        menubutton_width=max(map(len,options)),
                                        labelpos='nw',label_text='Direction:')
        widget.pack(side='left',pady=10,padx=10)
        widget = dialog.createcomponent('entity',(),'New Goal',
                                        Pmw.ComboBox,(dialog.interior(),),
                                        labelpos='nw',label_text='Entity:',
                                        entry_state='disabled',
                                        entry_disabledforeground=palette['foreground'],
                                        entry_disabledbackground=palette['background'],
                                        selectioncommand=self.selectEntity,
                                      )
        widget.pack(side='left',fill='x',expand='yes')
        widget = dialog.createcomponent('feature',(),'New Goal',
                                        Pmw.OptionMenu,
                                        (dialog.interior(),),
                                        labelpos='nw',
                                        label_text='Feature:')
        widget.pack(side='left',fill='x',expand='yes')
        return dialog

    def expand(self,goal,frame):
        table = {}
        for condition,tree,cache in goal.dependency:
            table[str(condition)] = {'actions': condition, 'tree': tree}
        tree = self.createcomponent(str(goal),(),'Editor',TreeBuilder,
                                    (frame,),society=self['society'],
                                    orient='horizontal',expert=True,
                                    key=goal.toKey(),font=('Helvetica',10),
                                    treeWidth=250,new=self.newDependency,
                                    delete=lambda d,s=self,g=goal:
                                        s.delDependency(g,d),
                                    table=table)
        tree.pack(side='left',fill='both',expand='yes')

    def collapse(self,goal):
        self.destroycomponent(str(goal))

    def newDependency(self,key,condition,tree):
        """Callback when a new action dependency is created
        """
        for goal in self.entity.getGoals():
            if goal.keys == [key]:
                break
        else:
            raise NameError,'Unable to find goal on %s' % (str(key))
        goal.addDependency(condition,tree)

    def delDependency(self,goal,dependency):
        for index in range(len(goal.dependency)):
            condition,tree,cache = goal.dependency[index]
            if condition == dependency['actions']:
                del goal.dependency[index]
                break
        else:
            raise ValueError,'Unable to find deleted goal dependency: %s' \
                % (str(condition))

    def select(self,name):
        self.selected = name

    def delete(self,event=None):
        if self.selected is None:
            tkMessageBox.showerror('No Selection','Please select a goal to delete.')
        else:
            del self.entity.goals[self.selected]
            self.entity.goals.normalize()
            self.component('scale').setDistribution()
