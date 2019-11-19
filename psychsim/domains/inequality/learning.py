import numpy
from sklearn.datasets.base import Bunch
from sklearn.naive_bayes import GaussianNB

def table2data(table,features,output):
	data = numpy.empty((len(table),len(features)),dtype=numpy.int)
	labels = numpy.empty((len(table),),dtype=numpy.int)

	for i in range(len(table)):
		data[i] = numpy.asarray([table[i][feature] for feature in features],dtype=numpy.int)
		labels[i] = numpy.asarray(table[i][output])
	return Bunch(data=data,target=labels)

def naiveBayes(data,debug=False):
	model = GaussianNB()
	model.fit(data.data,data.target)
	if debug:
		print(model.score(data.data,data.target))		
	return model