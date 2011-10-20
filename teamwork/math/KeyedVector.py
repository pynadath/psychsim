"""Classes for vectors with symbolic indices (i.e., L{Key} objects)
@var slopeTypes: dictionary of available classes for hyperplanes, indexed by appropriate labels
"""
try:
    from numpy.core.numeric import array,dot,all,seterr
    seterr(divide='raise')
    try:
        from numpy.core.numeric import matrixmultiply
    except ImportError:
        matrixmultiply = dot
except ImportError:
    try:
        from scipy import array,matrixmultiply,dot,all
    except ImportError:
        from Numeric import array,matrixmultiply,dot
        from Numeric import alltrue as all
from xml.dom.minidom import Document
import copy
from matrices import epsilon
from Keys import StateKey,ActionKey,ConstantKey,RelationshipKey,ClassKey,IdentityKey,keyDelete,keyConstant,Key

class KeyedVector:
    """A dictionary-based representation of a one-dimensional vector
    @ivar _fresh: flag indicating whether the current array needs an update
    @type _fresh: C{boolean}
    @ivar _frozen: flag indicating whether the dimensions of this vector are subject to change
    @type _frozen: C{boolean}
    @ivar _string: the string representation of this vector
    @type _string: C{str}
    @ivar _array: The numeric representation of this vector
    @type _array: C{array}
    """
    def __init__(self,args={}):
        self._frozen = False
##         self._fresh = False
        self._order = {}
        if len(args) > 0:
            # Store initial values
            self._orderedKeys = args.keys()
            self._orderedKeys.sort()
            values = []
            for index in range(len(args)):
                key = self._orderedKeys[index]
                self._order[key] = index
                values.append(args[key])
            self._array = array(values)
        else:
            # Start with no values
            self._orderedKeys = []
            self._array = None # This is somehow faster than array([])

    def keys(self):
        """
        @return: a consistently ordered list of keys
        @rtype: L{Key}[]
        """
        return self._orderedKeys
    
    def setArray(self):
        """Now deprecated because of irrelevance.  Used to update the internal numeric representation based on the current dictionary contents"""
        raise DeprecationWarning,'Calls to setArray should be unnecessary'

    def _updateString(self):
        """Updates the string representation of this vector, as needed to enforce consistent ordering (e.g., for hashing)"""
        self._string = '{'
        self._string += '\n'.join(map(lambda k: '\t%s: %5.3f' % (k,self[k]),
                                      self.keys()))
        self._string += '}'

    def compactString(self):
        """
        @return: a one-line string representation
        @rtype: str
        """
        return ','.join(map(lambda k: '%6.4f*%s' % (self[k],str(k)),
                            filter(lambda k: self[k] > epsilon,self.keys())))
    def addColumns(self,keys,values=None):
        """Adds new slots to this vector
        @param keys: the (sorted) keys for the new slots to insert
        @type keys: L{Key}[]
        @param values: the values to insert for each key (defaults to 0.)
        @type values: float, or dict:L{Key}S{->}float
        @warning: Assumes that keys are sorted!
        """
        if self._array is None:
            # Build up array from scratch; all keys are missing
            self._orderedKeys = keys[:]
            arrayValues = []
            for index in range(len(keys)):
                key = keys[index]
                self._order[key] = index
                if isinstance(values,dict):
                    try:
                        arrayValues.append(values[key])
                    except KeyError:
                        arrayValues.append(0.)
                elif values is None:
                    arrayValues.append(0.)
                else:
                    arrayValues.append(values)
            self._array = array(arrayValues)
            return
        # Initialize values and find out which keys are missing
        newKeys = []
        newValues = {}
        for key in keys:
            if not self.has_key(key):
                newKeys.append(key)
                if isinstance(values,dict):
                    try:
                        newValues[key] = values[key]
                    except KeyError:
                        newValues[key] = 0.
                elif values is None:
                    newValues[key] = 0.
                else:
                    newValues[key] = values
        # Nothing to do if there are no missing columns
        if len(newKeys) == 0:
            return
        elif self._frozen:
            raise UserWarning,'You are modifying a frozen vector'
        # OK, let's build ourselves a new vector
        finalOrder = {} # The key order for the resulting vector
        finalKeys = []  # The ordered key list for the resulting vector
        finalArray = [] # The ordered value list for the resulting vector
        oldIndex = 0    # The pointer to the next old key to copy
        newIndex = 0    # The pointer to the next new key to insert
        # Insert all the new keys
        while newIndex < len(newKeys):
            # Insert all the old keys that come before this new key
            newKey = newKeys[newIndex]
            while oldIndex < len(self._orderedKeys) and \
                      self._orderedKeys[oldIndex] < newKey:
                # Copy an old key
                key = self._orderedKeys[oldIndex]
                finalOrder[key] = len(finalKeys)
                finalKeys.append(key)
                finalArray.append(self._array[oldIndex])
                oldIndex += 1
            # Copy the new key
            finalOrder[newKey] = len(finalKeys)
            finalKeys.append(newKey)
            finalArray.append(newValues[newKey])
            newIndex += 1
        while oldIndex < len(self._orderedKeys):
            # Copy an old key
            key = self._orderedKeys[oldIndex]
            finalOrder[key] = len(finalKeys)
            finalKeys.append(key)
            finalArray.append(self._array[oldIndex])
            oldIndex += 1
        # Set the final results
        self._order = finalOrder
        self._orderedKeys = finalKeys
        self._array = array(finalArray)

    def getArray(self):
        """
        @return: the numeric array representation of this vector
        @rtype: C{array}
        """
        if self._array is None:
            return array([])
        else:
            return self._array

    def __getitem__(self,key):
        return self.getArray()[self._order[key]]
    
    def __setitem__(self,key,value):
        """@type key: L{Key} instance
        @type value: C{float}"""
        try:
            index = self._order[key]
            self.getArray()[index] = value
        except KeyError:
            self.addColumns([key],values={key:value})

    def getState(self):
        """
        @return: the embedded state vector, removing any non L{StateKey} elements (but including the constant factor)
        @rtype: L{KeyedVector}
        """
        result = KeyedVector()
        for key in self.keys():
            if isinstance(key,StateKey) or isinstance(key,ConstantKey):
                result[key] = self[key]
        if self._frozen:
            result.freeze()
        return result

    def normalize(self):
        """Scales this vector so that the highest absolute weight is 1
        @warning: throws exception if the vector is all 0s
        """
        factor = max(map(abs,self._array))
        if factor > 1e-10:
            self._array *= 1./factor
