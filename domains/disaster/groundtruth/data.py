import random

likert = {5: [0.2,0.4,0.6,0.8,1.],
          7: [0.14,0.28,0.42,0.56,0.70,0.84,1.],
          }

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
