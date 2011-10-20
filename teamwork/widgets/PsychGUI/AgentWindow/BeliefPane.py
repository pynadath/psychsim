from Tkinter import Frame
import Pmw
import tkMessageBox
from teamwork.math.Keys import ModelKey
from teamwork.widgets.TreeWidget import EasyTree
from teamwork.math.probability import Distribution
from teamwork.widgets.pmfScale import PMFScale
from teamwork.widgets.images import loadImages,makeButton

class BeliefFrame(Pmw.ScrolledFrame):
    """Frame for viewing recursive beliefs
    """
    
    def __init__(self,parent,entity,**kw):
        self.entity = entity
        self.activeBelief = None
        optiondefs = (
            ('balloon',None,Pmw.INITOPT),
            ('generic',False,Pmw.INITOPT),
            ('expert', False,None),
            ('orient','horizontal',Pmw.INITOPT),
            ('society',{},None),
            ('window',Frame,None), # Class used for individual agent windows
            ('hypoCmd',None,None),
            ('options',None,None),
            )
        self.defineoptions(kw, optiondefs)
        Pmw.ScrolledFrame.__init__(self,parent)
        self.images = loadImages({'minus': 'icons/users--minus.gif',
                                  'add': 'icons/users--plus.gif',
                                  'auto': 'icons/users--arrow.gif',
                                  },
                                 self['options'].get('Appearance','PIL') == 'yes')
        self.interior().grid_columnconfigure(0,weight=1)
        self.interior().grid_rowconfigure(1,weight=1)