#             if max(self._array) < 1e-10:
#                 # All negative
#                 self._array = -self._array
        else:
            raise ZeroDivisionError
        
    def __len__(self):
        return len(self._order)

    def items(self):
        return map(lambda k:(k,self[k]),self.keys())

    def __eq__(self,other):
        if self._frozen and other._frozen:
            diff = sum(map(abs,self.getArray() - other.getArray()))
            return diff < 1e-10
#            return all(self.getArray() == other.getArray())
        else:
            return all(self.getArray() == other.getArray()) == 1 and \
                   (self._order == other._order)

    def __delitem__(self,key):
        if self._frozen:
            raise UserWarning,'You are modifying a frozen vector'
        index = self._order[key]
        values = self._array.tolist()
        self._array = array(values[:index]+values[index+1:])
        del self._order[key]
        for other in self._orderedKeys[index+1:]:
            self._order[other] -= 1
        self._orderedKeys.remove(key)

    def has_key(self,key):
        return self._order.has_key(key)
    
    def fill(self,keys,value=None):
        """Fills in any missing slots with a default value (it's really just a call to L{addColumns} now)
        @param keys: the slots that should be filled
        @type keys: list of L{Key} instances
        @param value: the default value (defaults to 0)
        @note: does not overwrite existing values
        """
        self.addColumns(keys,value)

    def instantiate(self,table=False):
        """Substitutes values for any abstract references, using the given substitution table
        @param table: dictionary of key-value pairs, where the value will be substituted for any appearance of the given key in a field of this L{Key} object
        @type table: dictionary
        @rtype: L{KeyedVector}
        """
        args = {}
        for key,value in self.items():
            newKeys = key.instantiate(table)
            if not isinstance(newKeys,list):
                if newKeys == keyDelete:
                    newKeys = []
                else:
                    newKeys = [newKeys]
            for newKey in newKeys:
                try:
                    args[newKey] += value
                except KeyError:
                    args[newKey] = value
        return self.__class__(args)
        
    def instantiateKeys(self,table):
        """Substitutes values for any abstract references, using the given substitution table
        @param table: dictionary of key-value pairs, where the value will be substituted for any appearance of the given key in a field of this L{Key} object
        @type table: dictionary"""
        args = {}
        for key,value in self.items():
            newKeys = key.instantiate(table)
            if not isinstance(newKeys,list):
                if newKeys == keyDelete:
                    newKeys = []
                else:
                    newKeys = [newKeys]
            for newKey in newKeys:
                try:
                    args[newKey] += value
                except KeyError:
                    args[newKey] = value
        # Reset the vector
        self._order.clear()
        self._orderedKeys = args.keys()
        self._orderedKeys.sort()
        values = []
        for index in range(len(args)):
            key = self._orderedKeys[index]
            self._order[key] = index
            values.append(args[key])
        self._array = array(values)
