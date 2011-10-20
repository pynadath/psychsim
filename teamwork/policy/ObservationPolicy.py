from generic import *

class ObservationPolicy(Policy):
    """Policy that uses a lookup table, indexed by observation history
    @ivar Omega: list of possible observations
    @ivar entries: lookup table
    @ivar horizon: the maximum observation history that has been solved for (default is None)
    """
    
    def __init__(self,choices,observations,horizon=0):
        Policy.__init__(self,choices)
        self.Omega = observations[:]
        self.initialize(horizon)

    def initialize(self,horizon):
        """Sets the policy to the first policy in the ordered space
        """
        self.horizon = horizon
        self.entries = map(lambda n: 0,range(horizon+1))

    def next(self):
        """Increments this policy to the next one in the ordered space
        @return: C{True} if the next policy has been found; C{False} if reached the end of the policy space
        @rtype: bool
        """
        sizeA = len(self.choices)
        sizeOmega = len(self.Omega)
        pos = 0
        while True:
            try:
                self.entries[pos] += 1
            except IndexError:
                # Reached end of policy space
                return False
            if self.entries[pos] < pow(sizeA,pow(sizeOmega,pos)):
                break
            else:
                self.entries[pos] = 0
                pos += 1
        return True

    def execute(self,state=None,choices=[],debug=None,depth=-1,explain=False):
        """Execute the policy in the given state
        @param state: observation history
        @warning: Ignores C{choices} and C{depth} argument
        """
        try:
            policyIndex = self.entries[len(state)]
        except IndexError:
            # Haven't planned for an observation history this long
            length = len(self.entries)
            try:
                # Try most extensive policy found
                policyIndex = self.entries[-1]
            except IndexError:
                raise UserWarning,'No policy available'
            # Ignore oldest observations
            state = state[-length:]
        # Find entry for given observation history
        history = 0
        for omega in state:
            history *= len(self.Omega)
            if isinstance(omega,int):
                # Already an index
                history += omega
            else:
                # Convert symbol to index
                history += self.Omega.index(omega)
        # Index into policy using history
        action = (policyIndex / pow(len(self.choices),history)) \
            % (len(self.choices))
        return self.choices[action]

    def __str__(self,buf=None):
        if buf is None:
            import cStringIO
            buf = cStringIO.StringIO()
        sizeOmega = len(self.Omega)
        for horizon in range(len(self.entries)):
            # For each possible history length
            for history in range(pow(sizeOmega,horizon)):
                # For each possible history
                obs = []
                while len(obs) < horizon:
                    obs.insert(0,history % sizeOmega)
                    history /= sizeOmega
                print >> buf,map(lambda o:str(self.Omega[o]),obs),
                print >> buf,self.execute(obs)
        content = buf.getvalue()
        buf.close()
        return content

def solve(policies,horizon,evaluate,debug=False,identical=False):
    """Exhaustive search to find optimal joint policy over the given horizon
    @type policies: L{ObservationPolicy}[]
    @type horizon: int
    @param evaluate: function that takes this policy object and returns an expected value
    @type evaluate: lambda L{ObservationPolicy}: float
    @param identical: if C{True}, then assume that all agents use an identical policy (default is C{False})
    @type identical: bool
    @return: the value of the best policy found
    @rtype: float
    @warning: side effect of setting all policies in list to the best one found.  If you don't like it, too bad.
    """
    best = None
    for policy in policies:
        policy.initialize(horizon)
    done = False
    while not done:
        # Evaluate current candidate joint policy
        if debug:
            print 'Evaluating:',map(lambda p: str(p.entries),policies)
        value = evaluate(policies)
        if debug:
            print 'EV =',value
        if best is None or value > best['value']:
            if debug:
                print 'New best:'
                for policy in policies:
                    print '\t'+str(policy).replace('\n','\n\t')
            best = {'policy': map(lambda p: p.entries[:],policies),
                    'value': value}
        # Go on to next policy
        if identical:
            if policies[0].next():
                # Copy new policy over others
                for policy in policies[1:]:
                    policy.entries = policies[0].entries[:]
            else:
                # No more new policies to try
                break
        else:
            for index in range(len(policies)):
                policy = policies[index]
                if policy.next():
                    break
                else:
                    # Reached end of space for this policy
                    policy.initialize(horizon)
            else:
                # Gone through all combinations
                break
    # Update policy with best found
    for index in range(len(policies)):
        policies[index].entries = best['policy'][index]
    return best['value']

def solveExhaustively(scenario,transition,Omega,observations,evaluate,
                      horizon,identical=False,debug=False):
    """
    exhaustive search for optimal policy in given scenario
    """
    old = {}
    policies = []
    # Set up the initial observation-based policies
    for agent in scenario.members():
        actions = agent.actions.getOptions()
        if actions:
            old[agent.name] = agent.policy
            agent.policy = ObservationPolicy(actions,Omega.values())
            policies.append(agent.policy)
    # Phase 2: ?
    value = solve(policies,horizon,evaluate,identical=True)
    # Phase 3: Profit
    if debug:
        print value/float(horizon+1)
        for agent in scenario.members():
            if agent.actions.getOptions():
                print str(agent.policy)
                agent.policy = old[agent.name]
    return value

if __name__ == '__main__':
    import sys
    import time
    from teamwork.examples.TigerScenario import setupTigers,Omega,EV

    scenario,full,transition,reward,observations = setupTigers()

    for horizon in range(10):
        def evaluateJoint(policies):
            assert isinstance(scenario['Player 2'].policy,ObservationPolicy)
            return EV(scenario,transition,observations,reward,horizon)

        start = time.time()
        value = solveExhaustively(scenario,transition,Omega,observations,
                                  evaluateJoint,horizon,True)
        delta = time.time()-start
        print '%d,%f,%f' % (horizon,value/float(horizon+1),delta)
        sys.stdout.flush()
