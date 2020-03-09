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
  health = world.defineState(victim.name,'health')
  world.setFeature(health,1)


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

By default, a variable is assumed to be float-valued, so the previous section's definitions of state features created only float-valued variables. Both the :py:meth:`~psychsim.world.World.defineState` and :py:meth:`~psychsim.world.World.defineRelation` methods take optional arguments to modify the domain of valid values of the feature. The following definition has the identical effect as the previous  definitions of these variables, but it makes the default values for the variable type and range of possible values explicit::

  health = world.defineState(victim.name,'health',float,0,1)
  world.setFeature(health,1)
  trust = world.defineRelation(player.name,robot.name,'trusts',float,-1,1)
  world.setFeature(trust,0)

This relationship can now distinguish between a trusting and distrusting relationship (positive vs. negative values), with a fine-grained magnitude of the degree of (dis)trust. It is also possible to specify that a state feature has an integer-valued domain instead, such as for our numbered rooms::

   location = world.defineState(player.name,'location',int)
   player.setState('location',0)

One can also define a boolean state feature, where no range of values is necessary::

  alive = world.defineState(victim.name,'alive',bool)
  victim.setState('alive',True)

It is also possible to define an enumerated list of possible state features. Like all feature values, PsychSim represents these numerically within the actual state, but you do not need to ever use the numeric values::
             
   status = world.defineState(victim.name,'status',list,['unsaved','saved','dead'])
   victim.setState('status','unsaved')

Probability
^^^^^^^^^^^

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
^^^^^^^^^^^^^^^
As already mentioned, PsychSim uses a factored representation, so that a state of the world is expressed as a probability distribution over possible feature-value pairs. More precisely, instead of distributions over arbitrary elements, the state of a PsychSim world is represented as a :py:class:`~psychsim.pwl.state.VectorDistributionSet` that represents a probability distribution over possible worlds::

  world.setState(victim.name,'location',Distribution({1: 0.25, 3: 0.75}))
  world.setState(victim.name,'status',Distribution({'alive': 0.9, 'dead': 0.1}))

These statements specify uncertainty about the victim's location (probably Room 3 but maybe Room 1) and status (most likely alive, with a small chance of being dead). These two state features have independent distributions within the state. Thus, there is a 2.5% chance that the victim is lying dead in Room 1.

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

   for action in player.actions:
      print(len(action))
   quickSave = run | save

By default, an agent can choose from all of its available actions on every turn. However, we may sometimes want to restrict the available action choices based on the current state of the world. We will cover how to specify such restrictions in :ref:`sec-legality`. As a result, rather than inspecting the :py:attr:`~psychsim.agent.Agent.actions` attribute itself, we typically examine the context-specific set of action choices instead::

   for action in player.getActions():
      if len(action) == 1:
         print(action['verb'])

The fragment above illustrates one helpful shortcut for :py:class:`~psychsim.action.ActionSet` instances: you can access fields within the member actions as long as all of the member actions have the same value for that field. In other words, ``moveAndSave['subject']`` would return ``'Player 1'``, but ``moveAndSave['verb']`` would raise an exception.

Piecewise Linear (PWL) Functions
--------------------------------
As already mentioned, the effects of actions and the observations of those actions are critical components of any agent model (the transition probability, *P*, and observation functions, *O*, respectively, from POMDPs). In theory, we could allow for arbitrary functions for action effects and observations, but we instead restrict the functions to be piecewise linear (PWL). As we see from examples like Algebraic Decision Diagrams in the literature, it is useful to impose additional structure on the sample space to facilitate authoring, simulation, and understanding. 

At its heart, these effects are specified as matrices that transform one state vector into another. A PWL function is a decision tree with such matrices at its leaves and hyperplanes at its branches. If we again take :math:`S_0\times S_1\times\cdots\times S_n` to represent our state, then our PWL function building blocks are linear functions of the form :math:`S_i'\leftarrow\sum_{j=0}^n w_{ij}\cdot S_j`, specifying a new value for :math:`S_i` in terms of a set of weights :math:`w_{ij}`. The branches are similarly linear, testing whether :math:`\sum_{j=0}^n w_{j}\cdot S_j>\theta`. We canonically take :math:`S_0` to be a variable whose value is always 1.

