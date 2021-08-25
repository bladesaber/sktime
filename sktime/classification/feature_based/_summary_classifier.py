# -*- coding: utf-8 -*-
"""Summary Classifier.

Pipeline classifier using the Catch22 transformer and an estimator.
"""

__author__ = ["MatthewMiddlehurst"]
__all__ = ["SummaryClassifier"]

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.utils.multiclass import class_distribution

from sktime.base._base import _clone_estimator
from sktime.classification.base import BaseClassifier
from sktime.transformations.panel.catch22 import Catch22


class SummaryClassifier(BaseClassifier):
    """Canonical Time-series Characteristics (catch22) classifier.

    This classifier simply transforms the input data using the Catch22 [1]
    transformer and builds a provided estimator using the transformed data.

    Parameters
    ----------
    outlier_norm : bool, default=False
        Normalise each series during the two outlier catch22 features, which can take a
        while to process for large values
    estimator : sklearn classifier, default=None
        An sklearn estimator to be built using the transformed data. Defaults to a
        Random Forest with 200 trees.
    n_jobs : int, default=1
        The number of jobs to run in parallel for both `fit` and `predict`.
        ``-1`` means using all processors.
    random_state : int or None, default=None
        Seed for random, integer.

    Attributes
    ----------
    n_classes_ : int
        Number of classes. Extracted from the data.
    classes_ : ndarray of shape (n_classes)
        Holds the label for each class.

    See Also
    --------
    Catch22

    Notes
    -----
    Authors `catch22ForestClassifier <https://github.com/chlubba/sktime-catch22>`_.

    For the Java version, see `tsml <https://github.com/uea-machine-learning/tsml/blob
    /master/src/main/java/tsml/classifiers/hybrids/Catch22Classifier.java>`_.

    References
    ----------
    .. [1] Lubba, Carl H., et al. "catch22: Canonical time-series characteristics."
        Data Mining and Knowledge Discovery 33.6 (2019): 1821-1852.
        https://link.springer.com/article/10.1007/s10618-019-00647-x

    Examples
    --------
    >>> from sktime.classification.feature_based import Catch22Classifier
    >>> from sktime.datasets import load_italy_power_demand
    >>> X_train, y_train = load_italy_power_demand(split="train", return_X_y=True)
    >>> X_test, y_test = load_italy_power_demand(split="test", return_X_y=True)
    >>> clf = Catch22Classifier()
    >>> clf.fit(X_train, y_train)
    Catch22Classifier(...)
    >>> y_pred = clf.predict(X_test)
    """

    _tags = {
        "capability:multivariate": True,
        "capability:unequal_length": False,
        "capability:missing_values": False,
        "capability:train_estimate": False,
        "capability:contractable": False,
    }

    def __init__(
        self,
        outlier_norm=False,
        estimator=None,
        n_jobs=1,
        random_state=None,
    ):
        self.outlier_norm = outlier_norm
        self.estimator = estimator

        self.n_jobs = n_jobs
        self.random_state = random_state

        self._transformer = None
        self._estimator = None
        self.n_classes_ = 0
        self.classes_ = []
        super(SummaryClassifier, self).__init__()

    def _fit(self, X, y):
        self.classes_ = class_distribution(np.asarray(y).reshape(-1, 1))[0][0]
        self.n_classes_ = np.unique(y).shape[0]

        self._transformer = Catch22(outlier_norm=self.outlier_norm)
        self._estimator = _clone_estimator(
            RandomForestClassifier(n_estimators=200)
            if self.estimator is None
            else self.estimator,
            self.random_state,
        )

        m = getattr(self._estimator, "n_jobs", None)
        if callable(m):
            self._estimator.n_jobs = self.n_jobs

        X_t = self._transformer.fit_transform(X, y)
        X_t = np.nan_to_num(X_t, False, 0, 0, 0)
        self._estimator.fit(X_t, y)

    def _predict(self, X):
        return self._estimator.predict(self._transformer.transform(X))

    def _predict_proba(self, X):
        m = getattr(self._estimator, "predict_proba", None)
        if callable(m):
            return self._estimator.predict_proba(self._transformer.transform(X))
        else:
            dists = np.zeros((X.shape[0], self.n_classes_))
            preds = self._estimator.predict(self._transformer.transform(X))
            for i in range(0, X.shape[0]):
                dists[i, np.where(self.classes_ == preds[i])] = 1
            return dists
