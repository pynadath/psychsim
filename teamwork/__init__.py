"""The top-level package for all of the PsychSim code, plus all of the individual multiagent and math modules

To invoke PsychSim through the GUI:

>>> python teamwork/shell/PsychShell.py

(use the C{--help} argument for more information on command-line arguments)

The test suite also includes a U{use case of the API<http://pynadath.net:81/psychsim/doc/html/teamwork.test.testAll-pysrc.html>}.

The central multiagent simulation class is L{PsychAgents<teamwork.multiagent.PsychAgents.PsychAgents>}.
"""
__all__ = ['action','agent','dynamics','examples','images','math','multiagent','policy','reward','shell','widgets']
