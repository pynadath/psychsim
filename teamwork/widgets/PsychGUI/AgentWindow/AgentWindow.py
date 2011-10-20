#from Tkinter import *
import tkMessageBox
import Pmw
from teamwork.agent.GoalBased import GoalBasedAgent
from teamwork.agent.stereotypes import Stereotyper
from teamwork.widgets.MultiWin import InnerWindow
from PropertyPane import PropertyFrame
from StatePane import StateFrame
from GoalPane import GoalFrame
from BeliefPane import BeliefFrame
from MentalModelPane import MentalModelFrame
from PolicyPane import PolicyFrame
from ActionPane import ActionFrame
from MessagePane import MessageFrame
from ObservationPane import ObservationFrame
from RelationshipPane import RelationFrame
from teamwork.widgets.images import loadImages

class AgentWin(Pmw.MegaArchetype):
    """Widget for displaying an agent

    The following panes have separate widgets:
       - L{General<PropertyFrame>}
       - L{State<StateFrame>}
       - L{Actions<ActionFrame>}
       - L{Goals<GoalFrame>}
       - L{Observations<ObservationFrame>}
       - L{Beliefs<BeliefFrame>}
       - L{Mental Models<MentalModelFrame>}
       - L{Policy<PolicyFrame>}
       - L{Messages<MessageFrame>}
       - L{Relationships<RelationshipPane>}
    """
    
    agtHeight = 700
    agtWidth = 750

    def __init__(self, frame, **kw):
        optiondefs = (
            ('entity', None, Pmw.INITOPT),
            ('society',{},Pmw.INITOPT),
            ('x', 0, Pmw.INITOPT),
            ('y', 0, Pmw.INITOPT),
            ('balloon',None, Pmw.INITOPT),
            ('actCmd',lambda x,y:{},Pmw.INITOPT),
            ('msgCmd',lambda v,w,x,y,z: {},Pmw.INITOPT),
            ('policyCmd',None,Pmw.INITOPT),
            ('hypoCmd',None,Pmw.INITOPT),
            ('stepCmd',None,Pmw.INITOPT),
            ('valueCmd',None,Pmw.INITOPT),
            ('abstract',None,Pmw.INITOPT),
            ('expert',0,self.setExpert),
            ('beta',False,Pmw.INITOPT),
            ('destroycommand',None,Pmw.INITOPT),
            ('options',None,None),
            # Flag for whether we should create an entire InnerWindow
            ('window',True,Pmw.INITOPT),
            )
        self.defineoptions(kw,optiondefs)
        Pmw.MegaArchetype.__init__(self,frame)
        self.images = loadImages({'General': 'icons/home.gif',
                                  'State': 'icons/globe-green.gif',
                                  'Actions': 'icons/hammer-screwdriver.gif',
                                  'Goals': 'icons/trophy.gif',
                                  'Observations': 'icons/binocular.gif',
                                  'Beliefs': 'icons/users.gif',
                                  'Policy': 'icons/traffic-light.gif',
                                  'Messages': 'icons/balloon.gif',
                                  'Relationships': 'icons/chain.gif',
                                  },
                                 self['options'].get('Appearance','PIL') == 'yes')
        self.paneSpecs = \
            {'General': {'type': 'General','widget': PropertyFrame},
             'State': {'type': 'State','widget': StateFrame,'tag':'S'},
             'Actions': {'type': 'Actions','widget': ActionFrame,'tag':'A'},
             'Goals': {'type': 'Goals','widget': GoalFrame,'tag':'R'},
             'Observations': {'type': 'Observations','tag':u'\u03A9',
                              'widget': ObservationFrame},
             'Beliefs': {'type': 'Beliefs','widget': BeliefFrame,'tag': 'B'},
             'Policy': {'type': 'Policy','widget': PolicyFrame,'tag':u'\u03C0'},
             'Messages': {'type': 'Messages','widget': MessageFrame},
             'Relationships': {'type': 'Relationships',
                               'widget': RelationFrame},
             'Mental Models': {'type': 'Mental Models',
                               'widget': MentalModelFrame},
             }
        for key,spec in self.paneSpecs.items():
            if self.images.has_key(key):
                spec['image'] = self.images[key]
        # Determine which panes are relevant
        self.panes = [self.paneSpecs['General'],
                      self.paneSpecs['State']]
        if not self['abstract'] and len(self['entity'].actions.getOptions()) > 0:
            self.panes.append(self.paneSpecs['Actions'])
        if self['abstract'] and not self['entity'].parent:
            self.panes.append(self.paneSpecs['Actions'])
        if isinstance(self['entity'],GoalBasedAgent):
            self.panes.append(self.paneSpecs['Goals'])
        if not self['entity'].parent:
            self.panes.append(self.paneSpecs['Observations'])
        if not self['entity'].parent:
            self.panes.append(self.paneSpecs['Beliefs'])
        if not self['abstract'] and len(self['entity'].actions.getOptions()) > 0:
            self.panes.append(self.paneSpecs['Policy'])
        if not self['abstract']:
            self.panes.append(self.paneSpecs['Messages'])
        if not self['entity'].parent:
            self.panes.append(self.paneSpecs['Relationships'])
        # Save belief widgets
        self.policywidgets = {}
        self.bstatewidgets = {}
        if self['window']:
            self.win = InnerWindow(parent = frame, title = self['entity'].name,
                                   height = self.agtHeight, width =  self.agtWidth,
                                   x = self['x'], y = self['y'],
                                   destroycommand=self['destroycommand'])
            container = self.win.component('frame')
        else:
            self.win = None
            container = frame
        # Create all of the separate panes
        notebook = self.createcomponent('notebook',(), None, Pmw.NoteBook,
                                        (container,),raisecommand=self.selectPage,
                                        )
        if self.win:
            notebook.pack(fill='both',expand='yes')
        for entry in self.panes:
            self.create_pane(self['entity'], notebook, entry)
        self.selectPage(self.panes[0]['type'])
        self.initialiseoptions()

    def setExpert(self,entity=None):
        if not entity:
            entity = self['entity']
        for component in self.components():
            if self.componentgroup(component) == 'Pane':
                self.component(component).configure(expert=self['expert'])
        if not self['abstract'] and len(entity.actions.getOptions()) > 0:
            # Generic models don't have polices, nor do agents
            # with no actions
            self.setExpertPane(entity,'Policy','Messages')
        if isinstance(entity,Stereotyper) and \
               len(entity.getEntities()) > 0 and self['beta']:
            # ...only those agents with mental models and theory
            # of mind
            self.setExpertPane(entity,'Mental Models','Policy')

    def setExpertPane(self,entity,pane,before):
        notebook = self.component('notebook')
        if self['expert']:
            spec = self.paneSpecs[pane]
            try:
                tag = spec['tag']
            except KeyError:
                tag = spec['type']
            if not tag in notebook.pagenames():
                page = notebook.insert(tag,before=before)
                self.create_pane(entity,notebook,spec,page)
        elif pane in notebook.pagenames():
            if entity.parent:
                self.destroycomponent('%s %s' % \
                                      (entity.ancestry(),pane))
            else:
                self.destroycomponent(pane)
            notebook.delete(pane)
            
    def applyPolicy(self,entity):
        """Display's the hypothetical result of the entity's policy"""
        widget = self.component('Actions')
        options = widget.getActions()
        if len(options) == 0:
            tkMessageBox.showerror('Agent Action Error','The agent has no allowable actions!  Please go to the Action pane and select at least one possible choice.')
        elif self['hypoCmd']:
            self['hypoCmd'](entity,options)
        else:
            raise NotImplementedError,'%s has no hypothetical step option' % (entity.ancestry())
        
    def stepEntity(self):
        """Performs the policy-selected action of the given entity"""
        widget = self.component('Actions')
        options = widget.getActions()
        if len(options) == 0:
            tkMessageBox.showerror('Agent Action Error','The agent has no allowable actions!  Please go to the Action pane and select at least one possible choices.')
        else:
            self['stepCmd'](self['entity'],options)
        
    def value(self,entity):
        """Performs the policy-selected action of the given entity"""
        self['valueCmd'](entity)

    def actEntity(self,action):
        self['actCmd']({self['entity'].name:action})

    def create_pane(self, entity, notebook, pane, page=None):
        if pane.has_key('tag'):
            tab = pane['tag']
        else:
            tab = pane['type']
        # Access notebook page
        if page is None:
            try:
                page = notebook.add(tab,tab_text='',tab_image=pane['image'])
            except KeyError:
                try:
                    page = notebook.add(tab,tab_font=pane['font'])
                except KeyError:
                    page = notebook.add(tab)
        if self['balloon']:
            self['balloon'].bind(self.component('notebook').tab(tab),pane['type'])
        # Generate page content
        try:
            frame = self.component(pane['type'])
        except KeyError:
            frame = self.createcomponent(pane['type'],(),'Pane',pane['widget'],(page,),
                                         balloon=self['balloon'],
                                         entity=entity,
                                         options=self['options'],
                                         society=self['society'],
                                         expert=self['expert'],
                                         generic=self['abstract'])
        # Do some specialized configuration
        if isinstance(frame,Pmw.ScrolledFrame):
            frame.configure(horizflex='expand')
        if pane['type'] == 'General':
            frame.configure(step=self.stepEntity,policy=self.applyPolicy,
                            valueCmd=self['valueCmd'])
        elif pane['type'] == 'State':
            for feature in entity.getStateFeatures():
                cmd = lambda widget=frame,f=feature:widget.set(f)
                if entity.parent:
                    self.bstatewidgets[entity.ancestry()+' '+feature] = cmd
        elif pane['type'] == 'Actions':
            if not self['abstract']:
                # Cannot actually perform action in generic society
                frame.configure(command=self.actEntity)
        elif pane['type'] == 'Goals':
            if not self['abstract']:
                frame.configure(society=None)
            frame.recreate_goals()
        elif pane['type'] == 'Policy':
            frame.configure(vertflex='expand')
            frame.configure(actions=self.component('Actions'),command=self['policyCmd'])
        elif pane['type'] == 'Beliefs':
            frame.configure(vertflex='expand',window=self.__class__,hypoCmd=self['hypoCmd'])
        elif pane['type'] == 'Messages':
            frame.configure(send=self['msgCmd'])
        frame.pack(side='top',expand='yes',fill='both')

    def update(self):
        self.component('State').update()
        for key in self.bstatewidgets.keys():
            apply(self.bstatewidgets[key],())
        if 'Actions' in self.components():
            self.component('Actions').drawActions()
        if 'Goals' in self.components():
            self.component('Goals').recreate_goals()
        if 'Beliefs' in self.components():
            self.component('Beliefs').update()
        if 'Relationships' in self.components():
            self.component('Relationships').update()

    def selectPage(self,page):
        palette = Pmw.Color.getdefaultpalette(self.interior())
        widget = self.component('notebook')
        for name in filter(lambda n:widget.componentgroup(n) == 'Page',
                           widget.components()):
            if name == page:
                widget.tab(name).configure(fg=palette['selectForeground'],
                                           bg=palette['selectBackground'])
            else:
                widget.tab(name).configure(fg=palette['activeForeground'],
                                           bg=palette['activeBackground'])
        if page == 'Actions' and self['abstract']:
            self.component('Actions_type_entry').focus_set()
        elif page == 'State' and self['abstract']:
            self.component('State_new_entry').focus_set()
        elif page == 'General':
            try:
                self.component('General_description_text').focus_set()
            except KeyError:
                # Probably haven't rendered this pane yet
                pass
