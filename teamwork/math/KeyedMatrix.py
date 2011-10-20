"""Classes for matrices with symbolic indices (i.e., L{Key} objects)
"""
try:
    from numpy.core.numeric import array
    try:
        from numpy.core.numeric import matrixmultiply
    except ImportError:
        from numpy.core.numeric import dot as matrixmultiply
except ImportError:
    try:
        from scipy import array,matrixmultiply
    except ImportError:
        from Numeric import array,matrixmultiply
from xml.dom.minidom import Document
import copy
from KeyedVector import KeyedVector,DeltaRow,UnchangedRow,IncrementRow,ScaleRow,DiminishRow,SetToConstantRow,SetToFeatureRow,ActionCountRow,SetToDiffRow,SetToFeaturePlusRow
from Keys import Key,StateKey,keyDelete,keyConstant

class KeyedMatrix(dict):
    """A dictionary-based representation of a two-dimensional matrix
    @cvar defaultValue: the default value to insert into any missing positions
    @type defaultValue: C{float}
    @ivar _array: The numeric representation of this matrix
    @ivar _fresh: flag indicating whether there have been any changes to the array contents since the last update to the numeric array
    @type _fresh: C{boolean}
    @ivar _frozen: flag indicating whether the dimensions of this matrix are subject to change
    @type _frozen: C{boolean}
    @ivar _rowKeys: an ordered list of the indices of the rows of this matrix
    @type _rowKeys: L{Key}[]
    @ivar _rowOrder: a dictionary containing the row position of each key within the matrix
    @type _rowOrder: L{dict}(L{Key}:C{int})
    @warning: Use the L{set} method to set individual values.  Using built-in assignment calls (e.g., M[row][col] = 0.) will lead to inconsistencies.  If you can think of a clever way to enforce this in code, please feel free to do so.
    """
    defaultValue = 0.
    dimension = 2
    def __init__(self,args={}):
        dict.__init__(self)
        self._fresh = False
        self._frozen = False
        self._rowOrder = {}
        if len(args) > 0:
            # Grab all the row keys
            self._rowKeys = args.keys()
            self._rowKeys.sort()
            for index in range(len(args)):
                # Set all the row indices
                key = self._rowKeys[index]
                self._rowOrder[key] = index
            # Extract values
            values = []
            for rowKey in self._rowKeys:
                row = args[rowKey]
                dict.__setitem__(self,rowKey,row)
                rowValues = []
                for colKey in row.keys():
                    try:
                        rowValues.append(args[rowKey][colKey])
                    except KeyError:
                        rowValues.append(self.defaultValue)
                values.append(rowValues)
            self._array = array(values)
        else:
            self._rowKeys = []
            self._array = None

    def rowKeys(self):
        """
        @return: ordered list of the keys to all rows in this matrix
        @rtype: L{Key}[]
        """
        return self._rowKeys

    def colKeys(self):
        """
        @return: ordered list of the keys to all columns in this matrix
        @rtype: L{Key}[]
        """
        if len(self) == 0:
            return []
        else:
            return self.values()[0].keys()
        
    def colOrder(self,key):
        """
        @return: the position of the given key within the columns of this matrix
        @rtype: int
        """
        if len(self) == 0:
            raise ValueError,'No column %s in this matrix' % (str(key))
        else:
            try:
                return self.values()[0]._order[key]
            except KeyError:
                raise ValueError,'No column %s in this matrix' % (str(key))
            
    def set(self,row,col,value):
        """Sets an individual value in this matrix
        @param row,col: the keys for this value's position
        @type row,col: L{Key}
        @param value: the value to insert
        @type value: C{float}
        """
        self._fresh = False
