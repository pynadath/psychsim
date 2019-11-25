import logging
import os.path
from string import Template


from psychsim.pwl import *

typeMap = {float: 'double'}

actionTemplate = Template('meCurrentAction = PSCivilianActionEnum.${action};\nRaiseActionChangedEvent(new ActionChangedEventArgs(this, meCurrentAction));')
branchTemplate = Template('if ${plane} {\n\t${true}\n} else {\n\t${false}\n}')
dynamicsTemplate = Template('\t\tprotected override void update_${variable}()\n\t\t{\n\t\t\tswitch (meCurrentAction)\n\t\t\t{\n${trees}\t\t\t\tdefault: { break; }\n\t\t\t}\n\t\t}\n')
caseTemplate = Template('\t\t\t\tcase PSCivilianActionEnum.${action}:\n\t\t\t\t{\n\t\t\t\t\t${tree}\n\t\t\t\t\tbreak;\n\t\t\t\t}\n')
effectTemplate = Template('${var} = ${vector};')

def encodeName(name):
	return name.replace(' ','')
def encodeAction(action):
	if 'object' in action:
		return '%s%s' % (action['verb'],action['object'].replace(' ').capitalize())
	else:
		return action['verb']

def encodeVariable(var,name):
	"""
	:param name: The name of the agent whose mind is being exported
	"""
	if var == CONSTANT:
		return '1.0'
	else:
		if isFuture(var):
			var = makePresent(var)
			logging.warning('Ignoring future flag on %s' % (var))
		return state2feature(var) if state2agent(var) == name else '%s_%s' % (state2agent(var),state2feature(var))

def encodePlane(plane,name):
	return '(%s %s %f)' % (encodeVector(plane[0],name),KeyedPlane.COMPARISON_MAP[plane[2]],plane[1])

def encodePolicy(policy,name):
	if policy.isLeaf():
		action = policy.getLeaf()
		return actionTemplate.safe_substitute({'name': encodeName(name),'action': encodeAction(action)})
	else:
		assert len(policy.branch.planes) == 1,'Currently unable to export simultaneous tests'
		plane = policy.branch.planes[0]
		return branchTemplate.safe_substitute({'plane': encodePlane(plane,name),
			'true': encodePolicy(policy.children[True],name).replace('\n','\n\t'),
			'false': encodePolicy(policy.children[False],name).replace('\n','\n\t')}).replace('\n','\n\t\t\t')

def encodeTree(tree,name):
	if tree.isLeaf():
		return encodeMatrix(tree.getLeaf(),name)
	else:
		assert len(tree.branch.planes) == 1,'Currently unable to export simultaneous tests'
		plane = tree.branch.planes[0]
		return branchTemplate.safe_substitute({'plane': encodePlane(plane,name),
			'true': encodeTree(tree.children[True],name).replace('\n','\n\t'),
			'false': encodeTree(tree.children[False],name).replace('\n','\n\t')}).replace('\n','\n\t\t\t')
def encodeMatrix(matrix,name):
	assert len(matrix) == 1,'Currently unable to export joint dynamics'
	var,vector = next(iter(matrix.items()))
	return effectTemplate.safe_substitute({'var': encodeVariable(makePresent(var),name),'vector': encodeVector(vector,name)})
def encodeVector(vector,name):
	return '+'.join(['(%f)*%s' % (weight,encodeVariable(var,name)) for var,weight in sorted(vector.items())])
def encodeDynamics(world,var,name):
	table = {'variable': encodeVariable(var,name),'trees': ''}
	for action,tree in sorted(world.dynamics[var].items()):
		if action is True:
			# How to handle default dynamics?
			pass
		else:
			table['trees'] += caseTemplate.safe_substitute({'name': encodeName(name),'action': encodeAction(action),'tree': encodeTree(tree,name)})
	return dynamicsTemplate.safe_substitute(table)

def exportCS(world,name,dirname='.'):
	"""
	:param world: a PsychSim World instance defining the entire scenario
	:param name: the name of the Agent instance (not the actual instance) to be exported
	:param name: the name of the directory to put the exported C# files (default is the current working directory)
	"""
	agent = world.agents[name]
	safeName = encodeName(name)
	with open(os.path.join(os.path.dirname(__file__),'PS.cs'),'r') as inFile:
		template = Template(inFile.read())
	subs = {'name': safeName}
	# Relevant state features
	beliefs = agent.getBelief()
	assert len(beliefs) == 1,'Unable to export Unity version of agent with multiple personalities'
	model,belief = next(iter(beliefs.items()))
	variables = [var for var in sorted(belief.keys()) if isStateKey(var) and not isSpecialKey(var)]
	subs['states'] = ';\n\t\t'.join(['%s %s' % (typeMap[world.variables[var]['domain']],encodeVariable(var,name)) for var in variables])+';'
	# Possible actions
	subs['actions'] = ','.join([encodeAction(action) for action in agent.actions])
	# Dynamics of actions
	subs['dynamics'] = '\n\n'.join([encodeDynamics(world,var,name) for var in variables if var in world.dynamics])
	# Policy of behavior
	policy = agent.compilePi()
	subs['policy'] = encodePolicy(policy,name)
	code = template.safe_substitute(subs)
	with open(os.path.join(os.path.dirname(__file__),'PS%s.cs' % (safeName)),'w') as outFile:
		outFile.write(code)