from teamwork.math.boltzmann import *

from LookaheadPolicy import *
from LookupAheadPolicy import *

import random
class StochasticLookahead(LookaheadPolicy):
    """A nondeterministic version of the lookahead-based policy, where
    actions are selected with a probability that is a function of
    their expected values."""
    # This policy's "temperature" constant for controlling the
    # probability distribution of actions.  Increasing values produce
    # a behavior closer to deterministic lookahead; decreasing values
    # produce a behavior closer to uniform randomness
    beta = 1.
    
    def execute(self,state,choices=[],debug=Debugger(),depth=-1):
        """Returns a randomly selected action out of the available
        choices, with each action selected with a probability
        dependent on its relative expected value"""
        # Compute the EV of each option
        values = self.evaluateChoices(state=state,choices=choices,
                                      debug=debug,depth=depth)
        # Compute the probability distribution
        for option in values.values():
            option['whole value'] = option['value']
            option['value'] = option['value'].total().mean()
        self.computeDistribution(values)
        for option in values.values():
            debug.message(7,'P(%s) = %4.3f' % (`option['decision']`,
                                               option['probability']))
        # Choose an action according to this distribution
        cutoff = random.random()
        total = 0.
        for option in values.values():
            total += option['probability']
            if total > cutoff:
                break
        # Return the selected action
        action = option['decision']
        del action['actor']
        explanation = {'options':values,
                       'value':option['whole value'],
                       'decision':action,
                       'actor':state.name,
                       'breakdown':option['breakdown'],
                       'effect':option['effect'],
                       'differential':0.}
        debug.message(9,'%s selects %s with Prob %4.3f' \
                      % (state.name,`action`,option['probability']))
        return action,explanation

    def computeDistribution(self,options):
        """Computes a probability distribution over the provided
        dictionary of action choices.  Each value in the dictionary
        must have a 'value' field containing a float.  This method
        computes a Boltzmann distribution based on these values and
        stores it in the 'probability' field of each entry.  Modify
        the 'beta' attribute on this object to vary the steepness of
        the distribution (0 is a uniform distribution, increasing
        values lead to deterministic behavior).  To use a different
        distribution altogether, simply override this method."""
        return prob(options,self.beta*float(len(options)))