##         self._fresh = False
        self._updateString()

    def compose(self,other,op):
        """Composes the two vectors together using the given operator
        @param other: the other vector to compose with
        @type other: L{KeyedVector} instance
        @param op: the operator used to generate the new array values
        @type op: C{lambda x,y:f(x,y)} where C{x} and C{y} are C{array} instances
        @rtype: a new L{KeyedVector} instance"""
        result = KeyedVector()
        result._order = self._order
        result._orderedKeys = self._orderedKeys
        result._array = op(self.getArray(),other.getArray())
        if self._frozen:
            result.freeze()
        else:
            result.unfreeze()
        return result

    def merge(self,other):
        """
        @type other: L{KeyedVector}
        @return: a vector combining all of the values of this one with the one passed in
        @rtype: L{KeyedVector}
        """
        result = KeyedVector()
        for key in self.keys():
            result[key] = self[key]
        for key in other.keys():
            result[key] = other[key]
        return result

    def freeze(self):
        """Locks in the dimensions and keys of this vector.  A frozen vector leads to faster math.
        """
        self._frozen = True

    def unfreeze(self):
        """Unlocks the dimensions and keys of this vector
        @return: C{True} iff the vector was originally frozen
        @rtype: bool
        """
        if self._frozen:
            self._order = copy.copy(self._order)
            self._orderedKeys = copy.copy(self._orderedKeys)
            self._frozen = False
            return True
        else:
            return False
        
    def __add__(self,other):
        """
        @warning: assumes that your vectors are aligned
        """
        return self.compose(other,lambda x,y:x+y)

    def __sub__(self,other):
        return self + (-other)
    
    def __neg__(self):
        result = KeyedVector()
        result._order = self._order
        result._orderedKeys = self._orderedKeys
        result._array = -self.getArray()
        if self._frozen:
            result.freeze()
        else:
            result.unfreeze()
        return result
    
    def __mul__(self,other):
        """
           - If other is a L{KeyedVector}, then the result is the dot product
           - If other is a L{KeyedMatrix}, then the result is product of this vector, transposed, by the matrix
           - Otherwise, each element in this vector is scaled by other
           """
        if isinstance(other,KeyedVector):
            # Dot product
            if self._frozen and other._frozen:
                # Assume that they are aligned
                try:
                    result = dot(self.getArray(),other.getArray())
                except ValueError:
                    # Generate helpful error message
                    missing = []
                    extra = []
                    for key in self.keys():
                        if not other.has_key(key):
                            missing.append('"%s"' % (str(key)))
                    for key in other.keys():
                        if not self.has_key(key):
                            extra.append('"%s"' % (str(key)))
                    msg = 'Multiplicand'
                    if len(missing) > 0:
                        msg += ' is missing %s' % (', '.join(missing))
                        if len(extra) > 0:
                            msg += ' and'
                    if len(extra) > 0:
                        msg += ' has extra %s' % (', '.join(extra))
                    raise UserWarning,msg
            else:
                # Not aligned, so go key by key
                result = 0.
                for key in self.keys():
                    try:
                        result += self[key]*other[key]
                    except KeyError:
                        # Assume other[key] is 0
                        pass
            return result
        elif isinstance(other,dict):
            result = KeyedVector()
            try:
                result._array = matrixmultiply(self.getArray(),
                                               other.getArray())
            except ValueError:
                # More helpful error message than simply "objects are not aligned"
                missing = []
                extra = []
                for key in self.keys():
                    if not key in other.rowKeys():
                        missing.append('row "%s"' % (str(key)))
                    if not key in other.colKeys():
                        missing.append('column "%s"' % (str(key)))
                for key in other.rowKeys():
                    if not self._order.has_key(key):
                        extra.append('row "%s"' % (str(key)))
                for key in other.colKeys():
                    if not self._order.has_key(key):
                        extra.append('column "%s"' % (str(key)))
                msg = 'Multiplicand has'
                if len(missing) > 0:
                    msg += ' missing %s' % (', '.join(missing))
                    if len(extra) > 0:
                        msg += ' and'
                if len(extra) > 0:
                    msg += ' extra %s' % (', '.join(extra))
                raise UserWarning,msg
            result._order = self._order
            result._orderedKeys = self._orderedKeys
            if self._frozen:
                result.freeze()
            else:
                result.unfreeze()
            return result
        else:
            result = copy.copy(self)
            result._array = self.getArray()*other
            result._order = self._order
            result._orderedKeys = self._orderedKeys
            if self._frozen:
                result.freeze()
            else:
                result.unfreeze()
            return result

    def __rmul__(self,other):
        if isinstance(other,dict):
            # Key by key multiplication
            result = KeyedVector()
            for key in self.keys():
                try:
                    result[key] = self*other[key]
                except KeyError:
                    # Assume no-change if missing (by convention)
                    result[key] = self[key]
            return result
        else:
            raise UserWarning,'Unable to multiply %s by KeyedVector' % \
                  (other.__class__.__name__)
        
    def __str__(self):
        self._updateString()
        return self._string

    def simpleText(self):
        keys = filter(lambda k: abs(self[k]) > epsilon,self.keys())
        return ','.join(map(lambda k: '%s: %5.3f' % (str(k),self[k]),keys))

    def __hash__(self):
        return hash(str(self))

    def __xml__(self):
        doc = Document()
        root = doc.createElement('vector')
        doc.appendChild(root)
        for key,value in self.items():
            node = doc.createElement('entry')
            root.appendChild(node)
            node.appendChild(key.__xml__().documentElement)
            node.setAttribute('weight',str(value))
        return doc

    def parse(self,element,changeInPlace=False):
        """Extracts the distribution from the given XML element
        @param element: The XML Element object specifying the vector
        @type element: Element
        @param changeInPlace: flag, if C{True}, then modify this vector itself; otherwise, return a new vector
        @type changeInPlace: boolean
        @return: the L{KeyedVector} instance"""
        assert(element.tagName=='vector')
        if changeInPlace:
            node = element.firstChild
            while node:
                if node.nodeType == node.ELEMENT_NODE:
                    if node.tagName =='entry':
                        value = float(node.getAttribute('weight'))
                        child = node.firstChild
                        while child and child.nodeType != child.ELEMENT_NODE:
                            child = child.nextSibling
                        key = Key()
                        key = key.parse(child)
                        self[key] = value
                node = node.nextSibling
            result = self
        else:
            # Determine what type of vector this is
            vectorType = str(element.getAttribute('type'))
            try:
                cls = globals()['%sRow' % (vectorType)]
            except KeyError:
                cls = self.__class__
            vector = cls()
            result = vector.parse(element,True)
        return result

    def __copy__(self):
        result = self.__class__()
        result._array = copy.copy(self.getArray())
        result._order = self._order
        result._orderedKeys = self._orderedKeys
        if self._frozen:
            result.freeze()
        else:
            result._frozen = True
            result.unfreeze()
        return result
        
    def __deepcopy__(self,memo):
        result = KeyedVector()
        memo[id(self)] = result
        result._array = copy.deepcopy(self.getArray(),memo)
        result._order = self._order
        result._orderedKeys = self._orderedKeys
        if self._frozen:
            result.freeze()
        else:
            result._frozen = True
            result.unfreeze()
        return result
        
        