##        self.addColumns([col])
        if not self._rowOrder.has_key(row):
            self.addRows([row])
        self[row][col] = value

    def rowPosition(self,key):
        """Finds the row position where this key should be inserted
        @param key: the key to insert
        @type key: L{Key}
        @return: the index to insert at
        @rtype: C{int}
        @warning: does not check whether key is already present
        """
        # Find the position for this key
        for index in range(len(self._rowOrder)):
            if key < self.rowKeys()[index]:
                break
        else:
            index = len(self._rowOrder)
        return index

    def addRows(self,keys,value=None):
        """Adds a new row slot to this matrix
        @param keys: the (sorted) keys for the new slots to insert
        @type keys: L{Key}[]
        @param value: the row to insert (defaults to a row of L{defaultValue})
        @type value: C{float}
        @warning: assumes that this row does not already exist
        """
        if self._frozen:
            raise UserWarning,'You are modifying a frozen matrix'
        self._fresh = False
        # Initialize values and find out which keys are missing
        newKeys = []
        newValues = {}
        for key in keys:
            if not self.has_key(key):
                newKeys.append(key)
                if value is None:
                    newValues[key] = KeyedVector()
                elif isinstance(value,KeyedVector):
                    if len(keys) > 1:
                        newValues[key] = copy.copy(value)
                    else:
                        newValues[key] = value
                elif isinstance(value,dict):
                    try:
                        newValues[key] = value[key]
                    except KeyError:
                        newValues[key] = KeyedVector()
                else:
                    # Can't really put anything else in here
                    newValues[key] = KeyedVector()
        # Nothing to do if there are no missing rows
