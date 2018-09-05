import random

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
    