#        if not self['generic']:
        # Toolbar
        self.createcomponent('toolbar',(),None,Frame,(self.interior(),),
                             bd=2,relief='raised').grid(row=0,sticky='ew')
        # Button for adding mental model
        widget = makeButton(self.component('toolbar'),self.images,'add',
                            self.newModel,'+')
        widget.pack(side='left',ipadx=5,ipady=5)
        if self['balloon']:
            self['balloon'].bind(widget,'Add candidate mental model.')
        # Button for generating mental model space
        widget = makeButton(self.component('toolbar'),self.images,'auto',
                            self.generate,'Auto')
        widget.pack(side='left',ipadx=5,ipady=5)
        if self['balloon']:
            self['balloon'].bind(widget,'Generate mental model space.')
        # Belief display
        frame = self.createcomponent('panes',(),None,Pmw.PanedWidget,
                             (self.interior(),),orient='horizontal')
        frame.add('browser', size=200)
        frame.add('display', min=.1)
        self.component('panes_display').grid_columnconfigure(0,weight=1)
        self.component('panes_display').grid_rowconfigure(1,weight=1)
        browser = self.createcomponent('tree',(),None,EasyTree,
                                       (self.component('panes_browser'),),
                                       font=('Helvetica', 12),
                                       root_label='%s believes:' % \
                                       entity.name,
                                       action=None)
        browser.inhibitDraw = True
        # Populate entity selector tree
        entities = entity.getEntityBeliefs()
        entities.sort(lambda x,y: cmp(x.name,y.name))
        remaining = map(lambda e:(e,browser.easyRoot),entities)
        while len(remaining) > 0:
            belief,node = remaining.pop(0)
            entities = belief.getEntityBeliefs()
            entities.sort(lambda x,y: cmp(x.name,y.name))
            subnode = node.addChild(browser,belief.name,isLeaf=len(entities)==0)
            subnode['action'] = lambda h,ev,s=self,e=belief: s.beliefentitywin(h,e,0)
            remaining += map(lambda e:(e,subnode),entities)
        browser.pack(side='top',expand='yes',fill='both')
        browser.inhibitDraw = False
        browser.root.expand()
        self.initialiseoptions()
        frame.setnaturalsize()
        frame.grid(row=1,sticky='ewns')
        
    def beliefentitywin(self, h, entity, path=''):
        # Hide the previous belief window
        if self.activeBelief and entity.ancestry() != self.activeBelief.ancestry():
            old = self.component('%s_notebook' % (self.activeBelief.ancestry()))
            old.grid_forget()
        # Mental model scale
        try:
            widget = self.component('scale')
        except KeyError:
            widget = self.createcomponent('scale',(),None,PMFScale,
                                          (self.component('panes_display'),),
                                          viewprobs=True,floatdomain=False,
                                          usePIL=self['options'].get('Appearance','PIL') == 'yes',
                                          select=self.setModel,command=self.updateBelief)
        self.update(entity)
        # Create a new belief window
        try:
            pane = self.component(entity.ancestry())
        except KeyError:
            pane = self.createcomponent(entity.ancestry(),(),None,self['window'],
                                        (self.component('panes_display'),),
                                        entity=entity,society=self['society'],
                                        window=None,
                                        expert=self['expert'],
                                        balloon=self['balloon'],
                                        abstract=self['generic'],
                                        hypoCmd=self['hypoCmd'],
                                        options=self['options'],
                                        )
            entity.attributes['window'] = pane
        # Show the new belief window
        pane.component('notebook').grid(row=1,sticky='ewns',padx=10,pady=10)
        self.activeBelief = entity
        if len(widget['distribution'].domain()) > 0:
            widget.grid(row=0,sticky='ew')
        else:
            widget.grid_forget()
        self.setExpert(entity)

    def setExpert(self,entity=None):
        for component in self.components():
            if self.componentgroup(component) == 'agent':
                self.component(component).configure(expert=self['expert'])

    def newModel(self,event=None):
        if self.activeBelief is None:
            tkMessageBox.showerror('No selection','Please select an entity to whom to add the mental model.')
            return
        else:
            keys = []
            for key in self.activeBelief.models.keys():
                try:
                    keys.append(int(key))
                except ValueError:
                    pass
            if keys:
                new = str(max(keys)+1)
            else:
                new = '0'
            if self.activeBelief.models:
                value = 0.
            else:
                value = 1.
            self.activeBelief.newModel(new)
            self.component('scale').addElement(new,value)
            self.component('scale').grid(row=0,sticky='ew')
            self.component('scale_elem0').select_range(0,'end')
            self.setModel(new)

    def destroy(self):
        # This is an annoying bug
        self.component('panes').unbind('<Configure>')
        Pmw.ScrolledFrame.destroy(self)
            
    def setModel(self,model):
        """Sets the mental model of the active recursive belief and updates the display
        """
        if self.activeBelief is None:
            tkMessageBox.showerror('No selection','Please select an entity to whom to add the mental model.')
            return
        else:
            self.activeBelief.setModel(model)
            self.component(self.activeBelief.ancestry()).update()
            
    def updateBelief(self,widget,value=None):
        if value is None:
            value = widget['distribution']
        entity = self.activeBelief.parent
        old = self.activeBelief.models.keys()
        new = []
        for name in widget['distribution'].domain():
            if self.activeBelief.models.has_key(name):
                old.remove(name)
            else:
                new.append(name)
        if old:
            assert len(old) == 1
            if len(new) == len(old):
                self.activeBelief.models[new[0]] = self.activeBelief.models[old[0]]
                self.activeBelief.setModel(new[0])
            del self.activeBelief.models[old[0]]
        entity.setModelBeliefs(self.activeBelief.name,value)

    def update(self,entity=None):
        if entity is None:
            entity = self.activeBelief
        if entity:
            key = ModelKey({'entity': entity.name})
            prob = Distribution()
            try:
                marginal = entity.parent.beliefs['models'].getMarginal(key)
            except KeyError:
                marginal = None
            if marginal:
                for name,model in entity.models.items():
                    prob[name] = marginal[model['value']]
            self.component('scale').configure(distribution=prob)
    
    def generate(self,event=None):
        """
        Auto-generate mental model space
        """
        if self.activeBelief is None:
            tkMessageBox.showerror('No selection','Please select an entity to auto-generate mental models for.')
            return
        elif not self.activeBelief.parent is self.entity:
            tkMessageBox.showerror('Invalid selection','Please select only direct children of this entity.')
            return
        real = self.entity.world[self.activeBelief.name]
        real.getEstimator(self.entity.world)
        real.generateModels()
        self.activeBelief.models.clear()
        self.activeBelief.models.update(real.models)
        distribution = self.activeBelief.beliefs['entities'].state
        belief = self.activeBelief.beliefs['entities'].state2world(distribution)
        model = self.activeBelief.findBelief(belief)
        # Create mental models
        key = ModelKey({'entity': real.name})
        prob = Distribution()
        for other in self.activeBelief.models.values():
            if other['name'] == model['name']:
                prob[other['value']] = 1.
            else:
                prob[other['value']] = 0.
        self.entity.beliefs['models'].join(key,prob)
        self.component('scale').grid(row=0,sticky='ew')
        self.update()

