import numpy
from sklearn.datasets.base import Bunch
from sklearn.naive_bayes import GaussianNB,MultinomialNB
from sklearn import linear_model

def table2data(table,features,output):
	data = numpy.empty((len(table),len(features)),dtype=numpy.int)
	labels = numpy.empty((len(table),),dtype=numpy.int)

	for i in range(len(table)):
		data[i] = numpy.asarray([table[i][feature] for feature in features],dtype=numpy.int)
		labels[i] = numpy.asarray(table[i][output])
	return Bunch(data=data,target=labels)

def naiveBayes(data,gaussian=False):
	if gaussian:
		model = GaussianNB()
	else:
		model = MultinomialNB()
	model.fit(data.data,data.target)
	return model

def linear(data,debug=False):
	model = linear_model.LinearRegression()	
	model.fit(data.data,data.target)
	return model