class DeltaRow(KeyedVector):
    """Subclass for rows used to compute deltas in dynamics"""
    keyClass = Key
    label = 'change'
    count = 1
    coefficients = [1.]

    def __init__(self,args={},sourceKey=None,deltaKey=None,value=0.):
        """
        @param sourceKey: the feature to be changed
        @param deltaKey: the feature to use in computing the delta
        @type sourceKey,deltaKey: L{Key}
        @param value: the coefficient for that feature
        @type value: C{float}
        """
        self.sourceKey = sourceKey
        self.deltaKey = deltaKey
        if sourceKey is None and len(args) > 0:
            raise UserWarning,'Use keyword arguments for typed row constructors'
        if self.sourceKey is None:
            KeyedVector.__init__(self,args)
        else:
            if deltaKey is None:
                self.deltaKey = self.keyClass()
            row = {self.sourceKey:1.}
            if isinstance(value,list):
                values = value[:]
            else:
                values = map(lambda w: w*value,self.coefficients)
            if isinstance(self.deltaKey,list):
                deltas = self.deltaKey
                assert len(deltas) == self.count,'Incorrect number of keys provided to %s' % (self.__class__.__name__)
            else:
                deltas = [self.deltaKey]
                assert self.count == 1,'Incorrect number of keys provided to %s' % (self.__class__.__name__)
            for position in range(len(deltas)):
                if isinstance(self.keyClass,list):
                    assert isinstance(deltas[position],self.keyClass[position]),'%s is not a %s' % (self.deltaKey,self.keyClass[position].__name__)
                else:
                    assert isinstance(deltas[position],self.keyClass),'%s is not a %s' % (self.deltaKey,self.keyClass.__name__)
                try:
                    row[deltas[position]] += values[position]
                except KeyError:
                    row[deltas[position]] = values[position]
            row.update(args)
            KeyedVector.__init__(self,row)

    def instantiate(self,table,debug=False):
        source = self.sourceKey.instantiate(table)
        if isinstance(source,list):
            if len(source) > 1:
                raise UserWarning,'Unable to instantiate ambiguous %s: %s->%s' \
                      % (self.__class__.__name__,self.sourceKey,str(source))
            else:
                source = source[0]
        if isinstance(self.deltaKey,list):
            delta = map(lambda k: k.instantiate(table),self.deltaKey)
            if max(map(len,delta)) > 1:
                raise UserWarning,'Unable to instantiate ambiguous %s: %s' % \
                    (self.__class__.__name__,self.simpleText())
            delta = map(lambda l: l[0],delta)
            value = map(lambda k: self[k],self.deltaKey)
#            value = self[self.deltaKey[0]]
        else:
            delta = self.deltaKey.instantiate(table)
            if isinstance(delta,list):
                if len(delta) > 1:
                    raise UserWarning,'Unable to instantiate ambiguous %s: %s' \
                          % (self.__class__.__name__,self.simpleText())
                else:
                    delta = delta[0]
            value = self[self.deltaKey]
        if self.sourceKey == self.deltaKey:
            result = self.__class__(sourceKey=source,deltaKey=delta,value=value-1.)
        else:
            result = self.__class__(sourceKey=source,deltaKey=delta,value=value)
        return result
    
    def instantiateKeys(self,table):
        """Substitutes values for any abstract references, using the given substitution table
        @param table: dictionary of key-value pairs, where the value will be substituted for any appearance of the given key in a field of this L{Key} object
        @type table: dictionary"""
        KeyedVector.instantiateKeys(self,table)
        keyList = self.sourceKey.instantiate(table)
        if isinstance(keyList,list):
            if len(keyList) > 1:
                raise UserWarning,'Unable to instantiate ambiguous %s: %s' \
                      % (self.__class__.__name__,self.simpleText())
            else:
                self.sourceKey = keyList[0]
        else:
            self.sourceKey = keyList
        keyList = self.deltaKey.instantiate(table)
        if isinstance(keyList,list):
            if len(keyList) > 1:
                raise UserWarning,'Unable to instantiate ambiguous %s: %s' \
                      % (self.__class__.__name__,self.simpleText())
            else:
                self.deltaKey = keyList[0]
        else:
            self.deltaKey = keyList

    def __delitem__(self,key):
        KeyedVector.__delitem__(self,key)
        if key == self.sourceKey:
            print 'Deleting source key from %s!' % (self.__class__.__name__)
        elif key == self.deltaKey:
            self.deltaKey = self.sourceKey
            
    def __copy__(self):
        if isinstance(self.deltaKey,list):
            deltas = self.deltaKey
        else:
            deltas = [self.deltaKey]
        if self.sourceKey == self.deltaKey:
            return self.__class__(sourceKey=self.sourceKey,
                                  deltaKey=self.deltaKey,
                                  value=self[deltas[0]]-1.)
        else:
            return self.__class__(sourceKey=self.sourceKey,
                                  deltaKey=self.deltaKey,
                                  value=self[deltas[0]])

    def __deepcopy__(self,memo):
        if isinstance(self.deltaKey,list):
            deltas = self.deltaKey
            value = map(lambda k: self[k],self.deltaKey)
        else:
            deltas = [self.deltaKey]
            value = self[self.deltaKey]
            if self.sourceKey == self.deltaKey:
                value -= 1.
        result = self.__class__(sourceKey=self.sourceKey,
                                    deltaKey=self.deltaKey,
                                    value=value)
        memo[id(self)] = result
        # Check whether there are any other keys to be inserted
        for key in self.keys():
            if key != self.sourceKey and not key in deltas:
                break
        else:
            # Nope
            return result
        result._array = copy.deepcopy(self.getArray(),memo)
        result._order = self._order
        result._orderedKeys = self._orderedKeys
        if self._frozen:
            result.freeze()
        else:
            result._frozen = True
            result.unfreeze()
        return result

    def __xml__(self):
        doc = KeyedVector.__xml__(self)
        element = doc.documentElement
        node = doc.createElement('source')
        element.appendChild(node)
        node.appendChild(self.sourceKey.__xml__().documentElement)
        node = doc.createElement('delta')
        element.appendChild(node)
        if isinstance(self.deltaKey,list):
            for key in self.deltaKey:
                node.appendChild(key.__xml__().documentElement)
        else:
            node.appendChild(self.deltaKey.__xml__().documentElement)
        element.setAttribute('type',self.__class__.__name__[:-3])
        return doc

    def parse(self,element,changeInPlace=True):
        """Extracts the distribution from the given XML element
        @param element: The XML Element object specifying the vector
        @type element: Element
        @param changeInPlace: flag, if C{True}, then modify this vector itself; otherwise, return a new vector
        @type changeInPlace: boolean
        @return: the L{KeyedVector} instance"""
        if not changeInPlace:
            return KeyedVector.parse(self,element,False)
        KeyedVector.parse(self,element,True)
        # Fill in the missing bits from XML
        node = element.firstChild
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                if node.tagName == 'source':
                    child = node.firstChild
                    while child and child.nodeType != child.ELEMENT_NODE:
                        child = child.nextSibling
                    key = Key()
                    self.sourceKey = key.parse(child)
                elif node.tagName == 'delta':
                    self.deltaKey = []
                    child = node.firstChild
                    while child:
                        if child.nodeType == child.ELEMENT_NODE:
                            key = Key()
                            self.deltaKey.append(key.parse(child))
                        child = child.nextSibling
                    if len(self.deltaKey) == 1:
                        self.deltaKey = self.deltaKey[0]
                        self.value = self[self.deltaKey]
            node = node.nextSibling
        return self

    
