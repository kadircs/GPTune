# GPTune Copyright (c) 2019, The Regents of the University of California,
# through Lawrence Berkeley National Laboratory (subject to receipt of any
# required approvals from the U.S.Dept. of Energy) and the University of
# California, Berkeley.  All rights reserved.
#
# If you have questions about your rights to use or distribute this software,
# please contact Berkeley Lab's Intellectual Property Office at IPO@lbl.gov.
#
# NOTICE. This Software was developed under funding from the U.S. Department
# of Energy and the U.S. Government consequently retains certain rights.
# As such, the U.S. Government has been granted for itself and others acting
# on its behalf a paid-up, nonexclusive, irrevocable, worldwide license in
# the Software to reproduce, distribute copies to the public, prepare
# derivative works, and perform publicly and display publicly, and to permit
# other to do so.
#


import abc
from typing import Collection, Tuple
import numpy as np

from problem import Problem
from computer import Computer
from data import Data


class Model(abc.ABC):

    def __init__(self, problem : Problem, computer : Computer, **kwargs):

        self.problem = problem
        self.computer = computer

    @abc.abstractmethod
    def train(self, data : Data, **kwargs):

        raise Exception("Abstract method")

    @abc.abstractmethod
    def update(self, newdata : Data, do_train: bool = False, **kwargs):

        raise Exception("Abstract method")

    @abc.abstractmethod
    def predict(self, points : Collection[np.ndarray], tid : int, **kwargs) -> Collection[Tuple[float, float]]:

        raise Exception("Abstract method")

