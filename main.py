#%% imports
from sklearn import tree
from sklearn import ensemble
from stats.maxLlh import MaxLlh
from dataReaders.reader import loadData


#%% configuration
nrTrainingSamples = 1000
nrTestingSamples = 100


#%% data
bandData, berClasses = loadData(nrTrainingSamples + nrTestingSamples)
bandDataTrain = bandData[:nrTrainingSamples]
bandDataTest = bandData[nrTrainingSamples:]
berClassesTrain = berClasses[:nrTrainingSamples]
berClassesTest = berClasses[nrTrainingSamples:]


#%% Maximum likelihood classifier
mllhClf = MaxLlh()
mllhClf.fit(bandDataTrain, berClassesTrain)
mllhScore = mllhClf.score(bandDataTest, berClassesTest)
print(mllhScore)


#%% Tree classifier
treeClf = tree.DecisionTreeClassifier()
treeClf.fit(bandDataTrain, berClassesTrain)
treeScore = treeClf.score(bandDataTest, berClassesTest)
print(treeScore)


#%% Random forrest classifier
rdfrClf = ensemble.RandomForestClassifier()
rdfrClf.fit(bandDataTrain, berClassesTrain)
rdfrScore = treeClf.score(bandDataTest, berClassesTest)
print(rdfrScore)