#        print newKeys
        if len(newKeys) == 0:
            return
        # OK, let's build ourselves a new matrix
        finalOrder = {} # The key order for the resulting matrix
        finalKeys = []  # The ordered key list for the resulting matrix
        oldIndex = 0    # The pointer to the next old key to copy
        newIndex = 0    # The pointer to the next new key to insert
        # Insert all the new keys
        while newIndex < len(newKeys):
            # Insert all the old keys that come before this new key
            newKey = newKeys[newIndex]
            while oldIndex < len(self._rowKeys) and \
                      self._rowKeys[oldIndex] < newKey:
                # Copy an old key
                key = self._rowKeys[oldIndex]
                finalOrder[key] = len(finalKeys)
                finalKeys.append(key)
                oldIndex += 1
            # Copy the new key
            finalOrder[newKey] = len(finalKeys)
            finalKeys.append(newKey)
            dict.__setitem__(self,newKey,newValues[newKey])
            newIndex += 1
        while oldIndex < len(self._rowKeys):
            # Copy an old key
            key = self._rowKeys[oldIndex]
            finalOrder[key] = len(finalKeys)
            finalKeys.append(key)
            oldIndex += 1
        # Set the final results
        self._rowOrder = finalOrder
        self._rowKeys = finalKeys

    def isIdentity(self):
        """
        @return: C{True} iff this matrix is an identity matrix
        @rtype: boolean
        """
        for key in self.rowKeys():
            row = self[key]
            if not isinstance(row,UnchangedRow) or row.sourceKey != key:
                break
        else:
            return True
        return False
    
    def addColumns(self,keys,value=None):
        """Adds new column slots to this matrix
        @param keys: the (sorted) keys for the new slots to insert
        @type keys: L{Key}[]
        @param value: the column to insert (defaults to a row of L{defaultValue})
        @type value: C{float}
        """
        if self._frozen:
            raise UserWarning,'You are modifying a frozen matrix'
        self._fresh = False
        if value is None:
            value = self.defaultValue
        for row in self.values():
            row.addColumns(keys,value)
        
    def getArray(self):
        """
        @return: the numeric array representation of this matrix
        @rtype: C{array}
        """
        if not self._fresh:
            rowValues = map(lambda k:self[k].getArray(),self.rowKeys())
            self._array = array(rowValues)
            self._fresh = True
        return self._array
    
    def __setitem__(self,key,value):
        """@type key: L{Key} instance
        @type value: C{KeyedVector}"""
        assert(isinstance(value,KeyedVector))
        # Add any new keys from this new row
        self.addColumns(value.keys())
        # Add any missing keys in this new row
        value.addColumns(self.colKeys(),self.defaultValue)
        if self._rowOrder.has_key(key):
            self._fresh = False
            matrix = self.getArray()
            matrix[self._rowOrder[key]] = value.getArray()
            dict.__setitem__(self,key,value)
        else:
            self.addRows([key],value)

    def __delitem__(self,key):
        if self._frozen:
            raise UserWarning,'You are modifying a frozen matrix'
        self._fresh = False
        index = self._rowOrder[key]
        del self._rowOrder[key]
        for other in self._rowKeys[index+1:]:
            self._rowOrder[other] -= 1
        self._rowKeys.remove(key)
        dict.__delitem__(self,key)


    def deleteColumn(self,key):
        """Removes the specified column from the matrix
        @param key: the index for the column to remove
        @type key: L{Key}
        """
        if self._frozen:
            raise UserWarning,'You are modifying a frozen matrix'
        self._fresh = False
        for row in self.values():
            del row[key]
            
    def fill(self,keys,value=None):
        """Fills in any missing rows and columns with a default value
        @param keys: the new slots that should be filled
        @type keys: list of L{Key} instances
        @param value: the default value (default is L{defaultValue})
        @note: does not overwrite existing values, but does fill in values for missing existing keys
        """
        self.addRows(keys,value)
        self.addColumns(keys,value)

    def freeze(self):
        """Locks in the dimensions and keys of this matrix"""
        self._frozen = True
        for row in self.values():
            row.freeze()

    def unfreeze(self):
        """Unlocks the dimensions and keys of this matrix"""
        self._rowOrder = copy.copy(self._rowOrder)
        self._rowKeys = copy.copy(self._rowKeys)
        for row in self.values():
            row.unfreeze()
        self._frozen = False

    def compose(self,other,op):
        """Composes the two matrices together using the given operator
        @param other: the other matrix to compose with
        @type other: L{KeyedMatrix},float
        @param op: the operator used to generate the new array values
        @type op: C{lambda x,y:f(x,y)} where C{x} and C{y} are C{array} instances
        @rtype: a new L{KeyedMatrix} instance"""
        if isinstance(other,float):
            return self.copyFromArray(op(self.getArray(),other))
        else:
            return self.copyFromArray(op(self.getArray(),other.getArray()))
        
    def __add__(self,other):
        return self.compose(other,lambda x,y:x+y)

    def __sub__(self,other):
        return self + (-other)
    
    def __neg__(self):
        result = self.__class__()
        result._array = -(self.getArray())
        result._rowOrder = self._rowOrder
        result._rowKeys = self._rowKeys
        for key,row in self.items():
            dict.__setitem__(result,key,-row)
        if self._frozen:
            result.freeze()
        else:
            result.unfreeze()
        return result
        
    def __mul__(self,other):
        if isinstance(other,KeyedMatrix):
            return self._multiplyByMatrix(other)
        elif isinstance(other,KeyedVector):
            return self._multiplyByVector(other)
        else:
            return self._multiplyByOther(other)

    def _multiplyByMatrix(self,other):
        """Handles multiplication when multiplicand is two-dimensional
        @type other: L{KeyedMatrix}"""
        return self.copyFromArray(matrixmultiply(self.getArray(),
                                                 other.getArray()))

    def _multiplyByVector(self,other):
        """Handles multiplication when multiplicand is one-dimensional
        @type other: L{KeyedVector}"""
        result = KeyedVector()
        try:
            result._array = matrixmultiply(self.getArray(),other.getArray())
        except ValueError:
            raise UserWarning,'Your matrices are not aligned; perhaps use fill method to align'
        result._order = self._rowOrder
        result._orderedKeys = self._rowKeys
        result._fresh = None
        result._updateString()
        if self._frozen:
            result.freeze()
        else:
            result.unfreeze()
        return result

    def _multiplyByOther(self,other):
        """Handles multiplication when multiplicand is something unknown class (typically, C{float})
        """
        return self.copyFromArray(self.getArray() * other)

    def copyFromArray(self,matrix):
        """Copies all aspects of this array (keys, etc.) except for the numerical value, which is taken fom the given matrix
        @param matrix: the numerical value to use
        @type matrix: array
        @rtype: L{KeyedMatrix}
        """
        result = KeyedMatrix()
        result._array = matrix
        result._rowKeys = self._rowKeys
        result._rowOrder = self._rowOrder
        for rowKey,oldRow in self.items():
            row = KeyedVector()
            row._orderedKeys = oldRow._orderedKeys
            row._order = oldRow._order
            row._array = result._array[self._rowOrder[rowKey]]
            dict.__setitem__(result,rowKey,row)
        if self._frozen:
            result.freeze()
        else:
            result.unfreeze()
        return result
        
    def inverse(self):
        raise NotImplementedError,'Tell David to fix numpy reference'
