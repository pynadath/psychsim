"""
Module that generates a PNG displaying the graph of mental models used by agents in a given world
@author: Camille Barot
"""
import pydot
        
def createModelGraph(world, filename="modelgraph"):
    '''
    This method creates a graph of the models used by the agents
    '''
    modelgraph = pydot.Dot('Model graph', graph_type='digraph') 
    for agent in world.agents.values():
        for my_model in list(agent.models.keys()):
            name = agent.name + ' ' + str(my_model)
            node_src = pydot.Node(name)
            if node_src.get_name() not in modelgraph.obj_dict['nodes'].keys():
                modelgraph.add_node(node_src)
            if world.agents[agent.name].models[my_model].has_key('beliefs'):
                beliefs = world.agents[agent.name].models[my_model]['beliefs']
                if beliefs != True:
                    for belief,pct in beliefs.items():
                        split = belief.replace('\t','\n').split('\n')
                        for line in split:
                            if '_model' in line:
                                modeled_agent_name = line.split("'")[0]
                                model_num = int(float(line.split(')')[-1].strip().split(': ')[1]))
                                model_key = world.agents[modeled_agent_name].index2model(model_num)
                                name = modeled_agent_name + ' ' + model_key
                                node_dst = pydot.Node(name)
                                if node_dst.get_name() not in modelgraph.obj_dict['nodes'].keys():
                                    modelgraph.add_node(node_dst)
                                if not modelgraph.get_edge(node_src.get_name(), node_dst.get_name()):
                                    edge = pydot.Edge(node_src, node_dst, label=str(pct))
                                    modelgraph.add_edge(edge)
                                else:
                                    old_edge = modelgraph.get_edge(node_src.get_name(), node_dst.get_name())[0]
                                    old_pct = old_edge.get_attributes()['label']
                                    modelgraph.del_edge(node_src, node_dst)
                                    edge = pydot.Edge(node_src, node_dst, label=str(float(old_pct)+pct))
                                    modelgraph.add_edge(edge)

    modelgraph.write_png(filename+'.png')