Given the readable names we have given to our state features, it would be barbaric to use integer indices for the weights in these linear functions. We instead use a :py:class:`~psychsim.pwl.vector.KeyedVector` that allows us to specify weights using the same string keys we use to set the values of the state itself (:math:`S_0` can be accessed via the special string key, :py:const:`~psychsim.pwl.keys.CONSTANT`). For example, we can specify linear weights that increment the world clock as follows::

  KeyedVector({stateKey(WORLD,'time'): 1, CONSTANT: 1})

We can also use strings that we have previously enumerated as possible values for a state feature, as in the following function that would specify a status of "saved"::

  KeyedVector({CONSTANT: 'saved'})

Matrices
^^^^^^^^
A linear function is not much use unless we can specify where the value returned by the function should go. We again use our string keys as indices into a matrix, each pointing to a :py:class:`~psychsim.pwl.vector.KeyedVector` that represents the linear function generating the new value for a given state feature. However, we first introduce distinct keys for the original and new values of a given variable::

  newLocation = makeFuture(stateKey(victim.name,'status'))
  newLocation = stateKey(victim.name,'status',future=True)

Both usages are interchangeable. We can now define a :py:class:`~psychsim.pwl.matrix.KeyedMatrix` that represents a change of a victim's status to "saved"::

  KeyedMatrix({makeFuture(status): KeyedVector({CONSTANT: 'saved'})})

We can also represent a teleport effect that allows the player to move immediately to the victim's location::

  KeyedMatrix({makeFuture(location): KeyedVector({stateKey(victim.name,'location'): 1})})

Note that this effect moves the player to the victim's original location. If the victim is moving at the same time as the player, we can specify that the player teleports to the victim's *new* location instead::

  KeyedMatrix({makeFuture(location): KeyedVector({stateKey(victim.name,'location',future=True): 1})})

Arbitrary linear functions of this form are allowed, but there are several often-used structures that are often repeated and that have been codified into "helper functions".

* :py:class:`~psychsim.pwl.matrix.setToConstantMatrix` specifies a constant to be used as the new value for a given variable. The first example in this subsection could be more compactly rewritten as::

    setToConstantMatrix(status,'saved')