#        from numpy.linalg.linalg import inv
#        return self.copyFromArray(inv(self.getArray()))
        
    def __hash__(self):
        """@warning: This is not cached, so repeated hashing may be inefficient"""
        return hash(str(self))

    def merge(self,other):
        """Merges rows from the two matrices (if any row keys are common, then the new row is used)
        @param other: the matrix to merge
        @type other: L{KeyedMatrix} instance
        @return: The new matrix
        @rtype: L{KeyedMatrix}
        """
        result = copy.copy(self)
        result.addRows(other.rowKeys(),other)
        return result

    def instantiate(self,table):
        """Substitutes values for any abstract references, using the
        given substitution table
        @param table: dictionary of key-value pairs, where the value will be substituted for any appearance of the given key in a field of this L{Key} object
        @type table: dictionary"""
        # Figure out all of the new key/row pairs
        newValues = {}
        for key,value in self.items():
            row = value.instantiate(table)
            newKey = key.instantiate(table)
            if isinstance(newKey,list):
                keyList = newKey
            elif newKey == keyDelete:
                keyList = []
            else:
                keyList = [newKey]
            for newKey in keyList:
                try:
                    newValues[newKey] += row
                except KeyError:
                    newValues[newKey] = row
        return KeyedMatrix(newValues)

    def instantiateKeys(self,table):
        """Substitutes values for any abstract references, using the
        given substitution table
        @param table: dictionary of key-value pairs, where the value will be substituted for any appearance of the given key in a field of this L{Key} object
        @type table: dictionary"""
        # Figure out all of the new key/row pairs
        newValues = {}
        for key,value in self.items():
            value.instantiateKeys(table)
            newKey = key.instantiate(table)
            if isinstance(newKey,list):
                keyList = newKey
            elif newKey == keyDelete:
                keyList = []
            else:
                keyList = [newKey]
            for newKey in keyList:
                try:
                    newValues[newKey] += value
                except KeyError:
                    newValues[newKey] = value
            dict.__delitem__(self,key)
        # Set up my new keys and values
        self._rowOrder.clear()
        self._rowKeys = newValues.keys()
        self._rowKeys.sort()
        for index in range(len(self._rowKeys)):
            key = self._rowKeys[index]
            dict.__setitem__(self,key,newValues[key])
            self._rowOrder[key] = index
    
    def __xml__(self):
        """@return: An XML Document object representing this matrix"""
        doc = Document()
        root = doc.createElement('matrix')
        doc.appendChild(root)
        for key,value in self.items():
            node = doc.createElement('row')
            root.appendChild(node)
            node.appendChild(key.__xml__().documentElement)
            node.appendChild(value.__xml__().documentElement)
        return doc

    def parse(self,element):
        """Extracts the distribution from the given XML element
        @param element: The XML object specifying the distribution
        @type element: Element
        @warning: modifies object in place; erases any previous contents of this matrix
        """
        self.clear()
        if element.tagName != 'matrix':
            raise UserWarning,'Expected matrix Element, but got %s instead' %\
                  element.tagName
        matrixType = str(element.getAttribute('type'))
        try:
            # Stored by label?
            cls = dynamicsTypes[matrixType]
        except KeyError:
            # Stored by class name?
            for cls in dynamicsTypes.values():
                if cls.__name__ == '%sMatrix' % (matrixType):
                    break
            else:
                # Stored in some incomprehensible manner?
                cls = self.__class__
        if not isinstance(self,cls):
            matrix = cls()
            return matrix.parse(element)
        else:
            matrix = self
        node = element.firstChild
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                for child in node.childNodes:
                    if child.nodeType != child.ELEMENT_NODE:
                        pass
                    elif child.tagName == 'vector':
                        row = KeyedVector()
                        row = row.parse(child)
                    elif child.tagName == 'key':
                        key = Key()
                        key = key.parse(child)
                    else:
                        msg = 'Unable to parse %s element of tag "%s"' % \
                              (matrix.__class__.__name__,child.tagName)
                        raise NotImplementedError,msg
                matrix[key] = row
            node = node.nextSibling
        return matrix
    
    def __str__(self):
        return self.simpleText()

    def simpleText(self):
        """
        @return: a more user-friendly string representation of this matrix
        @rtype: C{str}"""
        return '\n'.join(map(lambda k: '%s) %s' % (str(k),self[k].simpleText()),
                             self.rowKeys()))

    def __copy__(self):
        result = self.__class__()
        result._fresh = False
        result._rowOrder = copy.copy(self._rowOrder)
        result._rowKeys = copy.copy(self._rowKeys)
        for key,row in self.items():
            dict.__setitem__(result,key,row)
        return result
        
    def __deepcopy__(self,memo):
        result = self.__class__()
        memo[id(self)] = result
        result._fresh = False
        result._rowOrder = self._rowOrder
        result._rowKeys = self._rowKeys
        if self._frozen:
            result.freeze()
        else:
            result.unfreeze()
        for key,row in self.items():
            dict.__setitem__(result,key,copy.deepcopy(row,memo))
        return result
        
