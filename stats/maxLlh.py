import scipy.stats._multivariate as mult
import numpy as np


class MaxLlh:
    
    def fit(self, X, Y):
        """
        X: n * b numpy array
            n: nr of samples
            b: nr of bands
        """
        
        classData = {}
        for x, y in zip(X, Y):
            if y not in classData:
                classData[y] = []
            classData[y].append(x)
        
        stats = {}
        for className, classData in classData.items():
            mean = np.mean(classData, axis=0)
            dm = X - mean
            cov = dm.transpose() @ dm
            stats[className] = {"mean": mean, "cov": cov}

        self.stats = stats


    def predict(self, X):
        """
            X: n * b numpy array
                n: nr of samples
                b: nr of bands
        """
        nrSamples, nrBands = X.shape

        llhsPerClass = {}
        for className, classStats in self.stats.items():
            dist = mult.multivariate_normal(classStats["mean"], classStats["cov"], allow_singular=True)
            llhs = dist.pdf(X)
            llhsPerClass[className] = llhs
        
        predictions = np.zeros((nrSamples,))
        for i in range(nrSamples):
            maxLlh = 0
            maxLlhClass = "NONE"
            for className, llhs in llhsPerClass.items():
                llh = llhs[i]
                if llh > maxLlh:
                    maxLlh = llh
                    maxLlhClass = className
            predictions[i] = maxLlhClass

        return predictions


    def score(self, X, Y):
        nrSamples, nrBands = X.shape
        Ypred = np.array(self.predict(X))
        err = Y - Ypred
        err2 = err * err
        sse = np.sum(err2)
        return sse


