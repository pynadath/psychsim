Modeling
========

   | "O brave new world,
   | That has such people in't."

      -- William Shakespeare (The Tempest, Act 5, Scene 1)


This is a world::

  from psychsim.world import World
  world = World()

A world has people::

  from psychsim.agent import Agent
  player = world.addAgent('Human')

And robots::

  robot = world.addAgent('Gort')

These are *agents*, because they have names::

  for name in world.agents:
     agent = world.agents[name]
     print(agent.name)


Of course, not everything that has a name is an agent. There are a number of reasons to make something an agent. The most common one is that something *is* an agent, i.e., an autonomous, decision-making entity. But there can be good reasons for modeling non-agents as agents within PsychSim, usually because of improved readability of simulation output. For example, in a search-and-rescue domain, we could denote even immobile victims as agents, for more fine-grained scoping of states, observations, rewards, etc.::

    victim = world.addAgent('Victim 1')  

Conversely, not every agent has to be modeled as an agent, especially if that agent's decision-making is not relevant to the target scenario. It does not necessarily cost anything to have extra agents in the scenario (if they do not get a *turn*, their decision-making procedure is never invoked). The choice of whether to make something an agent is yours.


State
-----

The *state* of a simulation captures the dynamic process by which it evolves. As in a *factored MDP*, we divide the state, :math:`\vec S`, into a set of orthogonal features, :math:`S_0\times S_1\times\cdots\times S_n`. Each feature captures a distinct aspect of the simulation state. 

Unary State Features
^^^^^^^^^^^^^^^^^^^^

It can be useful to describe a state feature as being local to an individual agent. Doing so does *not* limit the dependency or influence of the state feature in any way. However, it can be useful to define state features as local to an agent to make the system output more readable. For example, the following defines a state feature "location" for the previously defined human player agent::

   location = world.defineState(player.name,'location')

The return value of :py:meth:`~psychsim.world.World.defineState` is the unique symbol that PsychSim assigns to this newly defined state feature. To set the value for this state feature, you can either use this symbol with :py:meth:`~psychsim.world.World.setFeature`, the original agent/feature combination with :py:meth:`~psychsim.world.World.setState`, or the feature name with :py:meth:`~psychsim.agent.Agent.setState`. In other words, the following three statements interchangeably set the location of the human player to be Room 0::

  world.setFeature(location,0)
  world.setState(player.name,'location',0)
  player.setState('location',0)

For state features which are not local to any agent, a special agent name (i.e., :py:const:`~psychsim.pwl.keys.WORLD`) indicates that the state feature will pertain to the world as a whole. Again, from the system's perspective, this makes no difference, but it can be useful to distinguish global and local state in presentation::

   clock = world.defineState(WORLD,'time')
   world.setState(WORLD,'time',0)

Thus, one reason for creating an agent is to group a set of such state features under a common name, as opposed to leaving them as part of the global world state. For example, we can maintain the states of individual victims using our previously defined victim "agent"::

  world.defineState(victim.name,'location')
  victim.setState('location',3)


Binary State Features
^^^^^^^^^^^^^^^^^^^^^

There can also be state features that represent the *relationship* between two agents::

  trust = world.defineRelation(player.name,robot.name,'trusts')

The order in which the agents appear in this definition *does* matter, as reversing the order will generate a reference to a different element of the state vector. For example, if the previous definition corresponds to how much trust the human player places in its robot assistant, the following variation would correspond to how much trust the robot places in the human player::

   reciprocalTrust = world.defineRelation(robot.name,player.name,'trusts')

The values associated with these relationships can be read and written in the same way as for unary state features. However, there are no helper methods like :py:meth:`~psychsim.world.World.setState` or :py:meth:`~psychsim.agent.Agent.getState`. Rather, you should use the symbol returned by :py:meth:`~psychsim.world.World.defineRelation` in combination with :py:meth:`~psychsim.world.World.setFeature`::

   world.setFeature(trust,0.25)
   world.setFeature(reciprocalTrust,0.75)

Types of State Features
^^^^^^^^^^^^^^^^^^^^^^^

By default, a state feature is assumed to be real-valued, in :math:`[-1,1]`. However, these state features are one example of PsychSim's more general class of random variables. These variables support a variety of domains:

float
   real valued and continuous

int
   integer valued and discrete

bool
   a binary ``True``/``False`` value

list/set
   an enumerated set of possible values (typically strings)

By default, a variable is assumed to be float-valued, so the previous section's definitions of state features created only float-valued variables. Both the :py:meth:`~psychsim.world.World.defineState` and :py:meth:`~psychsim.world.World.defineRelation` methods take optional arguments to modify the domain of valid values of the feature. The following definition has the identical effect as the previous trust definition, but it makes the default values for the variable type and range of possible values explicit::

  trust = world.defineRelation(player.name,robot.name,'trusts',float,-1,-1)
  world.setFeature(trust,0.)

This relationship can now distinguish between a trusting and distrusting relationship (positive vs. negative values), with a fine-grained magnitude of the degree of (dis)trust. It is also possible to specify that a state feature has an integer-valued domain instead, such as for our numbered rooms::

   location = world.defineState(player.name,'location',int)
   player.setState('location',0)

One can also define a boolean state feature, where no range of values is necessary::

  alive = world.defineState(victim.name,'alive',bool)
  victim.setState('alive',True)

It is also possible to define an enumerated list of possible state features. Like all feature values, PsychSim represents these numerically within the actual state, but you do not need to ever use the numeric values::
             
   status = world.defineState(victim.name,'status',list,['unsaved','saved','dead'])
   victim.setState('status','unsaved')

Actions
-------

The most common reason for creating an agent is to represent an entity that can take *actions* that change the state of the world. If an entity has a deterministic effect on the world, you can define a single action for it. However, agents typically have multiple actions to choose from, and it is the decision among them that is the focus of the simulation.

Atomic Actions
^^^^^^^^^^^^^^

The `verb` of an individual action is a required field when defining the action::

   nop = player.addAction({'verb': 'doNothing'})

The action created will also have a `subject` field, representing the agent who is performing this action. The `subject` field is automatically filled in with the name of the agent ("Player 1" in the above example). A third optional field, `object`, can represent the target of the specific action::

   save = player.addAction({'verb': 'save','object': victim.name})
   move = player.addAction({'verb': 'moveTo','object': '1'})

An action's field values can be accessed in the same way as entries in a dictionary::

   if action['verb'] == 'save':
      print('%s has been saved by %s' % (action['object'],action['subject']))

You are free to define any other fields as well to contain other parameterizations of the actions::

  walk = player.addAction({'verb': 'moveTo','object': '1','speed': 1})
  run = player.addAction({'verb': 'moveTo','object': '1','speed': 10})

We will describe the use of these fields in :ref:`sec-dynamics`.

Action Sets
^^^^^^^^^^^

Sometimes an agent can make a decision that simultaneously combines multiple actions into a single choice::

  moveAndSave = player.addAction([{'verb': 'moveTo','object': '3'},
                                    {'verb': 'save','object': victim.name}])

For the purposes of the agent's decision problem, this option is equivalent to a single atomic action (e.g., move to room 3 and save the victim upon arrival). However, as we will see in :ref:`sec-dynamics`, separate atomic actions can sometimes simplify the definition of the effects of such a combined action.

The return value of :py:meth:`~psychsim.agent.Agent.addAction` is an :py:class:`~psychsim.action.ActionSet`, even if only one atomic :py:class:`~psychsim.action.Action` is specified. All of an agent's available actions are stored as a set of :py:class:`~psychsim.action.ActionSet` instances within an agent's :py:attr:`~psychsim.agent.Agent.actions`. An :py:class:`~psychsim.action.ActionSet` is a subclass of `set`, so all standard Python set operations apply::

   for action in free.actions:
      print(len(action))
   rejectAndAttack = reject | battle

By default, an agent can choose from all of its available actions on every turn. However, we may sometimes want to restrict the available action choices based on the current state of the world. We will cover how to specify such restrictions in :ref:`sec-legality`. As a result, rather than inspecting the :py:attr:`~psychsim.agent.Agent.actions` attribute itself, we typically examine the context-specific set of action choices instead::

   for action in player.getActions():
      if len(action) == 1:
         print(action['verb'])

