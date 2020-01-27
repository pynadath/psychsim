import csv
import os.path
from pygraphml import Graph,GraphMLParser

if __name__ == '__main__':
    nodes = {}
    graph = Graph()
    with open('Annotated Phase 2 Graph USC - Nodes.tsv','r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            nodes[row['Name']] = graph.add_node(row['Name'])
    with open('Annotated Phase 2 Graph USC - Edges.tsv','r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            graph.add_edge(nodes[row['Source']],nodes[row['Target']],True)
    parser = GraphMLParser()
    parser.write(graph,os.path.join(os.path.dirname(__file__),'GroundTruth-USC.graphml'))
