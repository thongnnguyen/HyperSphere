import time

import numpy as np
from torch.autograd import Variable

from HyperSphere.coordinate.transformation import rect2spherical, spherical2rect
from HyperSphere.GP.models.gp_regression import GPRegression
from HyperSphere.GP.kernels.modules.matern52 import Matern52
from HyperSphere.GP.inference.inference import Inference
from HyperSphere.BO.acquisition_maximization import suggest
from HyperSphere.feature_map.functionals import *

from HyperSphere.test_functions.benchmarks import branin


def sphere_BO(func, n_eval=200):
	ndim = func.dim
	search_cube_half_sidelength = 1
	search_sphere_radius = 1
	rectangle_input = Variable(torch.ger(torch.FloatTensor([0, min(search_sphere_radius / ndim ** 0.5, search_cube_half_sidelength)]), torch.ones(ndim)))
	output = Variable(torch.zeros(rectangle_input.size(0), 1))
	for i in range(rectangle_input.size(0)):
		output[i] = func(rectangle_input[i])
	sphere_input = rect2spherical(rectangle_input)
	sphere_input[sphere_input != sphere_input] = 0

	kernel_input_map = periodize_one

	kernel = Matern52(ndim=ndim + kernel_input_map.dim_change, input_map=kernel_input_map)
	model = GPRegression(kernel=kernel)

	time_list = [time.time()] * 2
	elapes_list = [0, 0]

	inference = Inference((rectangle_input, output), model)
	inference.sampling(n_sample=100, n_burnin=0, n_thin=1)

	for e in range(n_eval):
		inference = Inference((sphere_input, output), model)
		learned_params = inference.sampling(n_sample=10, n_burnin=0, n_thin=10)
		next_eval_point = suggest(inference, learned_params, reference=torch.min(output)[0])
		next_eval_point[0:1, 0:1] = torch.fmod(torch.abs(next_eval_point[0:1, 0:1]), search_sphere_radius)

		time_list.append(time.time())
		elapes_list.append(time_list[-1] - time_list[-2])

		sphere_input = torch.cat([sphere_input, next_eval_point])
		rectangular_input = spherical2rect(sphere_input)
		output = torch.cat([output, func(rectangular_input[-1])])

		for d in range(sphere_input.size(0)):
			sphr_str = ('%+.4f/' % sphere_input.data[d, 0]) + '/'.join(['%+.3fpi' % (sphere_input.data[d, i]/math.pi) for i in range(1, sphere_input.size(1))])
			rect_str = '/'.join(['%+.4f' % rectangular_input.data[d, i] for i in range(0, rectangular_input.size(1))])
			time_str = time.strftime('%H:%M:%S', time.gmtime(time_list[d])) + '(' + time.strftime('%H:%M:%S', time.gmtime(elapes_list[d])) +')  '
			print(('%4d : ' % (d+1)) + time_str + rect_str + ' & ' + sphr_str + '    =>' + ('%12.6f' % output.data[d].squeeze()[0]))


if __name__ == '__main__':
	sphere_BO(branin, n_eval=100)
