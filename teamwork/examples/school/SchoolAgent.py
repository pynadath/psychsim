from teamwork.shell.TerminalShell import TerminalShell
from teamwork.multiagent.sequential import SequentialAgents
from teamwork.agent.Entities import PsychEntity

class SchoolAgent(PsychEntity):
    beliefClass = SequentialAgents

class SchoolShell(TerminalShell):
    agentClass = SchoolAgent
    
