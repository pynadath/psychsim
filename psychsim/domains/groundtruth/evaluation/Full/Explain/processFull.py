import csv
import os
import os.path

from pygraphml import Graph,GraphMLParser

if __name__ == '__main__':
    parser = GraphMLParser()
    directory = os.path.dirname(__file__)
    output = {}
    for name in sorted(os.listdir(directory if directory else '.')):
        fname,ext = os.path.splitext(os.path.basename(name))
        if ext == '.gml':
            label = fname[len('Scenario_C_Agent-Group-'):]
            els = label.split('_')
            label = ''
            for el in els[:-2]:
                label += el[0]
            label += els[-1]
            g = parser.parse(name)
            for node in g.nodes():
                if node.id in output:
                    output[node.id]['files'].add(label)
                else:
                    output[node.id] = {'files': {label}}
    fields = ['Node #','PNNL Node','Exact Match (TA1 Node)','Inexact Match (TA1 Node)','Notes']
    output = sorted(output.items())
    with open('graph.tsv','w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        for n in range(len(output)):
            node,entry = output[n]
            record = {'Node #': n+1,'PNNL Node': node,'Notes': ','.join(sorted(entry['files']))}
            writer.writerow(record)