##         elif page == 'Relationships' and self['abstract']:
##             self.component('Relationships_Relationship Name_entry').focus_set()


    def selectBeliefPage(self,page):
        if page == 'Policy' and len(self.activeBelief.policy.attributes) > 0:
            widget = self.component('%s Policy' % \
                                    (self.activeBelief.ancestry()))
            widget.displayPolicy()

    def setState(self,state='normal'):
        """Sets the state of all of the agent editing widgets
           - NORMAL: enables all of the widgets
           - DISABLED: disables all of the widgets
        """
        for pane in self.panes:
            if pane['type'] == 'General':
                try:
                    widget = self.component('%s Run Box' % (self['entity'].ancestry()))
                    widget.configure(Button_state=state)
                except KeyError:
                    pass
##                widget.component('hypo').configure(state=state)
            elif pane['type'] in ['State','Actions','Goals']:
                try:
                    widget = self.component(pane['type'])
                    widget.setState(state)
                except KeyError:
                    pass
            elif pane['type'] == 'Mental Models':
                if len(self['entity'].getEntities()) > 0:
                    try:
                        widget = self.component('%s Lock Models' % \
                                                (self['entity'].ancestry()))
                    except KeyError:
                        continue
                    widget.configure(state=state)
                    for other in self['entity'].getEntityBeliefs():
                        widget = self.component('%s Mental Models' % \
                                                (other.ancestry()))
                        if state == 'disabled':
                            widget.disable()
                        elif self['entity'].modelChange:
                            widget.enable()

    def renameEntity(self,old,new):
        """
        @param old: the current name of the entity
        @param new: the new name of the entity
        @type old,new: str
        """
        if self.win and self['entity'].name == new:
            self.win.configure(title=new)
        self.component('Relationships').renameEntity(old,new)
        if self.component('Actions_object').get() == old:
            self.component('Actions_object').selectitem(0)
        self.update()
    
    def getSelectedFrame(self):
        """
        @return: the selected frame (not just the notebook container pane)
        """
        selection = self.component('notebook').getcurselection()
        for pane in self.paneSpecs.values():
            if (pane.has_key('tag') and pane['tag'] == selection) or \
                    (pane['type'] == selection):
                break
        else:
            raise NameError,'Unable to find selected pane: %s' % (selection)
        return pane['type'],self.component(pane['type'])

    def getSelection(self):
        """
        @return: clipboard-ready selection from this window (C{None} if nothing appropriate)
        """
        pane = self.getSelectedFrame()[1]
        try:
            selection = pane.getSelection()
        except AttributeError:
            # Haven't defined getSelection for that pane.  So sue me.
            return None
        return selection

    def paste(self,content):
        pane = self.getSelectedFrame()[1]
#        try:
        pane.paste(content)
#        except AttributeError:
#            tkMessageBox.showerror('Unable to Paste','Cannot paste to %s pane' % (name.lower()))

    def destroy(self):
        self.win.destroy(override=True)
#        for name in self.components():
#            self.component(name).destroy()
        for variable in self.component('Actions').variables.values():
            del variable
        self.component('Observations').perfect
        self.component('General').destroycomponent('image')
        image = self['entity'].attributes['image']
        del image
        del self['entity'].attributes['image']
        Pmw.MegaArchetype.destroy(self)
