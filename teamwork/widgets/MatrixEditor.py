import Pmw

from teamwork.math.Keys import ActionKey,StateKey,ClassKey,IdentityKey,RelationshipKey,ConstantKey,keyConstant
from teamwork.math.KeyedVector import slopeTypes,TrueRow,ClassRow,RelationshipRow
from teamwork.math.KeyedMatrix import dynamicsTypes,KeyedMatrix,DynamicsMatrix,IdentityMatrix
from teamwork.math.KeyedTree import KeyedPlane
from teamwork.math.probability import Distribution

class MatrixEditor(Pmw.MegaWidget):
    """
    Widget for editing dynamics trees
    @cvar probBranch: label for probabilistic branch in type selector
    @type probBranch: str
    
    """
    probBranch = 'Probabilistic'
    
    def __init__(self,parent,**kw):
        optiondefs = (
            ('states',    {}, None),
            ('roles',     {}, None),
            ('classes',   {}, None),
            ('relations', {}, None),
            ('actions',   {}, None),
            ('selectorCount',3,None),
            # The feature and key whose dynamics this tree is of
            ('key', None, None),
            ('feature', None, None),
            # The discretization interval for real values
            ('interval',      0.1,  Pmw.INITOPT),
            # The possible leaf nodes (if None, then use dynamics functions)
            ('leaves', dynamicsTypes.keys(), None),
            )
        self.defineoptions(kw, optiondefs)
        Pmw.MegaWidget.__init__(self,parent)
        self['leaves'].sort()
        # Color info so that we can disable text entry in ComboBoxes,
        # without making it look like the whole box is disabled
        palette = Pmw.Color.getdefaultpalette(parent)
        widget = self.createcomponent('type',(),None,Pmw.ComboBox,
                                      (self.component('hull'),),
                                      entry_state='disabled',
                                      entry_disabledforeground=palette['foreground'],
                                      entry_disabledbackground=palette['background'],
                                      history=False)
        widget.pack(side='top',fill='x')
        # Possibly variable number of selectors
        for index in range(self['selectorCount']):
            widget = self.createcomponent('feature%d' % (index),
                                          (),'feature',Pmw.ComboBox,
                                          (self.component('hull'),),
                                          entry_state='disabled',
                                          entry_disabledforeground=palette['foreground'],
                                          entry_disabledbackground=palette['background'],
                                          history=False)
            widget.pack_forget()
        self.initialiseoptions()

    def getDynamics(self):
        """
        @return: the dynamics matrix currently selected
        """
        widget = self.component('type')
        try:
            cls = dynamicsTypes[widget.get()]
        except KeyError:
            # Non-dynamics leaves
            return widget.get()
        keys = []
        for row in range(cls.rowClass.count):
            widget = self.component('feature%d' % (row))
            if isinstance(cls.rowClass.keyClass,list):
                keyClass = cls.rowClass.keyClass[row]
            else:
                keyClass = cls.rowClass.keyClass
            if keyClass is StateKey:
                key = self['states'][widget.get()]
            elif keyClass is ConstantKey:
                key = keyConstant
            elif keyClass is ActionKey:
                for key in self['actions'].keys():
                    if str(key) == widget.get():
                        break
                else:
                    raise NameError,'Unknown action condition: %s' % (widget.get())
            else:
                raise NotImplementedError,'Unable to create %s leaves' % \
                      (cls.__name__)
            keys.append(key)
        value = float(self.component('feature%d' % (cls.rowClass.count)).get())
        if cls.rowClass.count == 1:
            key = keys[0]
        else:
            if cls.rowClass.coefficients[0] < 1e-8:
                value = [1.,value]
            key = keys
        if self['key']:
            # Use key if specified
            row = cls(source=self['key'],key=key,value=value)
        else:
            row = cls(source=self['feature'],key=key,value=value)
        return row

    def getBranch(self):
        """
        @return: the plane currently selected
        """
        name = self.component('type').get()
        if name == self.probBranch:
            # Probabilistic branch
            widget = self.component('feature%d' % (self['selectorCount']-1))
            threshold = float(widget.get())
            return Distribution({'then':threshold,'else':1.-threshold})
        else:
            # PWL branch type
            widget = self.component('type')
            cls = slopeTypes[widget.get()]
            newArgs = []
            for index in range(len(cls.args)):
                arg = cls.args[index]
                widget = self.component('feature%d' % (index))
                if arg['type'] is StateKey:
                    key = self['states'][widget.get()]
                elif arg['type'] is ClassKey:
                    key = self['classes'][widget.get()]
                elif arg['type'] is IdentityKey:
                    key = self['roles'][widget.get()]
                elif arg['type'] is RelationshipKey:
                    key = self['relations'][widget.get()]
                else:
                    raise NotImplementedError,'Cannot handle %s keys' % \
                          arg['type'].__name__
                newArgs.append(key)
            row = cls(keys=newArgs)
            if cls.threshold is None:
                widget = self.component('feature%d' % (self['selectorCount']-1))
                threshold = float(widget.get())
            else:
                threshold = cls.threshold
            return KeyedPlane(row,threshold,cls.relation)

    def setDynamics(self,rowType):
        """Configures the menus for the given dynamics type
        """
        try:
            cls = dynamicsTypes[rowType]
        except KeyError:
            # Non-dynamics leaves
            cls = None
        if cls:
            for row in range(cls.rowClass.count):
                # Set up selector for the key
                widget = self.component('feature%d' % (row))
                widget.pack(fill='x')
                if isinstance(cls.rowClass.keyClass,list):
                    self.setMenuItems(cls.rowClass.keyClass[row],widget)
                else:
                    self.setMenuItems(cls.rowClass.keyClass,widget)
                widget.configure(entry_state='disabled')
            # Set up selector for the value
            widget = self.component('feature%d' % (cls.rowClass.count))
            self.setMenuItems(float,widget)
            widget.pack(fill='x',after=self.component('feature%d' % (cls.rowClass.count-1)))
            if cls is IdentityMatrix:
                # We don't need the pulldowns if there's no change
                last = 0
            else:
                last = cls.rowClass.count + 1
        else:
            # No change
            last = 0
        # Undraw any unused widgets
        for index in range(last,self['selectorCount']):
            widget = self.component('feature%d' % (index))
            widget.pack_forget()

    def setBranch(self,rowType):
        """Configures the menus for the given branch type
        """
        try:
            noThreshold = not (slopeTypes[rowType].threshold is None)
        except KeyError:
            # Probably a TrueRow
            noThreshold = False
        last = None
        for index in range(self['selectorCount']-1):
            widget = self.component('feature%d' % (index))
            try:
                arg = slopeTypes[rowType].args[index]
            except IndexError:
                arg = None
            except KeyError:
                arg = None
            if arg:
                self.setMenuItems(arg['type'],widget)
