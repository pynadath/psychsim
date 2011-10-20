import time
from teamwork.math.KeyedVector import KeyedVector
from teamwork.math.probability import Distribution
from LookaheadPolicy import LookaheadPolicy
from pwlTable import PWLTable
    
class PWLPolicy(LookaheadPolicy):
    """
    Policy that uses L{PWLTable}s to store action rules
    """

    def __init__(self,entity,actions=None,horizon=None):
        """Same arguments used by constructor for L{LookupAheadPolicy} 
        superclass
        """
        if actions is None:
            actions = entity.actions.getOptions()
        if horizon is None:
            horizon = entity.horizon
        LookaheadPolicy.__init__(self,entity=entity,actions=actions,
                                 horizon=horizon)
        self.type = 'PWL'
        self.reset()

    def reset(self):
        """Removes any cached policy tables
        """
        self.tables = []

    def isEmpty(self):
        """
        @return: C{True} iff this policy is completely empty
        @rtype: bool
        """
        return len(self.tables) == 0

    def getDepth(self):
        """
        @return: the maximum belief depth supported by this policy
        @rtype: int
        """
        return len(self.tables)-1

    def getHorizon(self,depth=-1):
        """
        @param depth: the belief depth for which the horizon is requested (default is the maximum depth supported)
        @type depth: int
        @return: the maximum horizon supported by this policy at the given belief depth
        @rtype: int
        """
        try:
            return len(self.tables[depth])-1
        except IndexError:
            return 0

    def __getitem__(self,index):
        return self.execute(index)
    
    def execute(self,state=None,choices=[],debug=None,horizon=-1,explain=False,
                history=None):
        """Execute the policy in the given state
        @param horizon: the horizon to consider (by default, use the entity's given horizon)
        @type horizon: int
        @param choices: the legal actions to consider (default is all available actions)
        @type choices: L{Action<teamwork.action.PsychActions.Action>}[][]
        """
        if state is None:
            state = self.entity.getAllBeliefs()
        if horizon is None or horizon < 0:
            horizon = self.entity.horizon
        if self.tables and self.tables[-1]:
            try:
                table = self.tables[-1][horizon]
            except IndexError:
                table = self.tables[-1][-1]
            if isinstance(state,dict):
                state = state['state']
            if isinstance(state,Distribution):
                state = self.entity.entities.state2world(state)
            rhs = table[state]
        else:
            rhs = None
        if rhs is None:
            return LookaheadPolicy.execute(self,state,choices,debug,horizon,
                                           explain)
        elif rhs['rhs']:
            # Explicit RHS action
            return rhs['rhs'],rhs
        else:
            # Value function
            best = table.getRHS(state)
            # Find action from string
            for option in self.entity.actions.getOptions():
                if self.entity.makeActionKey(option) == best:
                    return option,rhs
            else:
                raise NameError,'Unable to find action %s' % (best)

    def reducePolicy(self):
        """Takes the currently active table and reduces it to a policy only (i.e., it strips off the value function
        """
        self.tables[-1][-1].prune(True)

    def project(self,R=None,depth=-1,horizon=-1,interrupt=None,debug=False):
        """
        Project the value function and policy one step further at the given depth
        @param R: the reward function in tabular form
        @type R: L{PWLTable}
        @param depth: the recursive belief depth to compute the value function for (default is deepest level already computed)
        @type depth: int
        """
        start = time.time()
        # Find policy at the specified depth (create one if none present)
        try:
            previous = self.tables[depth]
        except IndexError:
            if depth < 0:
                if len(self.tables) == abs(depth) - 1:
                    # Table at previous depth exists
                    self.tables.append([])
                else:
                    # Need to do intervening level first
                    self.project(R,depth+1,debug)
            else:
                while len(self.tables) < depth:
                    # Need to do intervening level first
                    self.project(R,depth-1,debug)
                else:
                    # Table at previous depth exists
                    self.tables.append([])
            previous = self.tables[depth]
        if horizon < 0:
            horizon += len(previous)
            horizon = max(0,horizon)
        # Project intermediate horizons
        while len(self.tables[depth]) < horizon:
            if interrupt and interrupt.isSet():
                return False
            self.project(R,depth,len(self.tables[depth]),interrupt,debug)
        if R is None:
            R = self.entity.getRewardTable()
        if debug:
            print 'Horizon = %d' % (horizon)
        # Compute new value function: V_a(b) = R(a,b) + ...
        V = R.getTable()
        if horizon > 0:
            # Transition to previous time step's value function
            if debug:
                print 'Computing V*...'
            for rule in previous[horizon-1].rules:
                assert len(rule['values']) == 3
            Vstar = previous[horizon-1].star()
            Vstar.prune(debug=debug)
            if debug:
                print 'V*'
                print Vstar
            if interrupt and interrupt.isSet():
                return False
            for omega,SE in self.entity.getEstimator().items():
                # ... + \sum_\omega V^*(SE_a(b,\omega))
                if debug:
                    print 'SE(b,%s)' % (omega)
                    print self.__str__(SE)
                    print 'Computing V*(SE(b,%s))...' % (omega)
                product = Vstar.__mul__(SE,debug=debug)
                if debug:
                    print 'V*(SE(b,%s))' % (omega)
                    print product
                if interrupt and interrupt.isSet():
                    return False
                V = V.__add__(product,debug=debug)
        # Compute policy
        if debug:
            print '\tMax (%d rules)' % (len(V))
            print V
        if interrupt and interrupt.isSet():
            return False
        policy = V.max(debug)
        try:
            previous[horizon] = policy
        except IndexError:
            previous.append(policy)
        # Replace string RHS with actual actions
        for rule in policy.rules:
            for option in self.entity.actions.getOptions():
                if self.entity.makeActionKey(option) == rule['rhs']:
                    rule['rhs'] = option
                    break
            else:
                raise NameError,'Unable to find RHS action "%s"' % (rule['rhs'])
        if debug:
            print str(self)
        print horizon,time.time()-start
        return True

    def getTable(self,depth=-1,horizon=-1,create=False):
        """
        @param depth: the recursive depth for the desired policy (default is maximum depth solved)
        @param horizon: the horizon for the desired policy (default is maximum horizon solved)
        @type depth, horizon: int
        @param create: if C{True}, then create an empty table if there is no existing policy for the specific parameters
        @type create: bool
        @return: a given policy table
        @rtype: L{PWLTable}
        """
        if create:
            while len(self.tables) <= depth:
                self.tables.append([])
            while len(self.tables[depth]) <= horizon:
                self.tables[depth].append(PWLTable())
        table = self.tables[depth][horizon]
        return table.getTable()
        
    def __str__(self,table=None):
        if table is None:
            table = self.getTable()
        content = str(table)
        for option in self.entity.actions.getOptions():
            content = content.replace(str(option),','.join(map(str,option)))
        return content
        
    def __xml__(self):
        doc = LookaheadPolicy.__xml__(self)
        for depth in range(len(self.tables)):
            for horizon in range(len(self.tables[depth])):
                table = self.tables[depth][horizon].__xml__().documentElement
                table.setAttribute('depth',str(depth))
                table.setAttribute('horizon',str(horizon))
                doc.documentElement.appendChild(table)
        return doc

    def parse(self,element):
        LookaheadPolicy.parse(self,element)
        node = element.firstChild
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                if node.tagName == 'table':
                    depth = int(node.getAttribute('depth'))
                    horizon = int(node.getAttribute('horizon'))
                    while len(self.tables) <= depth:
                        self.tables.append([])
                    while len(self.tables[depth]) <= horizon:
                        self.tables[depth].append(PWLTable())
                    self.tables[depth][horizon].parse(node)
            node = node.nextSibling
