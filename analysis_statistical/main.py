#%% imports
from sklearn import tree
from sklearn import ensemble
from stats.maxLlh import MaxLlh
from dataReaders.reader import loadData
import numpy as np


#%% configuration
nrTrainingSamples = 1000
nrTestingSamples = 100


#%% data
bandData = np.load("bandData.npy")
berClasses = np.load("berClasses.npy")
# bandData, berClasses = loadData(nrTrainingSamples + nrTestingSamples)
# np.save("bandData.npy", bandData)
# np.save("berClasses.npy", berClasses)

#%%
bandDataTrain = bandData[:nrTrainingSamples]
bandDataTest = bandData[nrTrainingSamples:]
berClassesTrain = berClasses[:nrTrainingSamples]
berClassesTest = berClasses[nrTrainingSamples:]


#%% Maximum likelihood classifier
mllhClf = MaxLlh()
mllhClf.fit(bandDataTrain, np.round(berClassesTrain))
mllhScore = mllhClf.score(bandDataTest, berClassesTest)
print(mllhScore)


#%% Tree classifier
treeClf = tree.DecisionTreeRegressor(max_depth=4, min_samples_leaf=3)
treeClf.fit(bandDataTrain, berClassesTrain)
treeScore = treeClf.score(bandDataTest, berClassesTest)
print(treeScore)

#%%
import matplotlib.pyplot as plt
figure = plt.figure(figsize=(10, 10))
ax = plt.axes()
tree.plot_tree(treeClf, ax=ax, fontsize=8, label='root', filled=True, impurity=False)



#%% Random forrest classifier
rdfrClf = ensemble.RandomForestRegressor()
rdfrClf.fit(bandDataTrain, berClassesTrain)
rdfrScore = treeClf.score(bandDataTest, berClassesTest)
print(rdfrScore)


# %%
