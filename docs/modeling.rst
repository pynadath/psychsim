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
  rufus = Agent('Rufus')
  world.addAgent(rufus)

And groups of people::
  
  free = Agent('Freedonia')
  world.addAgent(free)

And killer robots::

  world.addAgent(Agent('Klaatu'))

These are *agents*, because they have names::

  for name in world.agents:
     print(world.agents[name])


Of course, not everything that has a name is an agent. There are a number of reasons to make something an agent. The most common one is that something *is* an agent, i.e., an autonomous, decision-making entity. But there can be good reasons for modeling non-agents as agents within PsychSim, usually because of improved readability of simulation output. Conversely, not every agent has to be modeled as an agent, especially if that agent's decision-making is not relevant to the target scenario. It does not necessarily cost anything to have extra agents in the scenario (if they do not get a *turn*, their decision-making procedure is never invoked). The choice of whether to make something an agent is yours.

