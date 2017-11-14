
# Special keys
CONSTANT = ''
TERMINATED = '__END__'
VALUE = '__VALUE__'
WORLD = '__WORLD__'
ACTION = '__ACTION__'

def stateKey(name,feature,future=False):
    """
    @param future: if C{True}, then this refers to the projected value of this feature (default is C{False})
    @type future: bool
    @return: a key representation of a given entity's state feature
    @rtype: str
    """
    if future:
        return stateKey(name,feature)+"'"
    elif name is None:
        return feature
    else:
        return '%s\'s %s' % (name,feature)

def isStateKey(key):
    """
    @return: C{True} iff this key refers to a state feature
    @rtype: bool
    """
    return '\'s ' in key

def state2feature(key):
    """
    @return: the feature string from the given key
    @rtype: str
    """
    index = key.find("'")
    if index < 0:
        return key
    else:
        return key[index+3:]

def state2agent(key):
    """
    @return: the agent name from the given key
    @rtype: str
    """
    index = key.find("'")
    if index < 0:
        return None
    else:
        return key[:index]
    
def makePresent(key):
    """
    @return: a reference to the given state features' current value
    @rtype: str
    """
    if isinstance(key,set):
        return {makePresent(k) for k in key}
    elif key[-1] == "'":
        return key[:-1]
    else:
        return key

def makeFuture(key):
    """
    @return: a reference to the given state features' projected future value
    @rtype: str
    """
    if key[-1] == "'":
        raise ValueError('%s is already a future key' % (key))
    else:
        return key+"'"

def isFuture(key):
    return len(key) > 0 and key[-1] == "'"

def turnKey(name):
    return stateKey(name,'_turn')

def isTurnKey(key):
    return key[-8:] == '\'s _turn'

def turn2name(key):
    return key[:-8]

def actionKey(feature):    
    return '__action__%s__' % (feature)

def modelKey(name):
    return stateKey(name,'_model')

def isModelKey(key):
    return key[-9:] == '\'s _model'

def model2name(key):
    return key[:-9]

def binaryKey(subj,obj,relation):
    return '%s %s -> %s' % (subj,relation,obj)

def isBinaryKey(key):
    return ' -> ' in key

def key2relation(key):
    sides = key.split(' -> ')
    first = sides[0].split()
    return {'subject': ' '.join(first[:-1]),
            'object': sides[1],
            'relation': first[-1]}

def likesKey(subj,obj):
    return binaryKey(subj,obj,'likes')

def isLikesKey(key):
    return ' likes -> ' in key