The fragment above illustrates one helpful shortcut for :py:class:`~psychsim.action.ActionSet` instances: you can access fields within the member actions as long as all of the member actions have the same value for that field. In other words, ``moveAndSave['subject']`` would return ``'Player 1'``, but ``moveAndSave['verb']`` would raise an exception.

Probability
-----------

Maybe you already know this, but uncertainty is everywhere in social interaction. In particular, agents may not know what the true state of the world is, due to uncertain effects of actions and uncertain observations of those effects. As a result, :py:class:`~psychsim.probability.Distribution` objects are central to PsychSim's representations. Probability distributions can be treated as dictionaries, where the keys are the elements of the sample space, and the values are the probabilities associated with them. For example, we can represent a fair coin with the following distribution::

  coin = Distribution({'heads': 0.5, 'tails': 0.5})
  if coin.sample() == 'heads':
     print('You win!')

If you happen to lose enough that you suspect that the coin is in fact *not* fair, then you can update your beliefs by changing the distribution::

  coin['heads'] = 0.25
  coin['tails'] = 0.75

If you want to know the probability that the coin lands on its edge, ``coin['edge']`` would throw an exception, while ``coin.get('edge')`` would return 0. To account for the nonzero probability that the coin lands on its edge, you must explicitly add such a probability::

  coin['edge'] = 1e-8
  coin.normalize()
  for element in coin.domain():
     print(coin[element])

Possible Worlds
---------------
As already mentioned, PsychSim uses a factored representation, so that a state of the world is expressed as a probability distribution over possible feature-value pairs. More precisely, instead of distributions over arbitrary elements, the state of a PsychSim world is represented as a :py:class:`~psychsim.pwl.state.VectorDistributionSet` that represents a probability distribution over possible worlds::

  world.setState(victim.name,'location',Distribution({1: 0.25, 3: 0.75}))
  world.setState(victim.name,'status',Distribution({'alive': 0.9, 'dead': 0.1}))

These statements specify uncertainty about the victim's location (probably Room 3 but maybe Room 1) and status (most likely alive, with a small chance of being dead). These two state features have independent distributions within the state. Thus, there is a 2.5% chance that the victim is lying dead in Room 1.

Piecewise Linear (PWL) Functions
--------------------------------
As already mentioned, the effects of actions and the observations of those actions are critical components of any agent model (the transition probability, *P*, and observation functions, *O*, respectively, from POMDPs). In theory, we could allow for arbitrary functions for action effects and observations, but we instead restrict the functions to be piecewise linear (PWL). As we see from examples like Algebraic Decision Diagrams in the literature, it is useful to impose additional structure on the sample space to facilitate authoring, simulation, and understanding. 

At its heart, these effects are specified as matrices that transform one state vector into another. A PWL function is a decision tree with such matrices at its leaves and hyperplanes at its branches.

If we want to instead specify that Freedonia has 25000 troops if and only if it is the winner, then we specify a joint probability over `winner` and `troops`. To do so, we use a :py:class:`~psychsim.pwl.vector.KeyedVector` to represent elements of the joint sample space::

  freeVictory = KeyedVector({stateKey(WORLD,'winner'): 'Freedonia',
                             stateKey(free.name,'troops':): 25000})
  sylvVictory = KeyedVector({stateKey(WORLD,'winner'): 'Sylvania',
                             stateKey(free.name,'troops':): 10000})

over possible worlds. Thus, even though the above method call specificies a single value, the value is internally represented as a distribution with a single element (i.e., 40000) having 100% probability. We can also pass in a distribution of possible values for a state feature::


The :py:class:`~psychsim.probability.Distribution` constructor takes a dictionary whose keys constitute the distribution's sample space, and whose values constitte the probability mass of each element of that space. In the above example, the distribution over Freedonia's cost is 50-50 between 1000 and 2000. When you call the :py:meth:`~psychsim.world.World.setState` method with a probabilistic value, PsychSim *joins* the new distribution with the current state vector. After the previous two :py:meth:`~psychsim.world.World.setState` calls, there will be two possible worlds, each with 50% probability: one where Freedonia has 40000 troops and cost 1000, and a second where Freedonia has 40000 troops and cost 2000. Just as the second call doubles the number of possible worlds, a subsequent call to :py:meth:`~psychsim.world.World.setState` with a probabilistic value will similarly increase the number of possible worlds by a factor equal to the size of the distribution passed in. In other words, calling :py:meth:`~psychsim.world.World.setState` will generate worlds for all possible combinations of the individual values for the state features.

