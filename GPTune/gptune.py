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

import copy
import functools
import time

from autotune.problem import TuningProblem

from problem import Problem
from computer import Computer
from data import Data
from options import Options
from sample import *
from model import *
from search import *
import math

import mpi4py
from mpi4py import MPI		  
class GPTune(object):

	def __init__(self, tuningproblem : TuningProblem, computer : Computer = None, data : Data = None, options : Options = None, **kwargs):

		"""
		tuningproblem: object defining the characteristics of the tuning (See file 'autotuner/autotuner/tuningproblem.py')
		computer     : object specifying the architectural characteristics of the computer to run on (See file 'GPTune/computer.py')
		data         : object containing the data of a previous tuning (See file 'GPTune/data.py')
		options      : object defining all the options that will define the behaviour of the tuner (See file 'GPTune/options.py')
		"""
		self.problem  = Problem(tuningproblem)
		if (computer is None):
			computer = Computer()
		self.computer = computer
		if (data is None):
			data = Data(self.problem)
		self.data     = data
		if (options is None):
			options = Options()
		self.options  = options

	def MLA(self, NS, NS1 = None, NI = None, Igiven = None, **kwargs):

		print('\n\n\n------Starting MLA with %d tasks '%(NI))	
		stats = {
		  "time_tunner": 0,
		  "time_fun": 0
		}
		time_fun=0
				
		np.set_printoptions(suppress=False,precision=4)
		
		if (self.data.P is not None and len(self.data.P[0])>=NS):
			print('self.data.P[0])>=NS, no need to run MLA. Returning...')
			return (copy.deepcopy(self.data), None,stats)	
		
		t3 = time.time_ns()
		
		options1 = copy.deepcopy(self.options)
		kwargs.update(options1)

		""" Multi-task Learning Autotuning """

		
		if(Igiven is not None and self.data.I is None):  # building the MLA model for each of the given tasks
			self.data.I = Igiven 

########## normalize the data as the user always work in the original space

		if self.data.I is not None: # from a list of lists to a 2D numpy array
			self.data.I = self.problem.IS.transform(self.data.I)

		if self.data.P is not None:	# from a list of (list of lists) to a list of 2D numpy arrays		
			tmp=[]
			for x in self.data.P:		
				xNorm = self.problem.PS.transform(x)
				tmp.append(xNorm)
			self.data.P=tmp				
		
#        if (self.mpi_rank == 0):

		sampler = eval(f'{kwargs["sample_class"]}()')
		if (self.data.I is None):

			if (NI is None):
				raise Exception("Number of problems to be generated (NI) is not defined")

			check_constraints = functools.partial(self.computer.evaluate_constraints, self.problem, inputs_only = True, kwargs = kwargs)
			self.data.I = sampler.sample_inputs(n_samples = NI, IS = self.problem.IS, check_constraints = check_constraints, **kwargs)
			# print("riji",type(self.data.I),type(self.data.I[0]))
		
		if (self.data.P is not None and len(self.data.P) !=len(self.data.I)):
			raise Exception("len(self.data.P) !=len(self.data.I)")		
		
		if (self.data.P is None):
			if (NS1 is not None and NS1>NS):
				raise Exception("NS1>NS")
				
			if (NS1 is None):
				NS1 = min(NS - 1, 3 * self.problem.DP) # General heuristic rule in the litterature

			check_constraints = functools.partial(self.computer.evaluate_constraints, self.problem, inputs_only = False, kwargs = kwargs)
			self.data.P = sampler.sample_parameters(n_samples = NS1, I = self.data.I, IS = self.problem.IS, PS = self.problem.PS, check_constraints = check_constraints, **kwargs)
#            #XXX add the info of problem.models here
#            for P2 in P:
#                for x in P2:
#                    x = np.concatenate(x, np.array([m(x) for m in self.problems.models]))
		# print("good?")
		
		if (self.data.O is not None and len(self.data.O) !=len(self.data.I)):
			raise Exception("len(self.data.O) !=len(self.data.I)")
		
		t1 = time.time_ns()
		if (self.data.O is None):
			self.data.O = self.computer.evaluate_objective(self.problem, self.data.I, self.data.P, kwargs = kwargs) 
		t2 = time.time_ns()
		time_fun = time_fun + (t2-t1)/1e9
		# print("good!")	
#            if ((self.mpi_comm is not None) and (self.mpi_size > 1)):
#                mpi_comm.bcast(self.data, root=0)
#
#        else:
#
#            self.data = mpi_comm.bcast(None, root=0)

		NS2 = NS - len(self.data.P[0])
		# mpi4py.MPI.COMM_WORLD.Barrier()
		modeler  = eval(f'{kwargs["model_class"]} (problem = self.problem, computer = self.computer)')
		searcher = eval(f'{kwargs["search_class"]}(problem = self.problem, computer = self.computer)')
		for optiter in range(NS2): # YL: each iteration adds one sample until total #sample reaches NS
			# print("riji",type(self.data.I),type(self.data.I[0]))
			newdata = Data(problem = self.problem, I = self.data.I)
			# print("before train",optiter,NS2)
		
			modeler.train(data = self.data, **kwargs)
			# print("after train",self.data.P,'d',newdata.P) 
			# print("after train",self.data.O,'d',newdata.O) 
			# print("after train",self.data.I,'d',newdata.I) 
			res = searcher.search_multitask(data = self.data, model = modeler, **kwargs)
			newdata.P = [x[1][0] for x in res]
	#XXX add the info of problem.models here

	#            if (self.mpi_rank == 0):

			t1 = time.time_ns()
			newdata.O = self.computer.evaluate_objective(problem = self.problem, fun = self.problem.objective, I = newdata.I, P = newdata.P, kwargs = kwargs)
			t2 = time.time_ns()
			time_fun = time_fun + (t2-t1)/1e9		

	#                if ((self.mpi_comm is not None) and (self.mpi_size > 1)):
	#                    mpi_comm.bcast(newdata.O, root=0)
	#
	#            else:
	#
	#                newdata.O = mpi_comm.bcast(None, root=0)

			self.data.merge(newdata)
		
		