class SetToConstantRow(DeltaRow):
    """A row that sets the value of a given feature to a specific value
    @note: can possibly be abused to create a row that sets the value of one feature to a percentage of some other feature
    """
    keyClass = ConstantKey
    label = 'set to constant'
    
    def __init__(self,args={},sourceKey=None,
                 deltaKey=keyConstant,value=0.):
        """
        @param sourceKey: the feature to be changed
        @param deltaKey: the L{Key} for the value column; should be omitted
        @type sourceKey: L{StateKey}
        @type deltaKey: L{ConstantKey}
        @param value: the new value
        @type value: C{float}
        """
        DeltaRow.__init__(self,args,sourceKey,deltaKey,value)
        if self.sourceKey:
            self[self.sourceKey] = 0.

    def simpleText(self,numbers=True,all=False):
        return 'set to %4.2f' % (self[self.deltaKey])

class SetToFeatureRow(DeltaRow):
    """A row that sets the value of a given feature to a specific percentage of some other feature
    """
    keyClass = StateKey
    label = 'set to feature'
    
    def __init__(self,args={},sourceKey=None,deltaKey=keyConstant,value=0.):
        """
        @param sourceKey: the feature to be changed
        @param deltaKey: the L{Key} for the value column
        @type sourceKey: L{StateKey}
        @type deltaKey: L{StateKey}
        @param value: the percentage to use as the new value
        @type value: C{float}
        """
        DeltaRow.__init__(self,args,sourceKey,deltaKey,value)
        if self.sourceKey:
            self[self.sourceKey] = 0.

    def simpleText(self,numbers=True,all=False):
        return 'set to %d%% of %s' % (int(100.*self[self.deltaKey]),
                                      self.deltaKey.simpleText())

class IncrementRow(DeltaRow):
    """A row that increments the given feature by a constant amount"""
    keyClass = ConstantKey
    label = 'add constant'
    
    def __init__(self,args={},sourceKey=None,deltaKey=keyConstant,value=0.):
        """
        @param sourceKey: the feature to be changed
        @param deltaKey: the L{Key} for the increment column; should be omitted
        @type sourceKey: L{StateKey}
        @type deltaKey: L{ConstantKey}
        @param value: the amount of the increment
        @type value: C{float}
        """
        DeltaRow.__init__(self,args,sourceKey,deltaKey,value)

    def simpleText(self,numbers=True,all=False):
        if self[keyConstant] < 0.:
            return 'decrease by %5.3f' % (-self[keyConstant])
        else:
            return 'increase by %5.3f' % (self[keyConstant])

class ScaleRow(DeltaRow):
    """A row that increases the given feature by a percentage of another feature"""
    keyClass = StateKey
    label = 'add feature'

    def simpleText(self,numbers=True,all=False):
        try:
            coefficient = self[self.deltaKey]
        except KeyError:
            return DeltaRow.simpleText(self,numbers=numbers,all=all)
        if len(self) == 1:
            coefficient -= 1.
        coefficient *= 100.
        if coefficient < 0.:
            return 'decrease by %d%% of %s' % (-int(coefficient),
                                               self.deltaKey.simpleText())
        else:
            return 'increase by %d%% of %s' % (int(coefficient),
                                               self.deltaKey.simpleText())

