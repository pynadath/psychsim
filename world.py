from probability import Distribution

class World:
    def __init__(self):
        self.agents = {}
        self.state = Distribution()
        self.dynamics = {}

    def addAgent(self,agent):
        if self.agents.has_key(agent.name):
            raise NameError,'Agent %s already exists in this world' % (agent.name)
        else:
            self.agents[agent.name] = agent
            for other in self.agents.values():
                other.world = self

    def setState(self,entity,feature,value):
        """
        @param entity: the name of the entity whose state feature we're setting (does not have to be an agent)
        @type entity: str
        @type feature: str
        @type value: float or L{Distribution}
        """
        self.state.join("%s's %s" % (entity,feature),value)
