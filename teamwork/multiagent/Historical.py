from PsychAgents import *

class HistoricalAgents(PsychAgents):
    def __init__(self): 
        self.history = []

    def getHistory(self):
        try:
            return self.history
        except AttributeError:
            self.history = []
            return self.history

    def microstep(self,turns=[],hypothetical=False,explain=False,suggest=False,debug=Debugger(0)):
        previousState = self.getState().domain()[0].__copy__()
        result = PsychAgents.microstep(self,turns,hypothetical,explain,suggest,debug) 

        #We only store the history if we're doing a real step
        if not hypothetical:
            action = result['decision'].values()[0][0]
            self.getHistory().append({'action':action, 'previousState':previousState})

        return result
