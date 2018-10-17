import csv

import teamofrivals

if __name__ == '__main__':
    data = []
    expectedTime = {}
    probability = {}
    values = {}
    territories = {}
    R = {}
    Values = {}
    Territories = {}
    with open('risk.csv') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            data.append(row)
    for row in data:
        incentives = teamofrivals.counts2incentives({'value': int(row['valueRewards']),
                                                     'individual': int(row['territoryRewards']),
                                                     'team': int(row['teamRewards'])})
        key = ''.join(incentives)
        R[key] = incentives
        if not expectedTime.has_key(key):
            expectedTime[key] = 0.
            probability[key] = 0.
            values[key] = {}
            territories[key] = {}
            for player in R[key]:
                values[key][player] = 0.
                territories[key][player] = 0.
                Values[player] = 0.
                Territories[player] = 0.
        
        probability[key] += float(row['probability'])
        expectedTime[key] += float(row['probability'])*float(row['rounds'])
        for player in range(len(R[key])):
            values[key][R[key][player]] += float(row['probability'])*\
                                           float(row['valuePlayer%d' % (player+1)])
            territories[key][R[key][player]] += float(row['probability'])*\
                                                float(row['territoryPlayer%d' % (player+1)])
    for key,value in sorted(expectedTime.items()):
        print '%s\t%5.2f' % (key,value/probability[key])
        for reward in values[key].keys():
            V = values[key][reward]/(probability[key]*float(R[key].count(reward)))
            print '\tV[%s]\t%5.2f' % (reward[:4],V)
            Values[reward] += V
        for reward in values[key].keys():
            T = territories[key][reward]/(probability[key]*float(R[key].count(reward)))
            print '\tT[%s]\t%5.2f' % (reward[:4],T)
            Territories[reward] += T
    for key,value in sorted(Values.items()):
        print '%s\t%5.2f' % (key,value)
    for key,value in sorted(Territories.items()):
        print '%s\t%5.2f' % (key,value)
            

        
