from Tkinter import Label,Frame
import tkMessageBox
import Pmw
from teamwork.widgets.DynamicsEditor import DynamicsEditor
from teamwork.math.ProbabilityTree import identityTree
from teamwork.dynamics.pwlDynamics import PWLDynamics
from teamwork.widgets.images import loadImages
        
class DynamicsDialog(Pmw.Dialog):
    """Dialog to display and edit the dynamics of a state feature"""
    
    def __init__(self,parent=None,**kw):
        optiondefs = (
            ('dynamics', {},       None),
            ('key',      None,     None),
            ('feature',  None,     Pmw.INITOPT),
            ('action',   None,     Pmw.INITOPT),
            ('expert',   0,        Pmw.INITOPT),
            ('society',  {},       None),
            ('newLabel', 'New...', Pmw.INITOPT),
            ('usePIL',   True,     Pmw.INITOPT),
            )
        self.defineoptions(kw,optiondefs)
        Pmw.Dialog.__init__(self,parent)
        self.images = loadImages({'addstate': 'icons/globe--plus.gif',
                                  'delstate': 'icons/globe--minus.gif',
                                  'addaction': 'icons/hammer--plus.gif',
                                  'delaction': 'icons/hammer--minus.gif',  
                                  'tree': 'icons/application-tree.gif'},
                                 self['usePIL'])
        self.options = {}
        if self['action']:
            for feature,dynamics in self['dynamics'].items():
                for agent,tree in dynamics.items():
                    if tree:
                        label = '%s of %s' % (feature,agent)
                        if tree.isAdditive():
                            label = '+' + label
                        else:
                            label = '*' + label
                        self.options[label] = {'feature':feature,
                                               'agent':agent}
        else:
            for action,dynamics in self['dynamics'].items():
                if dynamics:
                    if dynamics.isAdditive():
                        label = '+%s' % (str(action))
                    else:
                        label = '*%s' % (str(action))
                    self.options[label] = action
        options = self.options.keys()
        options.sort(lambda x,y:cmp(str(x).lower(),str(y).lower()))
        # Create viewing widget
        tree = self.createcomponent('editor',(),None,
                                    DynamicsEditor,
                                    (self.component('dialogchildsite'),),
                                    menus_key=self['key'],
                                    menus_feature=self['feature'],
                                    expert=self['expert'],
                                    orient='horizontal',
                                    society=self['society'],
                                    )
        orientation = 'left'
        pane = tree.insert('select pane',min=200)
        if self['society']:
            toolbar = Frame(pane,bd=2,relief='raised')
            # Button for adding new dynamics tree
            button = Label(toolbar)
            button.bind('<ButtonRelease-1>',self.newDynamics)
            if self['action']:
                try:
                    button.configure(image=self.images['addstate'])
                except KeyError:
                    button.configure(text=self['newLabel'])
            else:
                try:
                    button.configure(image=self.images['addaction'])
                except KeyError:
                    button.configure(text=self['newLabel'])
            button.pack(side='left')
            # Button for deleting selected dynamics tree
            button = Label(toolbar)
            button.bind('<ButtonRelease-1>',self.delDynamics)
            if self['action']:
                try:
                    button.configure(image=self.images['delstate'])
                except KeyError:
                    button.configure(text='Delete')
            else:
                try:
                    button.configure(image=self.images['delaction'])
                except KeyError:
                    button.configure(text='Delete')
            button.pack(side='left')
            toolbar.pack(side='top',fill='x')
        itemList = options[:]
        # Create listbox-based action selector
        button = self.createcomponent('Selector',(),None,
                                      Pmw.ScrolledListBox,(pane,),
                                      items=itemList,
                                      selectioncommand=self.selectTree,
                                      dblclickcommand=self.toggleAdd,
                                      listbox_selectmode='single',
                                      )
        button.pack(side='top',fill='both',expand='yes')
        if len(options) > 0:
            button.setvalue(str(options[0]))
            self.selectTree()
