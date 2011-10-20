from teamwork.agent.RecursiveAgent import RecursiveAgent
from copy import deepcopy

class MemoryAgent(RecursiveAgent):
    '''
    Memory is stored in a list such that the most recent memory is the 0th element in the list
    and the oldest memory is the n-1th memory in the list where n is the memory length
    '''
    
    def __init__(self,name=''):
        RecursiveAgent.__init__(self,name)
        self.memoryLength = 3
        self.memory = []

    def updateMemory(self, actions, previousBeliefs):
        memory = {}

        #update the memory of the action taken
        memory['actions'] = actions.copy()

        #update beliefs
        memory['previousBeliefs'] = deepcopy(previousBeliefs)

        #insert the memory
        self.memory.insert(0, memory)

        #make sure we don't go over the memory length
        if len(self.memory) > self.memoryLength:
            self.memory.pop()
           
if __name__ == '__main__':
    from teamwork.multiagent.GenericSociety import GenericSociety
    from teamwork.multiagent.sequential import SequentialAgents
    import teamwork.examples.school.SchoolClasses as classModule
    from teamwork.multiagent.Historical import HistoricalAgents

    #We need to get a scenario
    society = GenericSociety()
    society.importDict(classModule.classHierarchy)

    #Instantiate the agents 
    victim = society.instantiate("Victim", "Victim")
    onlooker = society.instantiate("Onlooker", "Onlooker")
    bully = society.instantiate("Bully", "Bully")
    teacher = society.instantiate("Teacher", "Teacher")
    
    #Set up the relationships
    victim.relationships['victim'] = ['Victim']
    onlooker.relationships['victim'] = ['Victim']
    bully.relationships['victim'] = ['Victim']

    #Instantiate the scenario
    entities = [victim, onlooker, bully, teacher]
    agents = SequentialAgents(entities)
    agents.applyDefaults()
    agents.compileDynamics()

    result = agents.microstep()
    agents.microstep()

    print "\n\nmemory!\n\n"
#    print bully.memory[0]['previousBeliefs']['state'].items()[0][0].keys()[1]['entity']
#    print bully.memory[0]['previousBeliefs']['state'].items()[0][0].keys()
    print victim.entities.getStateKeys().keys()

#    for agent in agents.activeMembers():
#        print agent.name
#        for mem in agent.memory:
#            print "Previous Beliefs:"
#            for belkey in mem['previousBeliefs'].keys():
#                if belkey == 'state':
#                    print mem['previousBeliefs'][belkey].keys()[0]
#            print "\n"
#
#        print "\n\n"

