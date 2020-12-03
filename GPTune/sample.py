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
from typing import Callable
import math
import numpy as np
import time

import skopt.space
from skopt.space import *
from autotune.space import Space


class Sample(abc.ABC):

    @abc.abstractmethod
    def sample(self, n_samples : int, space : Space, **kwargs):

        raise Exception("Abstract method")

    def sample_constrained(self, n_samples : int, space : Space, check_constraints : Callable = None, check_constraints_kwargs : dict = {}, **kwargs):

        if (check_constraints is None):
            S = self.sample(n_samples, space)

        else:

            if ('sample_max_iter' in kwargs):
                sample_max_iter = kwargs['sample_max_iter']
            else:
                if ('options' in kwargs):
                    sample_max_iter = kwargs['options']['sample_max_iter']
                else:
                    sample_max_iter = 1

            S = []
            cpt = 0
            n_itr = 0
            while ((cpt < n_samples) and (n_itr < sample_max_iter)):
                # t1 = time.time_ns()
                S2 = self.sample(n_samples, space, kwargs=kwargs)
                # t2 = time.time_ns()
                # print('sample_para:',(t2-t1)/1e9)

                for s_norm in S2:
                    # print("jiji",s_norm)
                    s_orig = space.inverse_transform(np.array(s_norm, ndmin=2))[0]
                    kwargs2 = {d.name: s_orig[i] for (i, d) in enumerate(space)}
                    # print("dfdfdfdfd",kwargs2)
                    kwargs2.update(check_constraints_kwargs)
                    if (check_constraints(kwargs2)):
                        S.append(s_norm)
                        cpt += 1
                        if (cpt >= n_samples):
                            break
                # print('input',S,space[0],isinstance(space[0], Categorical))

                n_itr += 1
                if(n_itr%1000==0 and n_itr>=1000):
                    print('n_itr',n_itr,'still trying generating constrained samples...')


            if (cpt < n_samples):
                raise Exception("Only %d valid samples were generated while %d were requested.\
                        The constraints might be too hard to satisfy.\
                        Consider increasing 'sample_max_iter', or, provide a user-defined sampling method."%(len(S), n_samples))
        # print('reqi',S,'nsample',n_samples,sample_max_iter,space)
        S = np.array(S[0:n_samples]).reshape((n_samples, len(space)))

        return S

    def sample_inputs(self, n_samples : int, IS : Space, check_constraints : Callable = None, check_constraints_kwargs : dict = {}, **kwargs):

        return self.sample_constrained(n_samples, IS, check_constraints = check_constraints, check_constraints_kwargs = check_constraints_kwargs, **kwargs)

    def sample_parameters(self, n_samples : int, I : np.ndarray, IS : Space, PS : Space, check_constraints : Callable = None, check_constraints_kwargs : dict = {}, **kwargs):

        P = []
        for t in I:
            # print('before inverse_transform:',np.array(t, ndmin=2))
            I_orig = IS.inverse_transform(np.array(t, ndmin=2))[0]
            # I_orig = t
            # print('after inverse_transform I_orig:',I_orig)
            kwargs2 = {d.name: I_orig[i] for (i, d) in enumerate(IS)}
            kwargs2.update(check_constraints_kwargs)
            xs = self.sample_constrained(n_samples, PS, check_constraints = check_constraints, check_constraints_kwargs = kwargs2, **kwargs)
            P.append(xs)

        return P

