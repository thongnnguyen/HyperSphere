import math

import torch


def rect2spherical(x, shuffle_ind=None):
	_, n_dim = x.size()
	if shuffle_ind is None:
		shuffle_ind = torch.arange(0, n_dim).type_as(x.data if hasattr(x, 'data') else x).long()
	reverse_ind = torch.arange(n_dim-1, -1, -1).type_as(x.data if hasattr(x, 'data') else x).long()
	x_shuffled = x[:, shuffle_ind]
	x_shuffled_sq_accum = torch.sqrt(torch.cumsum((x_shuffled**2)[:, reverse_ind], dim=1)[:, reverse_ind])
	rphi = torch.cat((x_shuffled_sq_accum[:, [0]], x_shuffled[:, 0:n_dim-1]), dim=1)
	if n_dim > 2:
		rphi[:, 1:n_dim-1] = torch.acos(x_shuffled[:, 0:n_dim-2]/x_shuffled_sq_accum[:, 0:n_dim-2])
	rphi[:, -1] = torch.acos(x_shuffled[:, -2] / x_shuffled_sq_accum[:, -2])
	if hasattr(x, 'data'):
		rphi.data[:, -1][x_shuffled.data[:, -1] < 0] = 2 * math.pi - rphi.data[:, -1][x_shuffled.data[:, -1] < 0]
		zero_radius_mask = rphi.data[:, 0] == 0
		n_zero_radius = torch.sum(zero_radius_mask)
		if n_zero_radius > 0:
			_, zero_radius = torch.sort(zero_radius_mask, 0, descending=True)
			zero_radius = zero_radius[:n_zero_radius]
			rphi.data[zero_radius[0]] = 0.5 * math.pi
			if n_zero_radius > 1:
				rphi.data[zero_radius[1:]] = rphi.data.new(n_zero_radius - 1, n_dim).uniform_() * math.pi
			rphi.data[zero_radius, zero_radius.new(1).zero_()] = rphi.data.new(n_zero_radius).fill_(0)
			rphi.data[zero_radius, zero_radius.new(1).fill_(n_dim-1)] *= 2
	else:
		rphi[:, -1][x_shuffled[:, -1] < 0] = 2 * math.pi - rphi[:, -1][x_shuffled[:, -1] < 0]
		zero_radius_mask = rphi[:, 0] == 0
		n_zero_radius = torch.sum(zero_radius_mask)
		if n_zero_radius > 0:
			_, zero_radius = torch.sort(zero_radius_mask, 0, descending=True)
			zero_radius = zero_radius[:n_zero_radius]
			rphi[zero_radius[0]] = 0.5 * math.pi
			if n_zero_radius > 1:
				rphi[zero_radius[1:]] = rphi.new(n_zero_radius - 1, n_dim).uniform_() * math.pi
			rphi[zero_radius, zero_radius.new(1).zero_()] = rphi.new(n_zero_radius).fill_(0)
			rphi[zero_radius, zero_radius.new(1).fill_(n_dim - 1)] *= 2
	return rphi


def spherical2rect(rphi, shuffle_ind=None):
	"""

	:param rphi: r in [0, radius], phi0 in [0, pi], phi1 in [0, pi], ..., phi(n-1) in [0, 2pi] 
	:param shuffle_ind: 
	:return: 
	"""
	_, n_dim = rphi.size()
	if shuffle_ind is None:
		shuffle_ind = torch.arange(0, n_dim)
	inv_shuffle_ind = shuffle_ind_inverse(shuffle_ind)
	x = torch.cumprod(torch.cat((rphi[:, [0]], torch.sin(rphi[:, 1:n_dim])), dim=1), dim=1)
	x[:, 0:n_dim-1] = x[:, 0:n_dim-1] * torch.cos(rphi[:, 1:n_dim])
	return x[:, inv_shuffle_ind]


def shuffle_ind_inverse(shuffle_ind):
	_, inv_shuffle_ind = torch.sort(shuffle_ind, 0)
	return inv_shuffle_ind


def rphi2phi(rphi, radius):
	"""
	:param rphi: r in [0, radius], phi_i in [0, pi] for i in [1, d-2], phi_i in [0, 2pi] for i = d-1 
	:param radius
	:return: point in cube [0, 1] ^ d 
	"""
	phi0 = torch.acos(1 - 2 * rphi[:, :1] / radius) / math.pi
	phi = torch.cat([phi0, rphi[:, 1:-1] / math.pi, rphi[:, -1:] / (2.0 * math.pi)], 1)
	return phi


def phi2rphi(phi, radius):
	"""
	:param phi: in cube [0, 1] ^ d 
	:param radius: R, pi, ..., pi, 2pi
	:return: r in [0, R], phi_i in [0, pi] for i in [1, d-2], phi_i in [0, 2pi] for i = d-1 
	"""
	r = 0.5 * (1 - torch.cos(phi[:, 0:1] * math.pi)) * radius
	rphi = torch.cat([r, phi[:, 1:-1] * math.pi, phi[:, -1:] * 2 * math.pi], 1)
	return rphi


def check_rphi(rphi):
	assert torch.sum(rphi < 0) == 0
	assert torch.sum(rphi[:, 1:-1] > math.pi) == 0
	assert torch.sum(rphi[:, -1] > 2 * math.pi) == 0


if __name__ == '__main__':
	n_dim = 5
	n_data = 5
	x = torch.randn(n_data, n_dim)
	_, shuffle_ind = torch.sort(torch.randn(n_dim), 0)
	# shuffle_ind = torch.arange(0, n_dim).long()
	rphi = rect2spherical(x, shuffle_ind)
	x_recovered = spherical2rect(rphi, shuffle_ind)
	print(x)
	print(x_recovered)
	print(torch.dist(x, x_recovered))
	# phi = torch.FloatTensor(n_data, n_dim-1).uniform_(0, 2*math.pi)
	# r_phi = torch.cat((torch.ones(n_data, 1) * 1.0, phi), dim=1)
	# r_phi_domain = rect2spherical(spherical2rect(r_phi))
	# in_domain = (r_phi[:, 1:-1] <= math.pi).type_as(r_phi)
	# in_domain_accum = torch.cumsum(in_domain, dim=1)
	# not_in_domain = (r_phi[:, 1:-1] > math.pi).type_as(r_phi)
	# not_in_domain_accum = torch.cumsum(not_in_domain, dim=1)
	# diff = (r_phi[:, 1:-1] - r_phi_domain[:, 1:-1]) / math.pi
	# sum = (r_phi[:, 1:-1] + r_phi_domain[:, 1:-1]) / math.pi
	# for i in range(n_data):
	# 	print(torch.stack((in_domain[i], in_domain_accum[i], not_in_domain_accum[i], sum[i], diff[i]), dim=0))

