 ###########################################################################
 # 11/5/2001: David V. Pynadath, USC Information Sciences Institute
 #            pynadath@isi.edu
 #
 # Policy: generic class for a policy of behavior
 # CompositePolicy: a generic class for a policy that merges a list of
 #           policy functions
 # GenericPolicy: a generic class for a policy that is specified as a
 #           table
 ###########################################################################

def strip(state):
    s = {}
    for key in state.keys():
        if key[0] != '_':
            s[key] = state[key]
    return s
	
class Policy:
    """Generic class for a policy of behavior"""
    
    def __init__(self,choices,type=None):
	self.choices = choices

    def execute(self,state,choices=[],debug=0):
        raise NotImplementedError

class CompositePolicy(Policy):
    """Generic class for a policy that merges a list of policy
    functions"""
    def __init__(self,choices,policyList):
        Policy.__init__(self,choices,'composite')
        self.subpolicies = policyList

    def extend(self,subpolicy):
        self.subpolicies.append(subpolicy)

    def execute(self,state,choices,debug=0):
        for subpolicy in self.subpolicies:
            choice = subpolicy.execute(state,choices,debug)
            if choice:
                return choice
        return None

    def actionValue(self,state,actStruct,debug=0):
        """Return expected value of performing action"""
        value = None
        for subpolicy in self.subpolicies:
            try:
                delta = subpolicy.actionValue(state,actStruct,debug)
                if value:
                    value = value + delta
                else:
                    value = delta
            except AttributeError:
                pass
        return value

    def copy(self):
        newPolicy = CompositePolicy(self.choices,[])
        for subpolicy in self.subpolicies:
            newPolicy.extend(subpolicy.copy())
        return newPolicy
    
    def __str__(self):
	str = ''
	for subpolicy in self.subpolicies:
	    str = str + '\nSubpolicy:\n\t'+`subpolicy`
	return str[1:]

# Example actionTable:
# {'action':'listen',
#  'table':[{'key':{'Tiger':'left'},
#            'action':'openright',
#            'table':[...]},
#           {'key':{'Tiger':'right'},
#            'action':'openleft',
#            'table':[{'key':{'Tiger':'reset'},
#                      'action':'listen',
#                      'table':[...]},...]},
#            ...]
# }
class GenericPolicy(Policy):
    """Generic class for a policy that is specified as a table"""
    def __init__(self,actionTable):
	self.table = actionTable
	Policy.__init__(self,[],'generic')

    def execute(self,state,choices,debug=0):
	entry = self.table
	beliefList = state[:]
	beliefList.reverse()
	for belief in beliefList:
	    table = entry['table']
	    for entry in table:
		if entry['key'] == strip(belief):
                    if entry['action'] in choices:
                        break
	    else:
		# Policy doesn't specify anything for this belief
		return None
	return entry['action']

    def getNodes(self,depth=-1,node=None):
	# If depth < 0, returns leaf nodes;
	# otherwise, returns nodes at depth specified
	if not node:
	    node = self.table
	try:
	    table = node['table']
	except KeyError:
	    return [node]
	if depth == 0:
	    return [node]
	elif depth > 0:
	    # Decrement depth to search
	    depth = depth - 1
	nodeList = []
	for node in table:
	    nodeList = nodeList + self.getNodes(depth,node)
	return nodeList
	
    def __str__(self):
	result = ''
	entry = self.table
	try:
	    result = result + self.printTable(entry['table'],0)
	except KeyError:
	    result = '<Empty policy>'
	return result

    def printTable(self,table,depth):
	str = ''
	for entry in table:
	    for index in range(depth):
		str = str + '\t'
	    str = str + `entry['key']` + ' -> ' + entry['action'] + '\n'
	    try:
		str = str + self.printTable(entry['table'],depth+1)
	    except KeyError:
		pass
	return str
