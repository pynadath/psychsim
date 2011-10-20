import tkMessageBox
import Pmw
from DynamicsEditor import DynamicsEditor
from teamwork.action.PsychActions import ActionCondition
from ActionDialog import ActionDialog 
from teamwork.math.Keys import ActionKey,StateKey
from teamwork.math.ProbabilityTree import ProbabilityTree,identityTree
        
class TreeBuilder(DynamicsEditor):
    """Frame for creating and editing PWL trees
    @ivar options: table of options available for new dynamics tree
    @type options: strS{->}L{Key}
    """
    
    def __init__(self,parent=None,**kw):
        self.options = {}
        optiondefs = (
            ('table', {},       None),
##            ('action',   None,     Pmw.INITOPT),
            ('society',  {},       None),
            ('newLabel', 'New...', Pmw.INITOPT),
            # Callback when creating a new tree
            ('new',None,None),
            # Callback when deleting a tree
            ('delete',None,None),
            # Key label for state/action whose dynamics we're building
            ('key',None,None),
            # Default leaf node for new trees
            ('default',None,None),
            )
        self.defineoptions(kw,optiondefs)
        DynamicsEditor.__init__(self,parent)
        # Create listbox-based action selector
        if self['society']:
            self.configure(menus_key=self['key'])
        pane = self.insert('select pane',min=150)
        self.pane('select pane').configure(padx=10)
        button = self.createcomponent('selector',(),None,Pmw.ScrolledListBox,
                                      (pane,),
                                      labelpos='nw',
                                      selectioncommand=self.selectTree,
                                      listbox_selectmode='single',
                                      )
        if isinstance(self['key'],ActionKey):
            button.configure(label_text='State Feature:')
        else:
            button.configure(label_text='Action:')
        button.pack(side='top',fill='both',expand='yes')
        if self['society']:
            box = self.createcomponent('select buttons',(),None,
                                       Pmw.ButtonBox,(pane,),
                                       )
            box.add(self['newLabel'],command=self.newTree)
            box.add('Delete',command=self.delTree,state='disabled')
            box.pack(side='top',fill='x')
        if len(self['table']) > 0:
            options = self['table'].keys()
            options.sort(lambda x,y:cmp(str(x).lower(),str(y).lower()))
            button.setlist(map(str,options))
            button.setvalue(str(options[0]))
            self.selectTree()
        self.initialiseoptions()

    def newTree(self):
        try:
            dialog = self.component('dialog')
        except KeyError:
            dialog = self.createDialog()
        if isinstance(self['key'],ActionKey):
            # Selecting state features for new dynamics tree
            self.options.clear()
            for entity in self['society'].members():
                for vector in entity.state.domain():
                    for key in vector.keys():
                        if not isinstance(key,ActionKey) and \
                               not self['table'].has_key(str(key)):
                            self.options[str(key)] = key
            optionList = self.options.keys()
            optionList.sort()
            dialog.component('scrolledlist').setlist(optionList)
            try:
                dialog.component('scrolledlist').setvalue(optionList[0])
            except IndexError:
                tkMessageBox.showerror('No Possible Dynamics','All possible dynamics already exist.')
                return
        else:
            # Selecting actions for new dynamics tree
            dialog.component('actions').clear()
            self.options.clear()
            for entity in self['society'].members():
                for option in entity.actions.getOptions():
                    for action in option:
#                         for entry in self['table'].values():
#                             if entry['condition'].match(option):
#                                 break
#                         else:
                        self.options[action['type']] = True
            optionList = self.options.keys()
            optionList.sort()
            dialog['actions'] = optionList
        dialog.activate()

    def newTreeChoice(self,button):
        self.component('dialog').deactivate()
        if button == 'OK':
            if isinstance(self['key'],ActionKey):
                condition = ActionCondition()
                condition.addCondition(self['key']['type'])
                state = self.options[self.component('dialog').getvalue()[0]]
                entry = {'lhs': state,'condition': condition}
            else:
                condition = self.component('dialog').getCondition()
                state = self['key']
                entry = {'condition': condition}
            if self['default']:
                entry['tree'] = ProbabilityTree(self['default'])
            else:
                if state['entity'] != 'self':
                    key = StateKey(state)
                    key['entity'] = 'self'
                else:
                    key = state
                entry['tree'] = identityTree(key)
            if self['new']:
                self['new'](state,condition,entry['tree'])
            if isinstance(self['key'],ActionKey):
                option = str(entry['lhs'])
            else:
                option = str(entry['condition'])
            self['table'][option] = entry
            self.refreshItems(option)
            self.selectTree(entry)
        
    def selectTree(self,entry=''):
        if entry == '':
            # Extract selection
            widget = self.component('selector')
            try:
                selection = widget.getcurselection()[0]
                entry = self['table'][selection]
            except KeyError:
                raise UserWarning,'Unknown selection: %s' % \
                      widget.getcurselection()[0]
            except IndexError:
                # Empty selection
                pass
        if entry != '':
            # Update tree display
            if not isinstance(self['key'],StateKey) and entry.has_key('lhs'):
                self.configure(menus_key=StateKey({'entity': 'self',
                                                   'feature': entry['lhs']['feature']}))
            self.configure(tree=entry['tree'])
            self.component('tree').root.invoke()
            if self['society']:
                self.component('select buttons').component('Delete').configure(state='normal')

    def delTree(self):
        widget = self.component('selector')
        label = widget.getcurselection()[0]
        title = 'Confirm delete'
        msg = 'Delete these dynamics permanently?'
        if tkMessageBox.askokcancel(title=title,message=msg):
            if self['delete']:
                self['delete'](self['table'][label])
            del self['table'][label]
            self.refreshItems()
            self.configure(tree=None)

    def refreshItems(self,selection=None):
        """Redraw the items in the selection pane (on the left)
        """
        widget = self.component('selector')
        itemList = self['table'].keys()
        itemList.sort(lambda x,y:cmp(x.lower(),y.lower()))
        widget.setlist(itemList)
        if selection is None:
            if self['society']:
                self.component('select buttons').component('Delete').configure(state='disabled')
        else:
            widget.setvalue(selection)

    def createDialog(self):
        """Creates the dialog for selecting action dependencies
        """
        if isinstance(self['key'],ActionKey):
            dialog = self.createcomponent('dialog',(),None,Pmw.SelectionDialog,
                                          (self.interior(),),
                                          title='New Dynamics')
        else:
            dialog = self.createcomponent('dialog',(),None,ActionDialog,
                                          (self.interior(),))
        dialog.configure(command=self.newTreeChoice,buttons=('OK','Cancel'),
                         defaultbutton='OK')
        dialog.withdraw()
        return dialog
