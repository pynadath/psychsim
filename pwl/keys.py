
# Special keys
CONSTANT = ''
VALUE = '__VALUE__'
WORLD = '__WORLD__'
ACTION = '__ACTION__'
REWARD = '__REWARD__'
MODEL = '__MODEL__'
TURN = '__TURN__'

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
TERMINATED = stateKey(WORLD,'__END__')

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
    return stateKey(name,TURN)

def isTurnKey(key):
    return key[-(len(TURN)+3):] == '\'s %s' % (TURN)

def turn2name(key):
    return key[:-(len(TURN)+3)]

def actionKey(feature):    
    return '__action__%s__' % (feature)

def isActionKey(key):
    return isStateKey(key) and state2feature(key) == ACTION

def modelKey(name):
    return stateKey(name,MODEL)

def isModelKey(key):
    return key[-(len(MODEL)+3):] == '\'s %s' % (MODEL)

def model2name(key):
    return key[:-(len(MODEL)+3)]

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

def rewardKey(name):
    return stateKey(name,REWARD)

def isRewardKey(key):
    return isStateKey(key) and state2feature(key) == REWARD

def beliefKey(name,key):
    return '%s(%s)' % (name,key)

def isBeliefKey(key):
    return '(' in key

def belief2believer(key):
    return key[:key.index('(')]

def belief2key(key):
    return key[key.index('(')+1:-1]

def escapeKey(key):
    """
    @return: filename-ready version of the key
    """
    if not isinstance(key,str):
        key = str(key)
    future = isFuture(key)
    if future:
        key = makePresent(key)
    if isStateKey(key):
        agent = state2agent(key)
        if agent == WORLD:
            name = state2feature(key)
        else:
            name = '%sOf%s' % (state2feature(key),agent)
    else:
        name = key
    return name.replace(' ','')
