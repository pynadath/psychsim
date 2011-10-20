import SOAPpy

from xml.dom.minidom import parseString
from teamwork.multiagent.PsychAgents import PsychAgents
from teamwork.agent.Entities import PsychEntity

class PsychSoapServer:

    def loadScenario(self, fileContents=None):
        doc = parseString(fileContents)
        self.scenario = PsychAgents()
        self.scenario.parse(doc.documentElement,PsychEntity)

        return self.scenario.keys()

    def getRelationshipsForAgent(self, agentName=None):
        keys = self.scenario[agentName].relationships.keys() 

        if len(keys) == 0:
            keys.append('_NONE_')

        return keys

    def getRelationshipTargets(self, agentName, relationshipName):
        return self.scenario[agentName].relationships[relationshipName]

    def getStateKeys(self):
        states = []
        for key in self.scenario.getStateKeys().keys():
            if 'feature' in key.keys():
                states.append(key['feature'] + ':' + key['entity'])
        return states

    def getStateValue(self, agentName, stateName):
        featureEntityKeys = self.scenario.getState().items()[0][0].keys()
        for featureEntityDict in featureEntityKeys:
            if 'feature' in featureEntityDict.keys() and featureEntityDict['feature'] == stateName and featureEntityDict['entity'] == agentName:
                return self.scenario.getState().items()[0][0][featureEntityDict]
        return 30
    

server = SOAPpy.SOAPServer(("localhost", 8080))
psychsoapserver = PsychSoapServer()
server.registerObject(psychsoapserver, "psychsim")
#server.registerKWFunction(loadScenario, "psychsim")
server.serve_forever()