class DiminishRow(DeltaRow):
    """A row that increases the given feature by a percentage of 1-another feature"""
    keyClass = ConstantKey
    label = 'add diminishing'

    def __init__(self,args={},sourceKey=None,deltaKey=keyConstant,value=0.):
        """
        @param sourceKey: the feature to be changed
        @param deltaKey: the L{Key} for the value column
        @type sourceKey: L{StateKey}
        @type deltaKey: L{StateKey}
        @param value: the percentage to use as the new value
        @type value: C{float}
        """
        DeltaRow.__init__(self,args,sourceKey,deltaKey,value)
        if self.sourceKey:
            self[self.sourceKey] -= abs(self[keyConstant])

    def simpleText(self,numbers=True,all=False):
        coefficient = self[keyConstant]
        coefficient *= 100.
        if coefficient < 0.:
            return 'approach -1 by %d%%' % (-int(coefficient))
        else:
            return 'approach 1 by %d%%' % (int(coefficient))

class SetToFeaturePlusRow(DeltaRow):
    """A row that sets the given feature to be a percentage of another feature plus some increment
    """
    keyClass = [StateKey,ConstantKey]
    label = 'set to feature plus'
    count = 2
    coefficients = [0.,1.]

    def __init__(self,args={},sourceKey=None,deltaKey=None,value=0.):
        DeltaRow.__init__(self,args,sourceKey,deltaKey,value)
        if self.sourceKey:
            self[self.sourceKey] -= 1.

    def simpleText(self,numbers=True,all=False):
        keys = [self.deltaKey[0],self.deltaKey[1]]
        if abs(self[keys[0]]-1.) < 1e-8:
            if self[keys[1]] < 0.:
                return 'set to %s %5.3f' % (keys[0].simpleText(),self[keys[1]])
            else:
                return 'set to %s + %5.3f' % (keys[0].simpleText(),self[keys[1]])
        return 'set to %d%% of %s+%5.3f' % (int(self[keys[0]]*100.),keys[0].simpleText(),self[keys[1]])
    
class SetToDiffRow(DeltaRow):
    """A row that sets the given feature to be a percentage of another feature"""
    keyClass = StateKey
    label = 'set to difference'
    count = 2
    coefficients = [1.,-1.]

    def __init__(self,args={},sourceKey=None,deltaKey=None,value=0.):
        DeltaRow.__init__(self,args,sourceKey,deltaKey,value)
        if self.sourceKey:
            self[self.sourceKey] -= 1.

    def simpleText(self,numbers=True,all=False):
        keys = [self.deltaKey[0],self.deltaKey[1]]
        try:
            keys.sort(lambda k1,k2: cmp(self[k1],self[k2]))
        except KeyError:
            return DeltaRow.simpleText(self,numbers=numbers,all=all)
        return 'set to by %d%% of %s-%s' % (int(self[keys[1]]*100.),keys[1].simpleText(),keys[0].simpleText())
    
class ActionCountRow(DeltaRow):
    """A rows that sets the value to a count of a given type of action
    """
    keyClass = ActionKey
    label = 'action count'

    def simpleText(self,numbers=True,all=False):
        return 'set to %d%% of # of %s' % (int(100.*self[self.deltaKey]),
                                           self.deltaKey.simpleText())

class UnchangedRow(IncrementRow):
    """A row that doesn't change the given feature"""
    label = 'no change'
    
    def __init__(self,args={},sourceKey=None,deltaKey=keyConstant,value=0.):
        """
        @param sourceKey: the feature to be changed
        @param deltaKey: the L{Key} for the increment column; should be omitted
        @type sourceKey: L{StateKey}
        @type deltaKey: L{ConstantKey}
        @param value: the amount of the increment (ignored, always 0)
        @type value: C{float}
        """
        IncrementRow.__init__(self,args,sourceKey,deltaKey,0.)
    
    def simpleText(self,numbers=True,all=False):
        return 'no change'
    
def getDeltaTypes():
    """Automatic extraction of possible L{DeltaRow} subclasses
    @return: all available subclasses of L{DeltaRow}
    @rtype: C{dict:str->class}
    """
    import inspect
    result = {}
    for key,value in globals().items():
        if inspect.isclass(value) and issubclass(value,DeltaRow) and \
               not value is DeltaRow:
            result[key[:-3]] = value
    return result
deltaTypes = getDeltaTypes()