#                name = 'feature%d' % (self['selectorCount']-1)
                widget.pack(fill='x')
                last = widget
            else:
                # All required selectors already drawn
                widget.pack_forget()
        # Draw selector for threshold
        widget = self.component('feature%d' % (self['selectorCount']-1))
        if rowType == self.probBranch:
            self.setMenuItems(float,widget,0.)
        else:
            self.setMenuItems(float,widget)
        widget.selectitem('0.0')
        if noThreshold:
            widget.pack_forget()
        elif last is None:
            widget.pack(fill='x')
        else:
            widget.pack(fill='x',after=last)

    def displayDynamics(self,matrix):
        """Sets the menus to the given dynamics matrix
        """
        self.component('type').setlist(map(str,self['leaves']))
        if isinstance(matrix,KeyedMatrix):
            assert len(matrix) == 1
            row = matrix.values()[0]
            if isinstance(matrix,DynamicsMatrix):
                current = matrix.__class__.rowClass.label
            else:
                # Untyped
                self.component('type_entry').configure(state='normal')
                self.component('type_entry').delete(0,'end')
                self.component('type_entry').insert(0,'Unknown')
                self.component('type_entry').configure(state='disabled')
                return
            self.setDynamics(current)
            self.component('type').selectitem(current)
            if not isinstance(row.deltaKey,list):
                deltas = [row.deltaKey]
            else:
                deltas = row.deltaKey
            values = []
            for index in range(len(deltas)):
                key = deltas[index]
                if self['key']:
                    if key == self['key']:
                        value = row[key] - 1.
                    else:
                        value = row[key]
                elif isinstance(key,StateKey) and \
                   key['feature'] == self['feature'] and \
                   key['entity'] == 'self':
                    value = row[key] - 1.
                else:
                    value = row[key]
                self.component('feature%d' % (index)).selectitem(key.simpleText())
                values.append(value)
            self.component('feature%d_entryfield' % (len(deltas))).setvalue('%5.3f' % (values[-1]))
        else:
            self.setDynamics(matrix)
            self.component('type').selectitem(matrix)

    def displayBranch(self,plane):
        """Sets the menus to the given plane
        """
        names = self.getSlopes()
        # Set up branch type selector
        self.component('type').setlist(names)
        if isinstance(plane,Distribution):
            row = None
            current = self.probBranch
            threshold = dict.__getitem__(plane,'then')
        else:
            row = plane.weights
            current = row.__class__.__name__[:-3]
            threshold = plane.threshold
        try:
            self.component('type').selectitem(current)
        except IndexError:
            if current == 'True':
                self.setBranch(names[0])
                self.component('type').selectitem(names[0])
            else:
                print 'Unable to handle branches of type:',current
                return
        self.setBranch(current)
        if not isinstance(plane,Distribution):
            # Set up rest of selectors
            index = 0
            keyList = row.keys()[:]
            for arg in row.__class__.args:
                widget = self.component('feature%d' % (index))
                for key in keyList:
                    if row[key] == arg['weight']:
                        break
                else:
                    raise KeyError,'No key with weight %4.2f' % (arg['weight'])
                widget.selectitem(key.simpleText())
                keyList.remove(key)
                index += 1
        if isinstance(plane,Distribution):
            # Set threshold with a minimum of 0
            widget = self.component('feature%d' % (self['selectorCount']-1))
            widget.selectitem(self.mapValue(threshold,0.))
        elif not isinstance(row,ClassRow) and not isinstance(row,TrueRow) \
               and not isinstance(row,RelationshipRow):
            # Set threshold
            widget = self.component('feature%d' % (self['selectorCount']-1))
            widget.selectitem(self.mapValue(threshold))

    def getSlopes(self):
        """
        @return: the relevant set of possible branch types
        @rtype: str[]
        """
        names = slopeTypes.keys()
        names.sort()
        if not self['classes']:
            names.remove('Class')
        if not self['roles']:
            names.remove('Identity')
        if not self['relations']:
            names.remove('Relationship')
        names += [self.probBranch]
        return names
        
    def getMenuItems(self,cls,minimum=None):
        """
        @param minimum: optional floor value
        @return: a list of possible values for a variable of the given class
        @rtype: list
        """
        if cls is StateKey:
            keyList = self['states'].keys()
            keyList.sort()
        elif cls is ClassKey:
            keyList = self['classes'].keys()
            keyList.sort()
        elif cls is float:
            if minimum is None:
                minimum = -1.
            maximum = max(1.,minimum)
            span = maximum - minimum
            keyList = map(lambda x:'%3.1f' % (x*self['interval']+minimum),
                          range(int(span/self['interval'])+1))
        elif cls is ConstantKey:
            keyList = [cls.keyType]
        elif cls is IdentityKey:
            keyList = self['roles'].keys()
            keyList.sort()
        elif cls is RelationshipKey:
            keyList = self['relations'].keys()
            keyList.sort()
        elif cls is ActionKey:
            keyList = map(str,self['actions'].keys())
            keyList.sort()
        else:
            raise NotImplementedError,'Cannot handle %s keys' % \
                  cls.__name__
        return keyList
    
    def setMenuItems(self,cls,widget,minimum=None):
        keyList = self.getMenuItems(cls,minimum)
        widget.component('scrolledlist').setlist(keyList)
        if len(keyList) > 0:
            widget.selectitem(str(keyList[0]))
        if cls is float:
            widget.configure(entry_state='normal')
        else:
            widget.configure(entry_state='disabled')

    def mapValue(self,value,minimum=None):
        """
        @return: index of value in the discretized number space
        @rtype: int
        """
        if minimum is None:
            minimum = -1.
        return int((value-minimum)/self['interval'])