#        tree.setnaturalsize()
        tree.configure(hull_width=800)
        tree.pack(side=orientation,fill='both',expand='yes')
        self.initialiseoptions()

    def newDynamics(self,event=None):
        options = {}
        if self['action']:
            # Select feature/agent combinations
            if self['society']:
                for agent in self['society'].members():
                    for feature in agent.getStateFeatures():
                        options['%s of %s' % (feature,agent.name)] = \
                                    {'feature':feature,'agent':agent.name}
            label = 'State Feature'
        else:
            # Select action type that is not already in dynamics
            label = 'Action Type'
            if self['society']:
                for agent in self['society'].members():
                    for action in sum(agent.actions.getOptions(),[]):
                        if not self['dynamics'].has_key(action['type']):
                            options[action['type']] = action['type']
            if not self['dynamics'].has_key(None):
                options['(none)'] = None
        if len(options) == 0:
            # All dynamics already exist!
            tkMessageBox.showerror('No Missing Dynamics','All possible dynamics are already included')
            return
        items = options.keys()
        items.sort(lambda x,y:cmp(x.lower(),y.lower()))
        dialog = Pmw.SelectionDialog(self.component('dialogchildsite'),
                                     title=label,
                                     scrolledlist_items=items,
                                     scrolledlist_listbox_width=50,
                                     buttons=('OK','Cancel'),
                                     defaultbutton='OK')
        if dialog.activate() == 'OK':
            try:
                option = dialog.component('scrolledlist').getcurselection()[0]
            except IndexError:
                tkMessageBox.showerror('No Selection','You did not select anything for new dynamics')
                return
            if self['feature']:
                if self['dynamics'].has_key(options[option]):
                    msg = 'Dynamics for %s already exist' % (option)
                    tkMessageBox.showerror('Duplicate Action',msg)
                    return
                elif self['key']:
                    args = {'tree':identityTree(self['key'])}
                    self['dynamics'][options[option]] = PWLDynamics(args)
                else:
                    args = {'tree':identityTree(self['feature'])}
                    self['dynamics'][options[option]] = PWLDynamics(args)
                dynamics = self['dynamics'][options[option]]
            else:
                feature = options[option]['feature']
                agent = options[option]['agent']
                if self['dynamics'].has_key(feature) and \
                       self['dynamics'][feature].has_key(agent):
                    msg = 'Dynamics for %s already exist' % (option)
                    tkMessageBox.showerror('Duplicate Feature',msg)
                    return
                else:
                    args = {'tree':identityTree(options[option]['feature'])}
                    dynamics = PWLDynamics(args)
                    try:
                        self['dynamics'][feature][agent] = dynamics
                    except KeyError:
                        self['dynamics'][feature] = {agent: dynamics}
            if dynamics.isAdditive():
                label = '+%s' % (str(option))
            else:
                label = '*%s' % (str(option))
            self.options[label] = options[option]
            self.refreshItems(label)
            option = self.options[label]
            self.selectTree(option)

    def selectTree(self,option=''):
        if option == '':
            widget = self.component('Selector')
            try:
                option = self.options[widget.getcurselection()[0]]
            except KeyError:
                raise UserWarning,'Unknown selection: %s' % \
                      widget.getcurselection()[0]
            except IndexError:
                # Empty selection
                pass
        if option != '':
            widget = self.component('editor')
            if self['action']:
                if self['society']:
                    widget.component('menus').configure(feature=option['feature'])
                dynamics = self['dynamics'][option['feature']][option['agent']]
            else:
                dynamics = self['dynamics'][option]
            tree = dynamics.getTree()
            widget.configure(tree=tree)
            widget.component('tree').root.invoke()

    def delDynamics(self,event=None):
        widget = self.component('Selector')
        label = widget.getcurselection()[0]
        try:
            option = self.options[label]
        except KeyError:
            raise UserWarning,'Unknown selection: %s' % (label)
        title = 'Confirm delete'
        msg = 'Delete these dynamics permanently?'
        if tkMessageBox.askokcancel(title=title,message=msg):
            del self.options[label]
            if self['action']:
                del self['dynamics'][option['feature']][option['agent']]
            else:
                del self['dynamics'][option]
            self.refreshItems()
            self.component('editor').configure(tree=None)

    def toggleAdd(self,event=None):
        widget = self.component('Selector')
        label = widget.getcurselection()[0]
        try:
            option = self.options[label]
        except KeyError:
            raise UserWarning,'Unknown selection: %s' % (label)
        if self['action']:
            dynamics = self['dynamics'][option['feature']][option['agent']]
        else:
            dynamics = self['dynamics'][option]
        del self.options[label]
        if label[0] == '+':
            dynamics.makeNonadditive()
            label = '*'+label[1:]
        else:
            dynamics.makeAdditive()
            label = '+'+label[1:]
        self.options[label] = option
        self.refreshItems(label)
        
    def refreshItems(self,selection=None):
        """Redraw the items in the selection pane (on the left)
        """
        widget = self.component('Selector')
        itemList = self.options.keys()
        itemList.sort(lambda x,y:cmp(x.lower(),y.lower()))
        widget.setlist(itemList)
        if not selection is None:
            widget.setvalue(selection)
