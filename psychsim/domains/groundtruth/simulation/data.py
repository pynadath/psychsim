# -*- coding: utf-8 -*-
import csv
import inspect
import logging
import os.path
import random
import sys

from psychsim.action import Action

gtNodes = {}
gtEdges = {}

likert = {5: [0.2,0.4,0.6,0.8,1.],
          7: [0.14,0.28,0.42,0.56,0.70,0.84,1.],
          }
reverseLikert = {'0': '0','0.2': '1','0.4': '2','0.6': '3','0.8': '4','1': '5'}

def toLikert(value,scale=5):
    for index in range(len(likert[scale])):
        if value < likert[scale][index]:
            return index+1
    else:
        return scale

def sampleNormal(mean,sigma,scale=5):
    mean = min(max(1,mean),scale)
    realValue = random.gauss(likert[scale][mean-1],likert[scale][sigma])
    return likert[scale][toLikert(realValue,scale)-1]

mapFromTandE = {'Actor’s distribution over ethnicGroup\'': ('Actors','ethnic_majority',reverseLikert),
                'Actor’s distribution over religion probability of majority\'':
                ('Actors','religious_majority',reverseLikert),
                '\'Actor’s distribution over religion probability of none\'':
                ('Actors','atheists',reverseLikert),
                'Actor’s distribution over age\'': ('Actors','age_max',None),
                'Actor’s distribution over children\'': ('Actors','children_max',None),
                'Actor’s distribution over owning a pet\'': ('Actors','pet_prob',reverseLikert),
                '\'Actor’s distribution over employed job_majority \'':
                ('Actors','job_majority',reverseLikert),
                '\'Actor’s distribution over employed job_minority \'':
                ('Actors','job_minority',reverseLikert),
                'Actor’s distribution over number of friendOf links\'': ('Actors','friends',None),
                'System’s resources\'': ('System','resources',reverseLikert),
                'Region’s risk distribution\'': ('Regions','risk_value',None),
                'Region’s security distribution\'': ('Regions','security_value',None),
                }

demographics = {'Gender': 'gender',
                'Age': 'age',
                'Ethnicity': 'ethnicGroup',
                'Religion': 'religion',
                'Children': 'kids',
                'Fulltime Job': 'job',
                'Pets': 'pet',
                'Wealth': 'wealth',
                'Residence': 'home'}
oldDemographics = {'Gender': 'gender',
                'Age': 'age',
                'Ethnicity': 'ethnicGroup',
                'Religion': 'religion',
                'Children': 'children',
                'Fulltime Job': 'employed',
                'Pets': 'pet',
                'Wealth': 'resources',
                'Residence': 'region'}

def getDemographics(actor,old=False):
    record = {}
    # Demographic info
    for field,answer in demographics.items():
        if isinstance(answer,str):
            value = actor.demographics[answer]
            if field == 'Wealth':
                if old:
                    record[field] = int(value*5.1)
                else:
                    record[field] = toLikert(value)
            elif isinstance(value,bool):
                if value:
                    record[field] = 'yes'
                else:
                    record[field] = 'no'
            else:
                record[field] = value
        elif field == 'Residence':
            record[field] = actor.demographics['home']
        else:
            raise RuntimeError('Unable to process pre-survey field: %s' % (field))
    return record

def readHurricanes(instance,run=0,sub=None,fname='HurricaneTable.tsv'):
    """
    :returns: A list of attributes about the hurricanes so far
    """
    inFile = os.path.join(os.path.dirname(__file__),'..','Instances','Instance%d' % (instance),'Runs','run-%d' % (run))
    if sub:
        inFile = os.path.join(inFile,sub)
    inFile = os.path.join(inFile,fname)
    return readHurricaneFile(inFile)
    