class DynamicsMatrix(KeyedMatrix):
    """Matrix subclass that provides some structure to be exploited for greater user friendliness"""
    rowClass = DeltaRow

    def __init__(self,source=None,key=None,value=0.):
        if key is None:
            key = keyConstant
        self.source = source
        if source:
            if isinstance(source,str):
                # Default is my state feature
                source = StateKey({'entity':'self','feature':source})
            row = self.rowClass(sourceKey=source,deltaKey=key,value=value)
            KeyedMatrix.__init__(self,{source:row})
        else:
            KeyedMatrix.__init__(self)

    def __copy__(self):
        new = KeyedMatrix.__copy__(self)
        new.source = self.source
        return new

    def __deepcopy__(self,memo):
        new = KeyedMatrix.__deepcopy__(self,memo)
        new.source = self.source
        return new

    def __xml__(self):
        """@return: An XML Document object representing this matrix"""
        doc = KeyedMatrix.__xml__(self)
        doc.documentElement.setAttribute('type',self.__class__.__name__[:-6])
        return doc
    
class IncrementMatrix(DynamicsMatrix):
    """A matrix for incrementing/decrementing the value of a given feature by a constant amount

    >>> matrix = IncrementMatrix('economicPower',value=0.1)
    """
    rowClass = IncrementRow

class ScaleMatrix(DynamicsMatrix):
    """A matrix for incrementing/decrementing the value of a given feature by some percentage of another feature (possibly the same one)

    >>> matrix = ScaleMatrix('economicPower',key,0.1)
    """
    rowClass = ScaleRow

class DiminishMatrix(DynamicsMatrix):
    """A matrix for incrementing/decrementing the value of a given feature by some percentage of 1 - another feature (possibly the same one)

    >>> matrix = DiminishMatrix('economicPower',key,0.1)
    """
    rowClass = DiminishRow

class SetToConstantMatrix(DynamicsMatrix):
    """A matrix for setting the value of a given feature to a specified constant value

    >>> matrix = SetToConstantMatrix(source='economicPower',value=0.)
    """
    rowClass = SetToConstantRow

class SetToFeatureMatrix(DynamicsMatrix):
    """A matrix for setting the value of a given feature to a specified percentage of some other feature

    >>> matrix = SetToFeatureMatrix(source='economicPower',key,value=0.5)
    """
    rowClass = SetToFeatureRow

class SetToDiffMatrix(DynamicsMatrix):
    """A matrix for setting the value of a given feature to a specified percentage of the difference between two features

    >>> matrix = SetToDiffMatrix(source='economicPower',[key1,key2],value=0.5)
    """
    rowClass = SetToDiffRow

class SetToFeaturePlusMatrix(DynamicsMatrix):
    """A matrix for setting the value of a given feature to a specified percentage of another feature plus a constant

    >>> matrix = SetToFeaturePlusMatrix(source='economicPower',[key,keyConstant],value=[1.0,0.1])
    """
    rowClass = SetToFeaturePlusRow

class ActionCountMatrix(DynamicsMatrix):
    """A matrix for setting the value of a given feature to a count of a certain type of action

    >>> matrix = ActionCountMatrix(source='economicPower',key,value=0.5)
    """
    rowClass = ActionCountRow

class IdentityMatrix(DynamicsMatrix):
    """A matrix for leaving the value of a given feature unchanged

    >>> matrix = IdentityMatrix('economicPower')
    """
    rowClass = UnchangedRow
    
def getDynamicsTypes():
    """Automatic extraction of possible L{DynamicsMatrix} subclasses
    @return: all available subclasses of L{DynamicsMatrix}
    @rtype: C{dict:str->class}
    """
    import inspect
    result = {}
    for value in globals().values():
        if inspect.isclass(value) and issubclass(value,DynamicsMatrix) and \
               not value is DynamicsMatrix:
            result[value.rowClass.label] = value
    return result
dynamicsTypes = getDynamicsTypes()

def makeIdentityMatrix(keys):
    """Generates an identity matrix, M, over the set of keys.  This matrix is filled and frozen.
    @param keys: the keys of the vector, v, for which we want M*v=v
    @type keys: L{Key}[]
    @rtype: L{KeyedMatrix}
    """
    matrix = KeyedMatrix()
    for key in keys:
        row = KeyedVector()
        row[key] = 1.
        matrix[key] = row
    matrix.fill(keys)
    matrix.freeze()
    return matrix
        
