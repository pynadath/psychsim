from world import World
from action import Action,ActionSet

class Agent:
    def __init__(self,name):
        self.name = name
        self.world = None
        self.subjective = None
        self.actions = set()
        self.reward = set()

    def setState(self,feature,value):
        self.world.setState(self.name,feature,value)

    def addAction(self,action):
        new = ActionSet()
        if isinstance(action,set):
            for atom in action:
                if isinstance(atom,Action):
                    new.add(Action(atom))
                else:
                    new.add(atom)
        elif isinstance(action,Action):
            new.add(action)
        else:
            assert isinstance(action,dict),'Argument to addAction must be at least a dictionary'
            new.add(Action(action))
        for atom in new:
            if not atom.has_key('subject'):
                # Make me the subject of these actions
                atom['subject'] = self.name
        self.actions.add(new)

    def observe(self,observation,subjective=None):
        """
        @param observation: the observation received by this agent
        @param subjective: the pre-observation beliefs of this agent (default is current beliefs)
        @return: the post-observation beliefs of this agent
        """
        if subjective is None:
            subjective = self.subjective
            