* :py:class:`~psychsim.pwl.matrix.setToFeatureMatrix` specifies another variable whose value should be taken as the new value for the given variable. The second example in this subsection (using the victim's new location) could be more compactly rewritten as::

    setToFeatureMatrix(location,stateKey(victim.name,'location',True)

* :py:class:`~psychsim.pwl.matrix.incrementMatrix` specifies a constant to be added to the old value of the given variable. The first example in this section could be more compactly rewritten as::

    incrementMatrix(stateKey(WORLD,'time'),1)

* :py:class:`~psychsim.pwl.matrix.addFeatureMatrix` specifies another variable whose value is to be added to the old value of the given variable. The following shifts the player's location by its current speed (possibly updated by the most recent set of actions)::

    addFeatureMatrix(location,stateKey(player.name,'speed',True))

  There is an optional third argument that specifies a scaling factor of the other variable (the default is 1). The following specifies that the victim's health should increase by 80% of the player's healing power::

    addFeatureMatrix(health,stateKey(player.name,'power'),0.8)

* :py:class:`~psychsim.pwl.matrix.scaleMatrix` specifies a constant factor that the old value of the given variable should be multiplied by. The following specifies an effect that reduces the victim's health level by a quarter::

    scaleMatrix(health,0.75)

* :py:class:`~psychsim.pwl.matrix.approachMatrix` specifies that the given variable should move closer to the specified constant limit by a fixed percentage. The following specifies an effect that the victim's health level gets 25% closer to its maximum value of 1::

    approachMatrix(health,0.25,1)

  The following specifies the exact same effect as our :py:class:`~psychsim.pwl.matrix.scaleMatrix` example::

    approachMatrix(health,0.25,0)

  :py:class:`~psychsim.pwl.matrix.approachMatrix` takes an optional fourth argument that specifies another variable that should be used by the limit (the default is naturally :py:const:`~psychsim.pwl.keys.CONSTANT`). The following specifies that the victim's health should move 25% closer to 90% of a different victim's up-to-the-minute health level::

    approachMatrix(health,0.25,0.9,stateKey(healthierVictim.name,'health',True))

* :py:class:`~psychsim.pwl.matrix.setTrueMatrix` and :py:class:`~psychsim.pwl.matrix.setFalseMatrix` are special cases of :py:class:`~psychsim.pwl.matrix.setToConstantMatrix` that are used for Boolean variables. The following represent equivalent effects of death and resurrection of our victim:: 

    setFalseMatrix(alive)
    setToConstantMatrix(alive,False)

    setTrueMatrix(alive)
    setToConstantMatrix(alive,True)

* :py:class:`~psychsim.pwl.matrix.noChangeMatrix` is true to its name and specifies that the value of the given variable does not change. The following makes time stand still::

    noChangeMatrix(stateKey(WORLD,'time'))

* :py:class:`~psychsim.pwl.matrix.dynamicsMatrix` is a convenience wrapper for arbitrary weights (in the form of a :py:class:`~psychsim.pwl.vector.KeyedVector`). We leave understanding the meaning of the following as an exercise for the reader::

    dynamicsMatrix(health,KeyedVector({stateKey(player,'power'): 0.2,stateKey('fire','intensity'): -0.4,health: 1}))

Hyperplanes
^^^^^^^^^^^
If your agents live in a perfectly linear world, then these matrices are sufficient for your modeling purposes. However, most nontrivial domains have some nonlinearities. PsychSim supports a declarative representation of *piecewise* linear functions, allowing for different matrices to specify the output across different inputs. To specify what we mean by "different inputs", we use a :py:class:`~psychsim.pwl.plane.KeyedPlane`, that contains a :py:class:`~psychsim.pwl.vector.KeyedVector` specifying the weights on the hyperplane, a threshold, and a comparison to use between the weighted sum and the threshold. For example, the following specifies a hyperplane that tests whether the victim's health is below 1%::

  KeyedPlane(KeyedVector({health: 1.},0.01,2))

The first argument is the set of weights that implies a weighted sum over the variables that returns simply the victim's health. The second argument is the threshold to compare that weighted sum against (1%). And the third argument is a rather opaque way of specifying that the comparison should be a "strictly less than". In other words, this hyperplane test returns ``True`` if and only if the weighted sum (the victim's health) is < 0.01. If the third argument is omitted, it is assumed to be 1, corresponding to a "strictly greater than" comparison. A value of 0 corresponds to an equality test.  

As with the matrices, there are several helper functions that more easily express commonly used hyperplane structures.

* :py:class:`~psychsim.pwl.plane.thresholdRow` is one of the most commonly used, testing whether the given variable is strictly greater than a constant threshold. The following tests whether the player's healing power > 0.6::

    thresholdRow(stateKey(player.name,'power'),0.6)

* :py:class:`~psychsim.pwl.plane.greaterThanRow` is similar, but it tests whether the given variable is strictly greater than the value of another variable. The following tests whether the victim might actually be better off than the player::

    greaterThanRow(health,stateKey(player.name,'health'))

* :py:class:`~psychsim.pwl.plane.equalRow` tests whether the given variable equals the specified constant value. It is not recommended for continuous-valued variables, but works like a charm for integers or enumerated variables. For example, the following tests whether the victim has yet to be saved::

    equalRow(status,'unsaved')

* :py:class:`~psychsim.pwl.plane.equalFeatureRow` tests whether the given variable has the same value as another variable. Like :py:class:`~psychsim.pwl.plane.equalRow`, it is not recommended for continuous-valued variables, but is intended for integers or enumerated variables. For example, the following tests whether our victim's status has stayed the same over the current time step::

    equalFeatureRow(status,makeFuture(status))

* :py:class:`~psychsim.pwl.plane.trueRow` is used for Boolean variables, returning ``True`` if and only if the given variable is also ``True``. The following test whether the victim is alive::

    trueRow(alive)

* :py:class:`~psychsim.pwl.plane.differenceRow` compares the values of two variables, :math:`S_i` and :math:`S_j` and returns ``True`` if and only if :math:`S_i-S_j>\theta`. The following tests whether our victim's health has increased over the current time step::

    differenceRow(makeFuture(health),health,0)

* :py:class:`~psychsim.pwl.plane.andRow` tests a conjunction over Boolean variables (possibly negated) and returns ``True`` if and only if all of them have the desired value. The arguments are two lists: the first of variables that need to be ``True`` and the second of variables that need to be ``False``. The following returns ``True`` if and only if our victim is the only one alive out of some list of victim names::

    andRow([alive],[stateKey(name,'alive') for name in victimList if name != victim.name])

All of the planes presented so far have been binary tests. While combining such tests can achieve arbitrary levels of complexity, it can be simpler and more readable to have tests against multiple values simultaneously (i.e., parallel hyperplanes). To do so, you can provide multiple thresholds to test against, within the same instance. For example, an :py:class:`~psychsim.pwl.plane.equalRow` can take a list of possible values, returning the index of the value to which the variable is currently equal to::

  equalRow(status,['unsaved','saved','dead'])

This row will evaluate to 0 if the victim's current status is "unsaved", 1 if "saved", and 2 if "dead". If the victim's current status is some value not in the list of values provided (not possible in this case, but you get the idea), then the row evaluates to `None`. An analogous :py:class:`~psychsim.pwl.plane.thresholdRow` returns an index based on which interval the variable lies, where the intervals are defined by a provided list of thresholds::

  thresholdRow(health,[0.25,0.5,0.75])

This plane will return 0 if and only if the victim's health is :math:`\leq 0.25`, 1 if :math:`>0.25` and :math:`\leq 0.5`, 2 if :math:`>0.5` and :math:`\leq 0.75`, and 3 otherwise.  

Equality tests also support sets of possible values, in which case, the test is whether the variable equals any of the values in the set::

  equalRow(status,{'unsaved','dead'})

This instance returns `True` if and only if the victim is either "unsaved" or "dead". All planes support lists and sets of thresholds in the same way as :py:class:`~psychsim.pwl.plane.equalRow`, by testing whether the weighted sum equals any of the values in the list or set. 

It is also possible to combine hyperplanes that are not parallel. A single :py:class:`~psychsim.pwl.plane.KeyedPlane` object can contain multiple hyperplanes and represent either a disjunction or conjunction over their individual tests. The easiest way to create such a test is to add the individual hyperplanes together. The following creates a test on whether all victims have been saved::

    planes = [equalRow(stateKey(name,'status'),'saved') for name in victimList]
    allSaved = planes[0]
    for plane in planes[1:]:
      allSaved += plane

This creates a conjunction over the individual planes. Creating a disjunction instead is a bit clunkier::


    planes = [equalRow(stateKey(name,'status'),'saved') for name in victimList]
    allSaved = planes[0]
    allSaved.isConjunction = False
    for plane in planes[1:]:
      plane.isConjunction = False
      allSaved += plane

Helper functions that encapsulate these two combinations are relatively easy to write (HINT, HINT).


.. _sec-trees:

Trees
^^^^^
The hyperplanes and matrices form the building blocks for the decision-tree representation of PWL functions. These decision trees are instances of :py:class:`~psychsim.pwl.tree.KeyedTree`, which has many methods for building up such trees from the leaves up. However, it is recommended that you instead use :py:class:`~psychsim.pwl.tree.makeTree`. For trees with no branches, you can pass the value to be stored in the single leaf node directly. The following creates a tree consisting of a single leaf node specifying that the victim's health drops by 10%::

  makeTree(approachMatrix(health,0.1,0))

We can introduce a nonlinearity by passing in a dictionary with one "if" entry, containing a hyperplane, and other entries corresponding to the child trees corresponding to the result of evaluating that hyperplane. For example, we can use the following invocation to create a tree where the victim's health increase if the player ends up in the same room::

  makeTree({'if': equalFeatureRow(makeFuture(location)),stateKey(victim.name,'location',True),
    True: approachMatrix(health,0.1,1),
    False: approachMatrix(health,0.1,0)})

The dictionaries can be nested in the same way you wish the final tree to be nested. For example, we may want the player's impact on the victim's health to be a function of healing power::

  makeTree({'if': equalFeatureRow(makeFuture(location)),stateKey(victim.name,'location',True),
    True: {'if': thresholdRow(stateKey(player.name,'power',True), 0.5),
      True: approachMatrix(health,0.2,1),
      False: approachMatrix(health,0.1,1)},
    False: approachMatrix(health,0.1,0)})

One can use nonbinary tests in the "if" branch as well. For example, the victim's status could contribute to the player's score as follows::

  makeTree({'if': equalRow(makeFuture(status),['saved','unsaved','dead']),
    0: incrementMatrix(stateKey(player.name,'score'),10),
    1: noChangeMatrix(stateKey(player.name,'score')),
    2: incrementMatrix(stateKey(player.name,'score'),-25)})

At this point, you may be wondering where all our probabilities went. To specify a stochastic effect, your dictionary uses a "distribution" entry, instead of an "if". The value of the "distribution" is a list of tuples, with each tuple pairing a subtree (or leaf value) with a probability. The following represents uncertainty in the player's ability to save a victim, dependent on the player's healing power::

  stochTree = makeTree({'if': thresholdRow(stateKey(player.name,'power'),0.5),
    True: {'distribution': [(setToConstantMatrix(status,'saved'),0.75),
      (noChangeMatrix(status),0.25)]},
    False: {'distribution': [(setToConstantMatrix(status,'saved'),0.5),
      (noChangeMatrix(status),0.5)]}})

In this tree, the player has a 75% chance of saving the victim if its healing power is greater than 0.5, but only a 50% chance otherwise.

.. _sec-dynamics:

Transition Probability
^^^^^^^^^^^^^^^^^^^^^^
The main use of PWL functions is in specifying the dynamics of the world, i.e., the effects of actions on the state of the world. All of the examples used in Section :ref:`sec-trees` are examples of such PWL functions. To specify when a particular function should be used, you specify the action-state combination to which the effect applies::

  world.setDynamics(status,save,stochTree)

If there is an effect you would like to trigger on every time step, regardless of what actions are chosen, you can use `True`, instead of a specific action. The following might be a good way to update your clock::

  world.setDynamics(clock,True,makeTree(incrementMatrix(clock)))

If there is an effect you would like to never happen, you can use `False` instead. Or you could, you know, not do anything, and the result would be the same.

.. _sec-legality:

Legality
^^^^^^^^

By default, an agent's action space is the same on each time step, allowing it choose from any of its defined actions, regardless of the state of the world. It can be useful to have the agent disregard certain options, either for rule-enforcement or to simplify its decision-making. To do so, each action definition accepts an optional argument in the form of a PWL function of the state with Boolean leaf nodes: returning `True` when the action should be allowed, and `False`, when it should not be considered.  For example, if a player can save a victim only when in the same location, you could declare, a priori, that the player cannot even consider saving the victim as an option unless that condition holds::

  save = player.addAction({'verb': 'save','object': victim.name},
    makeTree({'if': equalFeatureRow(location,stateKey(victim.name,'location')),
      True: True, False: False}))

The hyperplanes are our usual PWL tests, as in the dynamics functions, but here the leaf nodes are Boolean constants, not matrices. Note that using these pre-defined legality functions is not necessary, and they do not extend the expressivity of the language. For example, instead of making saving a victim illegal, we could simply make it ineffective::

  tree = makeTree({'if': equalFeatureRow(location,stateKey(victim.name,'location')),
      True: setToConstantMatrix(status,'saved'), 
      False: noChangeMatrix(status)})
  setDynamics(status,save,tree) 

In this second version, the player agent would consider saving the victim even when not in the same room. Given these dynamics, it would have an expectation that choosing "save" would have no effect, thus making it less desirable than any other action that would derive some positive reward. Given such a calculation, making "save" illegal under such conditions would not change the agent's behavior. However, when saving is legal, the agent incurs the computational cost of making the expected reward calculation necessary to determine that it is ineffectual; making the action illegal avoids that cost.

Termination
^^^^^^^^^^^

*Termination* conditions specify when scenario execution should reach an absorbing end state (e.g., when a final goal is reached, when time has expired). A termination condition is a PWL function  with Boolean leaves, just like a legality condition (Section \ref{sec-legality). The following example constructs a very nested tree that returns `True` (i.e., the simulation is done) if and only if all of the victims are either saved or dead::

  tree = True
  for name in victimList:
    tree = {'if': equalRow(stateKey(name,'status'),'unsaved'),
      True: False, False: tree}
   world.addTermination(makeTree(tree))

We could replace this unsightly tree with a more compact one as follows::

  for name in victimList:
    unsaved = world.defineState(name,'unsaved',bool)
    world.setFeature(unsaved,True)
    tree = makeTree({'if': equalRow(stateKey(name,'status',True),'unsaved'),
      True: setTrueMatrix(unsaved), False: setFalseMatrix(unsaved)})
    world.setDynamics(unsaved,True,tree))
  tree = makeTree({'if': andRow(falseKey=[stateKey(name,'unsaved',True) for name in victimList]),
    True: True, False: False})
  world.addTermination(tree)

The downside of this version is that we add one additional state feature per victim, which can be costly when copying the state vector (as occurs in hypothetical reasoning).

Reward
------

We have already made a few references to the agent's reward function, which, after all, is the only reason the agent cares about the state, actions, their effects, etc. An agent's reward function represents its (dis)incentives for choosing certain actions. In other agent frameworks, this same component might be referred to as the agent's *utility* or *goals*. Just like every other function in a PsychSim model, reward functions are represented by our PWL trees. The leaf nodes are matrices that specify the effect on a special state feature corresponding to an agent's reward, labeled using a special function :py:class:`~psychsim.pwl.keys.rewardKey`. For example, the following represents a positive reward equal to the "value" of a particular victim::

  makeTree(setToFeatureMatrix(rewardKey(player.name),stateKey(victim.name,'value')))

As always, we can introduce hyperplanes to be more selective about when this reward is earned::

  makeTree({'if': equalRow(status,'saved'),
    True: setToFeatureMatrix(rewardKey(player.name),stateKey(victim.name,'value')),
    False: setToConstantMatrix(rewardKey(player.name),0)})

There are some helper functions that generate some commonly used reward function structures.

* :py:class:`~psychsim.reward.maximizeFeature` gives the agent positive reward that is linear in the given state feature, such as the victim's health::

    maximizeFeature(stateKey(victim.name,'health'),player.name)

Note that the second argument is the name of the agent who receives this reward; it has nothing to do with the agent whose value is the input to the reward function.

* :py:class:`~psychsim.reward.minimizeFeature` similarly gives the agent negative reward that is linear in the given state feature, such as the number of dead victims::

    minimizeFeature(stateKey(WORLD,deaths),player.name)

* :py:class:`~psychsim.reward.achieveFeatureValue` gives a reward when a given variable equals a desired value and none otherwise. We can use it for a more readable version of our selective saving reward from earlier in this section::

    achieveFeatureValue(status,'saved',player.name)

* :py:class:`~psychsim.reward.achieveGoal` gives a reward when a Boolean variable is `True` and none otherwise. For example, our player agent may be grateful that the victim hasn't died on it yet::

    achieveGoal(alive,player.name)

* :py:class:`~psychsim.reward.minimizeDifference` yields a reward inversely proportional to the magnitude of the difference between two variables. Perhaps our player is grateful just to be near the victim::

    minimizeDifference(location,stateKey(victim.name,'location'),player.name)

Rewards are computed just as any other state feature. They are essentially float-valued with no lower or upper bounds. However, while transition probability functions are inserted via :py:meth:`~psychsim.world.World.setDynamics`, reward functions are inserted via :py:meth:`~psychsim.agent.Agent.setReward`. Thus, reward functions are specific to an individual agent. The call also takes a weight to be given to the reward, representing the relative priority of this component of the agent's reward function. The following define a composite reward function for our player agent::

  player.setReward(minimizeDifference(location,stateKey(victim.name,'location'),player.name),1)
  player.setReward(achieveFeatureValue(status,'saved',player.name),2)

These commands give the player the goals of moving close to the victim agent and saving it. The former is only half as important as the latter in this example.

Observations
------------
By default, all agents know the true state of the world (i.e., their world is an MDP, not a POMDP). But what fun is that? 

Beliefs
------

Models
^^^^^^
A *model* in the PsychSim context is a potential configuration of an agent that may apply in certain worlds or decision-making contexts. All agents have a "True" model that represents their real configuration, which forms the basis of all of their decisions during execution. 


It also possible to specify alternate models that represent perturbations of this true model, either to represent the dynamics of the agent's configuration or to represent the perceptions other agents have of it::

   free.addModel('friend')

Model Attribute: `static`
^^^^^^^^^^^^^^^^^^^^^^^^^