class SlopeRow(KeyedVector):
    """Subclass for rows used to represent the slope of planes
    @cvar args: list of keys for this test
    @cvar threshold: the default threshold for a plane of this type
    @cvar relation: the default relation for a plane of this type
    """
    args = []
    threshold = None
    relation = None
    
    def __init__(self,args={},keys=None):
        initial = {}
        self.specialKeys = []
        if keys is not None:
            for index in range(len(self.args)):
                try:
                    key = keys[index]
                    if key.__class__.__name__ == 'dict':
                        key = self.args[index]['type'](key)
                    self.specialKeys.append(key)
                except IndexError:
                    raise IndexError,'%s expects %d keys' % \
                          (self.__class__.__name__,len(self.args))
                if key != keyDelete:
                    try:
                        initial[key] += self.args[index]['weight']
                    except KeyError:
                        initial[key] = self.args[index]['weight']
        initial.update(args)
        KeyedVector.__init__(self,initial)

    def instantiate(self,table):
        """Substitutes values for any abstract references, using the given substitution table
        @param table: dictionary of key-value pairs, where the value will be substituted for any appearance of the given key in a field of this L{Key} object
        @type table: dictionary"""
        substitutions = [[]]
        for index in range(len(self.specialKeys)):
            newKey = self.specialKeys[index].instantiate(table)
            if isinstance(newKey,list):
                if len(newKey) > 1:
                    newSubstitutions = []
                    while substitutions:
                        keyList = substitutions.pop()
                        for key in newKey:
                            newSubstitutions.append(keyList+[key])
                    substitutions = newSubstitutions
                elif len(newKey) == 0:
                    # No matches for the given key
                    return None
                else:
                    for keyList in substitutions:
                        keyList.append(newKey[0])
            else:
                for keyList in substitutions:
                    keyList.append(newKey)
        if len(substitutions) == 0:
            # No possible instantiations
            return None
        elif len(substitutions) == 1:
            # Unique instantiation
            return self.__class__(keys=substitutions[0])
        else:
            results = []
            for keyList in substitutions:
                newTable = {}
                newTable.update(table)
                for position in range(len(self.specialKeys)):
                    old = self.specialKeys[position]
                    new = keyList[position]
                    for slot,filler in old.slots.items():
                        if filler == old.ENTITY:
                            if isinstance(table[old[slot]],list) and \
                                len(table[old[slot]]) > 1:
                                # We have found a specific instance from a list of fillers
                                newTable[old[slot]] = [new[slot]]
                results.append({'row': self.__class__(keys=keyList),
                                'table': newTable})
            return results
        
    def instantiateKeys(self,table):
        """Substitutes values for any abstract references, using the given substitution table
        @param table: dictionary of key-value pairs, where the value will be substituted for any appearance of the given key in a field of this L{Key} object
        @type table: dictionary"""
        KeyedVector.instantiateKeys(self,table)
        for index in range(len(self.specialKeys)):
            keyList = self.specialKeys[index].instantiate(table)
            if isinstance(keyList,list):
                if len(keyList) > 1:
                    raise UserWarning,\
                          'Unable to instantiate ambiguous %s: %s' \
                          % (self.__class__.__name__,self.simpleText())
                else:
                    self.specialKeys[index] = keyList[0]
            else:
                self.specialKeys[index] = keyList
            
    def __copy__(self):
        return self.__class__(keys=self.specialKeys)

    def __deepcopy__(self,memo):
        result = self.__class__(keys=self.specialKeys)
        memo[id(self)] = result
        if len(self) > len(self.args):
            result._array = copy.deepcopy(self.getArray(),memo)
            result._order = self._order
            result._orderedKeys = self._orderedKeys
            if self._frozen:
                result.freeze()
            else:
                result._frozen = True
                result.unfreeze()
        return result

    def __xml__(self):
        doc = KeyedVector.__xml__(self)
        element = doc.documentElement
        element.setAttribute('type',self.__class__.__name__[:-3])
        for key in self.specialKeys:
            node = doc.createElement('slopeKey')
            element.appendChild(node)
            node.appendChild(key.__xml__().documentElement)
        return doc
    
    def parse(self,element,changeInPlace=True):
        """Extracts the distribution from the given XML element
        @param element: The XML Element object specifying the vector
        @type element: Element
        @param changeInPlace: flag, if C{True}, then modify this vector itself; otherwise, return a new vector
        @type changeInPlace: boolean
        @return: the L{KeyedVector} instance"""
        if not changeInPlace:
            return KeyedVector.parse(self,element,False)
        KeyedVector.parse(self,element,True)
        # Fill in the missing bits from XML
        node = element.firstChild
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                if node.tagName == 'slopeKey':
                    child = node.firstChild
                    while child and child.nodeType != child.ELEMENT_NODE:
                        child = child.nextSibling
                    key = Key()
                    self.specialKeys.append(key.parse(child))
            node = node.nextSibling
        # Patch bug in writing Equal Row
        if len(self.specialKeys) < len(self.args):
            node = element.firstChild
            while node:
                if node.nodeType == node.ELEMENT_NODE:
                    if node.tagName == 'entry':
                        child = node.firstChild
                        while child and child.nodeType != child.ELEMENT_NODE:
                            child = child.nextSibling
                        key = Key()
                        self.specialKeys.append(key.parse(child))
                node = node.nextSibling
        assert len(self.specialKeys) == len(self.args)
        return self

class TrueRow(SlopeRow):
    """A vector that produces a hyperplane that is always true

    The following creates such a row:

    >>> row = TrueRow()
    """
    args = []

    def simpleText(self,numbers=True,all=False):
        return '...'
    
class ThresholdRow(SlopeRow):
    """A vector for testing that a given state feature exceeds a threshold.  It should be created as C{row = ThresholdRow(keys=[{'entity':entity,'feature':feature}])} to create a test on the given C{feature} value of the given C{entity}

    The following creates a row to test my power:
    
    >>> row = ThresholdRow(keys=[{'entity':'self','feature':'power'}])"""
    args = [{'type':StateKey,'weight':1.}]

    def simpleText(self,numbers=True,all=False):
        return self.specialKeys[0].simpleText()

