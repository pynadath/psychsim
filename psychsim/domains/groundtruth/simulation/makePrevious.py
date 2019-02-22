import csv
from psychsim.pwl.keys import *
from psychsim.domains.groundtruth import accessibility

if __name__ == '__main__':
    parser = accessibility.createParser()
    args = accessibility.parseArgs(parser)
    data = accessibility.loadRunData(args['instance'],args['run'])
#    demos = accessibility.readDemographics(data)
    participants = accessibility.readParticipants(args['instance'],args['run'])['ActorPostTable']
    hurricanes = accessibility.readHurricanes(args['instance'],args['run'])
    output = []
    first = True
    with accessibility.openFile(args,'ActorPostTable.tsv') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        if first:
            fields = list(reader.fieldnames)
        for row in reader:            
#            match = accessibility.findMatches(row,population=demos)
#            assert len(match) == 1
            name = participants[int(row['Participant'])]
#            assert next(iter(match)) == name
            for oldField in list(row.keys()):
                if 'All Hurricanes' in oldField:
                    newField = oldField.replace('All Hurricanes','Previous Hurricane')
                    if first:
                        fields[fields.index(oldField)] = newField
                    hurricane = hurricanes[int(row['Hurricane'])-1]
                    if 'Dissatisfaction' in newField:
                        delta = data[name][stateKey(name,'grievance')][hurricane['End']+1]\
                            -data[name][stateKey(name,'grievance')][hurricane['Start']]
                        row[newField] = accessibility.toLikert(4.*delta+0.5)
                    else:
                        for t in range(hurricane['Start'],hurricane['End']+1):
                            if 'At Shelter' in newField:
                                action = data[name][actionKey(name)][t]
                                if action.get('object','')[:7] == 'shelter':
                                    row[newField] = 'yes'
                                    break
                            elif 'Evacuated' in newField:
                                action = data[name][actionKey(name)][t]
                                if action['verb'] == 'evacuate':
                                    row[newField] = 'yes'
                                    break
                            elif 'Injured' in newField:
                                if data[name][stateKey(name,'health')][t] < 0.2:
                                    row[newField] = 'yes'
                                    break
                            elif 'Risk' in newField:
                                row[newField] = max(row.get(newField,0),
                                    accessibility.toLikert(float(data[name]['__beliefs__'][stateKey(name,'risk')][t])))
                            else:
                                raise NameError('Unknown field: %s' % (newField))
                        else:
                            if newField not in row:
                                row[newField] = 'no'
            output.append(row)
            first = False
    accessibility.writeOutput(args,output,fields,'ActorPostTable.tsv')