If you would like more fine-grained control over the possible worlds, simply manipulate the distribution directly. Note that the world state is potentially a dictionary of distributions over worlds, although until further development occurs, the only entry in that table is indexed by {\tt None}:::

   possworld1 = KeyedVector({stateKey(free.name,'troops'): 40000, 
                             stateKey(free.name,'cost'): 1000})
   possworld2 = KeyedVector(possworld1)
   possworld2[stateKey(free.name,'cost')] = 2000
   possworld3 = KeyedVector()
   possworld3[stateKey(free.name,'troops')] = 25000
   possworld3[stateKey(free.name,'cost')] = 2000

   world.state[None].clear()
   world.state[None][possworld1] = 0.1
   world.state[None][possworld2] = 0.4
   world.state[None][possworld3] = 0.5

When querying for a given state feature, the returned value is *always* in :py:class:`~psychsim.probability.Distribution` form.::

   value = world.getState(free.name,'phase')
   for phase in value.domain():
      print 'P(%s=%s) = %5.3f' % (stateKey(free.name,'phase'),
                                  phase,value[phase])

The :py:func:`~psychsim.pwl.keys.stateKey` function is useful for translating an agent (or the world) and state feature into a canonical string representation::

   from psychsim.pwl import *
   s = KeyedVector({'S_0': 0.3, 'S_1': 0.7})
   s['S_n'] = 0.4
   for key in s:
      print(key,s[key])

Notice that PsychSim allows you to refer to each feature by a meaningful *key*, as in Python's dictionary keys. Keys are treated internally as unstructured strings, but you may find it useful to make use of the the following types of structured keys.

PsychSim uses piecewise linear (PWL) functions to structure the dependencies among variables, as we will see in later sections. While the PWL structure limits the expressivity of these dependencies, it provides a more human-readable language (as opposed to arbitrary code) and, more importantly, provides invertibility that is essential for automatic fitting and explanation.

We have already seen the basic building block of the PWL functions, the {\tt KeyedVector}. 

.. _sec-legality:

Legality
^^^^^^^^

Legality::

   tree = makeTree({'if': equalRow(stateKey(WORLD,'phase'),'offer'),
                    True: True,    
                    False: False})
   free.setLegal(action,tree)

.. _sec-dynamics:

Dynamics
^^^^^^^^

Termination
^^^^^^^^^^^

*Termination* conditions specify when scenario execution should reach an absorbing end state (e.g., when a final goal is reached, when time has expired). A termination condition is a PWL function (Section \ref{sec:pwl}) with boolean leaves.::

   world.addTermination(makeTree({'if': trueRow(stateKey(WORLD,'treaty')),
                                  True: True, False: False}))

This condition specifies that the simulation ends if a "treaty" is reached. Multiple conditions can be specified, with termination occurring if any condition is true.


Reward
------

An agent's *reward* function represents its (dis)incentives for choosing certain actions. In other agent frameworks, this same component might be referred to as the agent's *utility* or *goals*. It is often convenient to separate different aspects of the agent's reward function::

    goalFTroops = maximizeFeature(stateKey(free.name,'troops'))
    free.setReward(goalFTroops,1.)
    goalFTerritory = maximizeFeature(stateKey(free.name,'territory'))
    free.setReward(goalFTerritory,1.)

Models
------

A *model* in the PsychSim context is a potential configuration of an agent that may apply in certain worlds or decision-making contexts. All agents have a "True" model that represents their real configuration, which forms the basis of all of their decisions during execution. 


It also possible to specify alternate models that represent perturbations of this true model, either to represent the dynamics of the agent's configuration or to represent the perceptions other agents have of it::

   free.addModel('friend')

Model Attribute: `static`
^^^^^^^^^^^^^^^^^^^^^^^^^

Observations
------------
