from argparse import ArgumentParser
import csv
import itertools
import logging
import os

from psychsim.pwl import *
from psychsim.world import *

"""
Functions for automatic construction of PsychSim models
"""
class Domain:
    """
    Structure for representing model-building information
    @ivar idFields: fields representing unique IDs for each record
    @type idFields: str[]
    @ivar filename: root filename for all model-related files
    @type filename: str
    @ivar fields: key of mappings from fields of data to model variables
    @type fields: strS{->}dict
    @ivar data: table of records with relevant variables
    @ivar variations: list of dependency variations to explore
    @ivar models: list of model name codes to explore
    @ivar targets: set of fields to predict
    """
    def __init__(self,fname,logger=logging.getLogger()):
        self.logger = logger.getChild('Domain')
        self.filename = fname
        # Read variable/field definitions
        self.idFields = []
        self.fields = {}
        self.targets = set()
        self.readKey()
        # Read input data
        self.data = {}
        self.readInputData()
        # What is the hypothesis space?
        self.readVariations()
        if self.variations:
            varLens = [range(link['range']) for link in self.variations]
            self.models = [self.links2model(model) for model in itertools.product(*varLens)]
            # What are the previously tested hypotheses?
            self.readPredictions()
            self.logger.info('|Unmatched| = %d' % (len(self.unmatched())))

    def unmatched(self):
        return {ID: record for ID,record in self.data.items() \
                if min(map(len,record['__matches__'].values())) == 0}

    def targetHistogram(self,missing=None,data=None):
        if data is None:
            data = self.data
        result = {field: {} for field in self.targets}
        for ID,record in data.items():
            for field in self.targets:
                value = record[field]
                if missing is not None and len(value.strip()) == 0:
                    value = missing
                if not value in result[field]:
                    result[field][value] = set()
                result[field][value].add(ID)
        return result
    
    def recordID(self,record):
        return ''.join(['%s%s' % (field,record[field]) for field in self.idFields])
    
    def readPredictions(self,fname=None):
        if fname is None:
            fname = '%s-predictions.csv' % (self.filename)
        if os.path.isfile('%s-predictions.csv' % (args['input'])):
            with open(fname,'r') as csvfile:
                reader = csv.DictReader(csvfile)
                for record in reader:
                    ID = self.recordID(record)
                    if not self.data[ID].has_key('__prediction__'):
                        self.data[ID]['__prediction__'] = {}
                        self.data[ID]['__probability__'] = {}
                        for field in self.targets:
                            self.data[ID]['__prediction__'][field] = {}
                            self.data[ID]['__probability__'][field] = {}
                    if not record.has_key('__target__'):
                        assert len(self.targets) == 1
                        record['__target__'] = list(self.targets)[0]
                    field = record['__target__']
                    links = []
                    for variation in self.variations:
                        code = variation['code']
                        if record[code] == '':
                            value = None
                        else:
                            value = map(int,list(record[code].split(':')))
                        links.append(variation['domain'].index(value))
                    model = self.links2model(links)
                    self.data[ID]['__prediction__'][field][model] = record[field]
                    if record['P(%s)' % (field)]:
                        self.data[ID]['__probability__'][field][model] = float(record['P(%s)' % (field)])
        for record in self.data.values():
            # Missing predictions, so let's enter empty tables
            if not record.has_key('__prediction__'):
                record['__prediction__'] = {}
                record['__probability__'] = {}
                for field in self.targets:
                    record['__prediction__'][field] = {}
                    record['__probability__'][field] = {}
            record['__matches__'] = {}
            for field in self.targets:
                record['__matches__'][field] = {m for m in record['__prediction__'][field].keys() if record['__prediction__'][field][m] == record[field]}

    def writePredictions(self,fname=None):
        if fname is None:
            fname = '%s-predictions.csv' % (self.filename)
        with open(filename,'w') as csvfile:
            fields = None
            for ID,record in sorted(self.data.items()):
                for field in sorted(self.targets): 
                    for model,prediction in sorted(record['__prediction__'][field].items()):
                        newRecord = {field: record[field] for field in self.idFields}
                        newRecord['__target__'] = field
                        newRecord[field] = prediction
                        try:
                            newRecord['P(%s)' % (field)] = record['__probability__'][field][model]
                        except KeyError:
                            newRecord['P(%s)' % (field)] = ''
                        links = self.model2links(model)
                        for variation in self.variations:
                            code = variation['code']
                            value = variation['domain'][links[code]]
                            if value is None:
                                newRecord[code] = ''
                            elif len(value) == 1:
                                newRecord[code] = '%d' % (value[0])
                            else:
                                assert len(value) == 2
                                newRecord[code] = '%d:%d' % tuple(value)
                        if fields is None:
                            fields = sorted(newRecord.keys())
                            writer = csv.DictWriter(csvfile,fields,extrasaction='ignore')
                            writer.writeheader()
                        writer.writerow(newRecord)

    def readDataFile(self,fname):
        data = {}
        with open(fname) as csvfile:
            reader = csv.DictReader(csvfile)
            for record in reader:
                ID = self.recordID(record)
                assert not ID in data,'Duplicate ID: %s' % (ID)
                data[ID] = record
        return data
    
    def readInputData(self,fname=None):
        if fname is None:
            fname = '%s-input.csv' % (self.filename)
        if os.path.isfile(fname):
            self.data = self.readDataFile(fname)
        else:
            raw = self.readDataFile('%s-raw.csv' % (self.filename))
            self.processData(raw)
            fields = sorted(next(iter(self.data.values())).keys())
            for row in self.data.values():
                assert set(row.keys()) == set(fields)
            with open(fname,'w') as csvfile:
                writer = csv.DictWriter(csvfile,fields,extrasaction='ignore')
                writer.writeheader()
                for ID,record in sorted(self.data.items()):
                    writer.writerow(record)

    def processData(self,raw):
        """
        Takes in raw data and extracts the relevant fields
        """
        if isinstance(raw,dict):
            raw = raw.values()
        logger = self.logger.getChild('processData')
        self.data.clear()
        for record in raw:
            ID = self.recordID(record)
            logger.debug('Processing record: %s' % (ID))
            newRecord = {field: record[field] for field in self.idFields}
            for field,entry in self.fields.items():
                if field and not entry['class'] == 'id':
                    assert field in record,'Missing field %s from record %s' % (field,ID)
                    assert entry['variable'],'Field %s has no variable' % (field)
                    newRecord[field] = record[field]
            self.data[ID] = newRecord
        
    def readKey(self,fname=None):
        if fname is None:
            fname = '%s-key.csv' % (self.filename)
        with open(fname) as csvfile:
            reader = csv.DictReader(row for row in csvfile if not row.startswith('#'))
            for field in reader:
                if field['class'] == 'id':
                    self.idFields.append(field['field'])
                else:
                    self.fields[field['field']] = field
                    if len(field['variable']) == 0:
                        field['variable'] = field['field']
                    if field['target'] == 'yes':
                        self.targets.add(field['field'])

    def readVariations(self,fname=None):
        if fname is None:
            fname = '%s-variations.csv' % (self.filename)
        self.variations = []
        if os.path.isfile(fname):
            # Read in modeling variations from file
            with open(fname) as csvfile:
                reader = csv.DictReader(row for row in csvfile if not row.startswith('#'))
                index = 0
                for link in reader:
                    # Read variables involved and possible link values
                    link['from'] = link['from'].split(';')
                    link['domain'] = [None if val == 'None' else map(int,val.split(':')) for val in link['domain'].split(';')]
                    link['range'] = int(link['range'])
                    link['index'] = index
                    self.variations.append(link)
                    # Derive downstream effects
                    link['effects'] = {}
                    link['effects'][link['to']] = link['domain'][:]
                    index += 1
        return self.variations

    def links2model(self,links):
        return ''.join(['%s%s' % (self.variations[i]['code'],links[i]) \
                        for i in range(len(self.variations))])

def noisyOrTree(tree,value):
    if isinstance(tree,dict):
        return {'if': tree['if'],
                True: noisyOrTree(tree[True],value),
                False: noisyOrTree(tree[False],value)}
    else:
        return tree*(1.-value)

def leaf2matrix(tree,key):
    if isinstance(tree,dict):
        return {'if': tree['if'],
                True: leaf2matrix(tree[True],key),
                False: leaf2matrix(tree[False],key)}
    else:
        prob = 1.-tree
        return {'distribution': [(setTrueMatrix(key),prob),(setFalseMatrix(key),1.-prob)]}

if __name__ == '__main__':
    logging.basicConfig(level=logging.ERROR)
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',default='WARNING',help='Level of logging detail')
    # Positional argument for input file
    parser.add_argument('input',nargs='?',default='seattle',
                        help='Root name of CSV files for input/output [default: %(default)s]')
    args = vars(parser.parse_args())
    # Extract logging level from command-line argument
    level = getattr(logging, args['debug'].upper(), None)
    if not isinstance(level, int):
        raise ValueError('Invalid debug level: %s' % args['debug'])
    logging.getLogger().setLevel(level)
    domain = Domain(args['input'])
