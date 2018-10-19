Simulation
==========

The basic simulation method is the :py:meth:`~psychsim.world.World.step`, which generates a single decision epoch's worth of action choices, state changes, and belief updates. Calling the method with no arguments will allow all of the agents to choose their actions autonomously based on their beliefs in the current world::

   world.step()

Algorithms
----------

Decision Making
^^^^^^^^^^^^^^^

Belief Update
^^^^^^^^^^^^^

World has :math:`\Pr(M_0)`

World generates an observation :math:`omega`

But :math:`M_0` cannot generate :math:`\omega`

.. math::

   \begin{align}
   \Pr(M_1=m)&=\Pr(M_1=m|M_0,\omega)\\
   &=\frac{\Pr(M_1=m,\omega|M_0)}{\Pr(\omega|M_0)}\\
   &\propto 
   \end{align}

And done.