def readHurricaneFile(inFile):
    hurricanes = []
    with open(inFile,'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            hurricane = int(row['Name'])
            while len(hurricanes) < hurricane-1:
                hurricanes.append(None)
            if len(hurricanes) < hurricane:
                hurricanes.append({'Hurricane': hurricane,
                                   'Predicted Location': row['Location'],
                                   'Media Coverage': 'yes',
                                   'Actual Location': [],
                                   'Actual Track': [],
                                   'Official Announcements': 'none',
                                   'Start': int(row['Timestep']),
                                   'Actual Category': [],
                                   })
            elif row['Landed'] == 'yes':
                if row['Location'] == 'leaving':
                    hurricanes[-1]['End'] = int(row['Timestep'])
                else:
                    if not 'Landfall' in hurricanes[-1]:
                        hurricanes[-1]['Landfall'] = int(row['Timestep'])
                    if not 'Actual Severity' in hurricanes[-1]:
                        hurricanes[-1]['Actual Severity'] = row['Category']
                    if len(hurricanes[-1]['Actual Track']) == 0 or \
                       hurricanes[-1]['Actual Track'][-1] != row['Location']:
                        hurricanes[-1]['Actual Track'].append(row['Location'])
            hurricanes[-1]['Actual Category'].append(row['Category'])
            hurricanes[-1]['Actual Location'].append(row['Location'])
    for record in hurricanes:
        if record:
            record['Actual Track'] = ','.join(record['Actual Track'])
    if 'End' not in hurricanes[-1]:
        # Ignore partial hurricane track
        return hurricanes[:-1]
    else:
        return hurricanes

def readNetwork(instance,run=0,sub=None):
    """
    :returns: The social networks in the given run
    """
    networks = {}
    inFile = os.path.join(os.path.dirname(__file__),'..','Instances','Instance%d' % (instance),
                          'Runs','run-%d' % (run))
    if sub:
        inFile = os.path.join(inFile,sub)
    inFile = os.path.join(inFile,'RelationshipDataTable.tsv')
    with open(inFile,'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            link = row['RelationshipType']
            if link not in networks:
                networks[link] = {}
            assert row['Directed'] == 'yes'
            try:
                networks[link][row['FromEntityId']].add(row['ToEntityId'])
            except KeyError:
                networks[link][row['FromEntityId']] = {row['ToEntityId']}
    return networks

def readParticipants(instance,run=0,fname='psychsim.log',splitHurricanes=True,duplicates=False):
    """
    :returns: Mapping from participants to actor names for each survey
    """
    tables = {}
    if isinstance(instance,int):
        inFile = os.path.join(os.path.dirname(__file__),'..','Instances','Instance%d' % (instance),
                              'Runs','run-%d' % (run),fname)
    else:
        # Assume it's a directory
        inFile = os.path.join(instance,fname)
    with open(inFile,'r') as logfile:
        for line in logfile:
            if 'Participant' in line:
                elements = line.split()
                hurricane = int(elements[1][:-1])
                if splitHurricanes:
                    survey = '%s %d' % (elements[0],hurricane)
                else:
                    survey = elements[0]
                if not survey in tables:
                    tables[survey] = {}
                participant = int(elements[3][:-1])
                name = elements[4]
                if participant in tables[survey] and not duplicates:
                    assert name == tables[survey][participant],'Mismatch on participant %s in %s' % (participant,survey)
                else:
                    tables[survey][participant] = name
    return tables

def readActions(instance,run=0):
    """
    :returns: List of tables of actions by all agents
    """
    series = []
    inFile = os.path.join(os.path.dirname(__file__),'..','Instances','Instance%d' % (instance),
                          'Runs','run-%d' % (run),'RunDataTable.tsv')
    with open(inFile,'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            if row['VariableName'][-6:] == 'action':
                t = int(row['Timestep'])
                while len(series) < t:
                    series.append({})
                name = row['EntityIdx']
                action = Action(row['Value'])
                series[t-1][name] = action
    return series[1:]

def readDeaths(instance,run=0):
    """
    :returns: a table of who died and when
    """
    deaths = {}
    inFile = os.path.join(os.path.dirname(__file__),'..','Instances','Instance%d' % (instance),
                          'Runs','run-%d' % (run),'RunDataTable.tsv')
    with open(inFile,'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            if row['VariableName'] == 'Actor alive' and row['Value'] == 'False':
                if row['EntityIdx'] not in deaths:
                    deaths[row['EntityIdx']] = int(row['Timestep'])
    return deaths  

def readRunData(instance,run=0):
    inFile = os.path.join(os.path.dirname(__file__),'..','Instances','Instance%d' % (instance),
                          'Runs','run-%d' % (run),'RunDataTable.tsv')
    with open(inFile,'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        data = list(reader)
    return data

def readPrescription(inFile):
    prescription = {}
    with open(inFile,'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            if 'Timestep' in row:
                t = int(row['Timestep'])
                if t in prescription:
                    if isinstance(prescription[t],set):
                        prescription[t].add(row['Region'])
                    else:
                        prescription[t] = {prescription[t],row['Region']}
                else:
                    prescription[t] = row
            else:
                try:
                    prescription.append(row)
                except AttributeError:
                    prescription = [row]
    return prescription

def logNode(name,description=None,nodeType=None,notes='',offset=1):
    """
    :param offset: How many lines after this one is the relevant comment (default is 1)
    """
    if name not in gtNodes:
        nodeID = len(gtNodes)+1
        for other in gtNodes.values():
            assert nodeID != other[0]
        gtNodes[name] = ('%d' % (nodeID),)
    if description is not None and len(gtNodes[name]) == 1:
        frame = inspect.getouterframes(inspect.currentframe())[1]
        gtNodes[name] = (gtNodes[name][0],name,description,nodeType,inspect.getmodulename(frame.filename),'%d' % (frame.lineno+offset),notes)
        for value in gtNodes[name]:
            assert ',' not in value
        logging.debug('%s' % (','.join(gtNodes[name])))


def logEdge(source,target,frequency,description,notes='',offset=1):
    """
    :param offset: How many lines after this one is the relevant comment (default is 1)
    """
    if source not in gtNodes:
        logNode(source)
    if target not in gtNodes:
        logNode(target)
    label = (gtNodes[source][0],gtNodes[target][0])
    try:
        edgeID = gtEdges[label][0]
    except KeyError:
        edgeID = len(gtEdges)+1
        gtEdges[label] = (edgeID,set())
    frame = inspect.getouterframes(inspect.currentframe())[1]
    entry = ('%d' % (edgeID),source,target,frequency,description,inspect.getmodulename(frame.filename),'%d' % (frame.lineno+offset),notes,label[0],label[1])
    if (entry[5],entry[6]) not in gtEdges[label][1]:
        gtEdges[label][1].add((entry[5],entry[6]))
        for value in entry:
            assert ',' not in value
        logging.debug('%s' % (','.join(entry)))

if __name__ == '__main__':
    nodes = {}
    edges = {}
    try:
        nowrite = sys.argv[1] == 'nowrite'
    except IndexError:
        nowrite = False
    with open('psychsim.log','r') as log:
        for entry in log:
            cols = entry.split(',')
            if len(cols) == 7:
                # Entry for a node
                try:
                    start = int(cols[5])
                except ValueError:
                    # Probably some irrelevant line. Probably.
                    continue
                nodes[cols[0]] = cols
                newSrc = ''
                print(cols)
                with open(os.path.join(os.path.dirname(__file__),'%s.py' % (cols[4])),'r') as src:
                    found = False
                    fragment = ''
                    for lineno,line in enumerate(src):
                        if lineno < start-1:
                            newSrc += line
                        elif found:
                            newSrc += line
                        elif lineno == start-1:
                            comment = line
                        elif len(line.strip()) == 0:
                            found = True
                            try:
                                newSrc += comment[:comment.index('#')] + '#//GT: node %d; 1 of 1; next %d lines%s' % (int(cols[0]),lineno-start,comment[-1])
                            except ValueError:
                                raise ValueError('No comment on line %d in %s.py' % (start-1,cols[4]))
                            newSrc += fragment + line
                        else:
                            fragment += line
                if not nowrite:
                    with open(os.path.join(os.path.dirname(__file__),'%s.py' % (cols[4])),'w') as src:
                        src.write(newSrc)
            elif len(cols) == 10:
                # Entry for an edge
                try:
                    int(cols[0])
                except ValueError:
                    continue
                try:
                    edges[cols[0]].append(cols)
                except KeyError:
                    edges[cols[0]] = [cols]
    # Process edges
    for edgeID,entries in sorted(edges.items(),key=lambda item: int(item[0])):
        for i in range(len(entries)):
            newSrc = ''
            cols = entries[i]
            print(cols)
            start = int(cols[6])
            with open(os.path.join(os.path.dirname(__file__),'%s.py' % (cols[5])),'r') as src:
                found = False
                fragment = ''
                for lineno,line in enumerate(src):
                    if lineno < start-1:
                        newSrc += line
                    elif found:
                        newSrc += line
                    elif lineno == start-1:
                        comment = line
                    elif len(line.strip()) == 0:
                        found = True
                        newSrc += comment[:comment.index('#')] + '#//GT: edge %d; from %s; to %s; %d of %d; next %d lines%s' % \
                            (int(edgeID),cols[-2],cols[-1].strip(),i+1,len(entries),lineno-start,comment[-1])
                        newSrc += fragment + line
                    else:
                        fragment += line
            if not nowrite:
                with open(os.path.join(os.path.dirname(__file__),'%s.py' % (cols[5])),'w') as src:
                    src.write(newSrc)
    for nodeID in range(max([int(nodeID) for nodeID in nodes])):
        if str(nodeID+1) not in nodes:
            print('Missing node %d' % (nodeID+1))
    for edgeID in range(max([int(edgeID) for edgeID in edges])):
        if str(edgeID+1) not in edges:
            print('Missing edge %d' % (edgeID+1))
    # Do all nodes have an edge?
    for node in nodes.values():
        for edgeID,entries in edges.items():
            for record in entries:
                if record[1] == node[1] or record[2] == node[1]:
                    break
            else:
                continue
            break
        else:
            print('No edge for: %s' % (node['Name']))
    # Are all nodes from edges listed?
    for edgeID,entries in edges.items():
        for record in entries:
            for node in nodes.values():
                if node[1] == record[1]:
                    break
            else:
                print('Edge %d has unlisted source %s' % (edgeID,record[1]))
            for node in nodes.values():
                if node[1] == record[2]:
                    break
            else:
                print('Edge %d has unlisted target %s' % (edgeID,record[2]))
    # Write node table
    fields = ['Node ID','Name','Description','Type','Module','Line','Notes']
    with open('nodes.tsv','w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        for record in sorted(nodes.values(),key=lambda n: int(n[0])):
            writer.writerow({fields[i]: record[i].strip() for i in range(len(fields))})
    fields = ['Edge ID','Source','Target','Frequency','Description','Module','Line','Notes']
    with open('edges.tsv','w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        for edgeID,entries in sorted(edges.items(),key=lambda item: int(item[0])):
            for record in entries:
                writer.writerow({fields[i]: record[i].strip() for i in range(len(fields))})