class ClassRow(SlopeRow):
    """A vector for testing that a given entity is a member of a given class.  It should be created as C{row = ClassRow(keys=[{'entity':entity,'value':cls}])} to create a test that the given C{entity} is a member of the given C{cls}

    The following creates a row to test that the actor is a teacher:
    
    >>> row = ClassRow(keys=[{'entity':'actor','value':'Teacher'}])"""
    
    args = [{'type':ClassKey,'weight':1.}]
    threshold = 0.
    
    def simpleText(self,numbers=True,all=False):
        return self.specialKeys[0].simpleText()

class RelationshipRow(SlopeRow):
    """A vector for testing that a given entity has the specified relationship to another entity.  It should be created as C{row = RelationshipRow(keys=[{'feature':relation,'relatee':entity}])} to create a test that C{entity} is a C{relation} of me

    The following creates a row to test that the actor is my student

    >>> row = RelationshipRow(keys=[{'feature':'student','relatee':'actor'}])
    """
    args = [{'type':RelationshipKey,'weight':1.}]
    threshold = 0.
    
    def simpleText(self,numbers=True,all=False):
        return self.specialKeys[0].simpleText()
    
class IdentityRow(SlopeRow):
    """A vector for testing that a given entity is identical to another.  It should be created as C{row = IdentityRow(keys=[{'entity':entity}])} to create a test that the entity being tested is the given C{entity}

    The following creates a row to test that I am the object of the current action:
    
    >>> row = IdentityRow(keys=[{'entity':'object','relationship':'equals'}])"""
    args = [{'type':IdentityKey,'weight':1.}]
    threshold = 0.
    
    def simpleText(self,numbers=True,all=False):
        return self.specialKeys[0].simpleText()
    
class SumRow(SlopeRow):
    """A vector for testing that the sum of two given state features exceeds a threshold.
    @warning: not tested, probably doesn't work"""
    args = [{'type':StateKey,'weight':1.},
            {'type':StateKey,'weight':1.}]

    def simpleText(self,numbers=True,all=False):
        key1,key2 = self.specialKeys
        return '%s + %s' % (key1.simpleText(),key2.simpleText())
    
class DifferenceRow(SlopeRow):
    """A vector for testing that the difference between two given state features exceeds a threshold.
    @warning: not tested, probably doesn't work"""
    args = [{'type':StateKey,'weight':1.},
            {'type':StateKey,'weight':-1.}]

    def simpleText(self,numbers=True,all=False):
        key1,key2 = self.specialKeys
        if self[key1] > 0.:
            pos = key1
            neg = key2
        else:
            pos = key2
            neg = key1
        return '%s - %s' % (pos.simpleText(),neg.simpleText())
    
class EqualRow(SlopeRow):
    """A vector for testing that two given state features have the same value.
    """
    args = [{'type':StateKey,'weight':1.},
            {'type':StateKey,'weight':-1.}]
    threshold = 0.
    relation = '='

    def simpleText(self,numbers=True,all=False):
        key1,key2 = self.specialKeys
        if self[key1] > 0.:
            pos = key1
            neg = key2
        else:
            pos = key2
            neg = key1
        return '%s = %s' % (pos.simpleText(),neg.simpleText())

class ANDRow(SlopeRow):
    """Subclass representing a conjunction of tests.

    The following creates a row to test that the current state is both 'terminated' and 'accepted':

    >>> row = ANDRow(keys=[{'entity':'self','feature':'terminated'},{'entity':'self','feature':'accepted'}])
    """
    def __init__(self,args={},keys=None):
        SlopeRow.__init__(self,args,keys)
        if keys:
            self.specialKeys = keys[:]
        else:
            self.specialKeys = []

    def simpleText(self,numbers=True,all=False):
        content = []
        for key in self.specialKeys:
            if self[key] > 0.:
                content.append(key.simpleText())
            else:
                content.append('not %s' % (key.simpleText()))
        return ' and '.join(content)

class ORRow(SlopeRow):
    """Subclass representing a disjunction of tests.

    The following creates a row to test that the current state is either 'terminated' or 'accepted':

    >>> row = ORRow(keys=[{'entity':'self','feature':'terminated'},{'entity':'self','feature':'accepted'}])
    """
    def __init__(self,args={},keys=None):
        SlopeRow.__init__(self,args,keys)
        if keys:
            self.specialKeys = keys[:]
        else:
            self.specialKeys = []

    def simpleText(self,numbers=True,all=False):
        content = []
        for key in self.specialKeys:
            if self[key] > 0.:
                content.append(key.simpleText())
            else:
                content.append('not %s' % (key.simpleText()))
        return ' or '.join(content)
    
def getSlopeTypes():
    """Automatic extraction of possible L{SlopeRow} subclasses
    @return: all available subclasses of L{SlopeRow}
    @rtype: C{dict:str->class}
    """
    import inspect
    result = {}
    for key,value in globals().items():
        if inspect.isclass(value) and issubclass(value,SlopeRow) and \
               not value is SlopeRow:
            result[key[:-3]] = value
    # The following types are not easily supported by GUI
    del result['OR']
    del result['AND']
    # The following is not intended to be used, but is merely for display
    del result['True']
    return result
slopeTypes = getSlopeTypes()
vectorTypes = copy.copy(deltaTypes)
vectorTypes.update(slopeTypes)

if __name__ == '__main__':
    old = TrueRow()
    doc = old.__xml__()
    new = KeyedVector()
    new = new.parse(doc.documentElement)
    print new.__class__.__name__
    print new.simpleText()
