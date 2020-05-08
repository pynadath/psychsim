from pygraphml import Graph,GraphMLParser

import openpyxl

import os.path

import sys

if __name__ == '__main__':
    if len(sys.argv) > 1:
        name = sys.argv[1]
    else:
        name = os.path.join(os.path.dirname(__file__),'phase1graph.xlsx')
    graph = Graph()
    nodes = {}
    wb = openpyxl.load_workbook(name)
    edges = set()
    for sheet in wb:
        first = True
        for row in sheet.values:
            if first:
                headings = {row[i]: i for i in range(len(row))}
                first = False
                print(sorted(nodes.keys()))
            else:
                if sheet.title == 'Nodes':
                    name = row[headings['Name']]
                    nodes[name] = graph.add_node(name)
                else:
                    assert sheet.title == 'Edges'
                    if row[0] is None:
                        continue
                    edge = (nodes[row[headings['Source']]],nodes[row[headings['Target']]])
                    if edge not in edges:
                        graph.add_edge(edge[0],edge[1],True)
                        edges.add(edge)
    parser = GraphMLParser()
    parser.write(graph,'/tmp/GroundTruth-USC.graphml')
