
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
    :param future: if C{True}, then this refers to the projected value of this feature (default is C{False})
    :type future: bool
    :returns: a key representation of a given entity's state feature
    :rtype: str
    """
    assert isinstance(future,bool),'Future flag is non-boolean: %s' % (future)
    if future:
        return stateKey(name,feature)+"'"
    elif name is None:
        return feature
    else:
        return '%s\'s %s' % (name,feature)
TERMINATED = stateKey(WORLD,'__END__')

def isStateKey(key):
    """
    :returns: C{True} iff this key refers to a state feature
    :rtype: bool
    """
    return '\'s ' in key

def state2feature(key):
    """
    :returns: the feature string from the given key
    :rtype: str
    """
    index = key.find("'")
    if index < 0:
        return key
    else:
        return key[index+3:]

def state2agent(key):
    """
    :returns: the agent name from the given key
    :rtype: str
    """
    index = key.find("'")
    if index < 0:
        return None
    else:
        return key[:index]

def state2tuple(key):
    """
    :returns: the separated agent name and feature from the given key
    :rtype: (str,str)
    """
    index = key.find("'")
    if index < 0:
        return None
    else:
        return key[:index],key[index+3:]
    
def makePresent(key):
    """
    :returns: a reference to the given state features' current value
    :rtype: str
    """
    if isinstance(key,set):
        return {makePresent(k) for k in key}
    elif key[-1] == "'":
        return key[:-1]
    else:
        return key

def makeFuture(key):
    """
    :returns: a reference to the given state features' projected future value
    :rtype: str
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

def actionFieldKey(feature):    
    return '__action__%s__' % (feature)

def actionKey(name):
    return stateKey(name,ACTION)

def isActionKey(key):
    return isStateKey(key) and state2feature(key) == ACTION

def modelKey(name):
    return stateKey(name,MODEL)

def isModelKey(key):
    return key[-(len(MODEL)+3):] == '\'s %s' % (MODEL)

def model2name(key):
    return key[:-(len(MODEL)+3)]

def isSpecialKey(key):
    """
    :return: True iff the given key is a state key and its feature is a reserved name (e.g., for a turn, model, reward, etc)
    """
    return isStateKey(key) and state2feature(key)[:2] == '__'
    
def binaryKey(subj,obj,relation):
    return '%s %s -- %s' % (subj,relation,obj)

def isBinaryKey(key):
    return ' -- ' in key

def key2relation(key):
    sides = key.split(' -- ')
    first = sides[0].split()
    return {'subject': ' '.join(first[:-1]),
            'object': sides[1],
            'relation': first[-1]}

def likesKey(subj,obj):
    return binaryKey(subj,obj,'likes')

def isLikesKey(key):
    return ' likes -- ' in key

def rewardKey(name,future=False):
    return stateKey(name,REWARD,future)

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
    :returns: filename-ready version of the key
    """
    if not isinstance(key,str):
        key = str(key)
    if isBeliefKey(key):
        believer = belief2believer(key)
        subkey = belief2key(key)
        return 'Belief(%s)Of%s' % (escapeKey(subkey),believer)
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