########## denormalize the data as the user always work in the original space
		if self.data.I is not None:    # from 2D numpy array to a list of lists    
			self.data.I = self.problem.IS.inverse_transform(self.data.I)
		if self.data.P is not None:    # from a collection of 2D numpy arrays to a list of (list of lists)       
			tmp=[]
			for x in self.data.P:		
				xOrig = self.problem.PS.inverse_transform(x)
				tmp.append(xOrig)		
			self.data.P=tmp		
			
		t4 = time.time_ns()
		stats['time_tunner'] = (t4-t3)/1e9		
		stats['time_fun'] = time_fun			
		
		
		return (copy.deepcopy(self.data), modeler,stats)

		
	def TLA1(self, Tnew, nruns):
       
		print('\n\n\n------Starting TLA1 for task: ',Tnew)

		stats = {
		  "time_tunner": 0,
		  "time_fun": 0
		}
		time_fun=0
		
		t3=time.time_ns()
		# Initialization
		kwargs = copy.deepcopy(self.options)
		ntso = len(self.data.I)
		ntsn = len(Tnew)

		PSopt =[]
		for i in range(ntso):
			PSopt.append(self.data.P[i][np.argmin(self.data.O[i])])	
		# YSopt = np.array([[self.data.O[k].min()] for k in range(ntso)])
		MSopt = []



		# convert the task spaces to the normalized spaces
		INorms=[]
		for t in self.data.I:		
			INorm = self.problem.IS.transform(np.array(t, ndmin=2))[0]
			INorms.append(INorm.reshape((-1, self.problem.DI)))		
		INorms = np.vstack([INorms[i] for i in range(ntso)]).reshape((ntso,self.problem.DI))
  
		tmp=[]
		for t in Tnew:		
			INorm = self.problem.IS.transform(np.array(t, ndmin=2))[0]
			tmp.append(INorm.reshape((-1, self.problem.DI)))		
		InewNorms=np.vstack([tmp[i] for i in range(ntsn)]).reshape((ntsn,self.problem.DI))
   
  
  
		# convert the parameter spaces to the normalized spaces  
		PSoptNorms = self.problem.PS.transform(PSopt)
		columns = []
		for j in range(self.problem.DP):
			columns.append([])
		for i in range(ntso):
			for j in range(self.problem.DP):
				columns[j].append(PSoptNorms[i][j])
		PSoptNorms = []
		for j in range(self.problem.DP):
			PSoptNorms.append(np.asarray(columns[j]).reshape((ntso, -1))) 

		

		# Predict optimums of new tasks
		for k in range(self.problem.DP):
			K = GPy.kern.RBF(input_dim=self.problem.DI)
			M = GPy.models.GPRegression(INorms, PSoptNorms[k], K)
			# M.optimize_restarts(num_restarts = 10, robust=True, verbose=False, parallel=False, num_processes=None, messages="False")
			M.optimize_restarts(num_restarts = kwargs['model_restarts'], robust=True, verbose = kwargs['verbose'], parallel = (kwargs['model_threads'] > 1), num_processes = kwargs['model_threads'], messages = "False", optimizer = 'lbfgs', start = None, max_iters = kwargs['model_max_iters'], ipython_notebook = False, clear_after_finish = True)
			MSopt.append(M)

		aprxoptsNorm=np.hstack([MSopt[k].predict_noiseless(InewNorms)[0] for k in range(self.problem.DP)])  # the index [0] is the mean value, [1] is the variance
		aprxoptsNorm=np.minimum(aprxoptsNorm,(1-1e-12)*np.ones((ntsn,self.problem.DP)))
		aprxoptsNorm=np.maximum(aprxoptsNorm,(1e-12)*np.ones((ntsn,self.problem.DP)))
		# print('aprxoptsNorm',aprxoptsNorm,type(aprxoptsNorm))
		aprxopts = self.problem.PS.inverse_transform(aprxoptsNorm)
		# print('aprxopts',aprxopts,type(aprxopts),type(aprxopts[0]))
		
  






		aprxoptsNormList=[]
		# TnewNormList=[]
		for i in range(ntsn):
			aprxoptsNormList.append([aprxoptsNorm[i,:]])  # this makes sure for each task, there is only one sample parameter set
			# InewNormList.append(InewNorms[i,:])
		
		t1 = time.time_ns()
		O = self.computer.evaluate_objective(problem = self.problem, fun = self.problem.objective, I = InewNorms, P =aprxoptsNormList, kwargs = kwargs)
		t2 = time.time_ns()
		time_fun = time_fun + (t2-t1)/1e9		

		#        print(aprxopts)
		#        pickle.dump(aprxopts, open('TLA1.pkl', 'w'))

		t4 = time.time_ns()
		stats['time_tunner'] = (t4-t3)/1e9		
		stats['time_fun'] = time_fun		
		
		return (aprxopts,O,stats)

	def TLA2(): # co-Kriging

		pass
