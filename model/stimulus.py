import numpy as np


def impulse(length: int) -> list[int]:
	"""Return a unit impulse containing exactly length samples."""
	if length <= 0:
		raise ValueError("length must be greater than zero")

	return [1] + [0] * (length - 1)


def step(length: int, amplitude: int = 1) -> list[int]:
	"""Return a constant integer sequence containing exactly length samples."""
	if length <= 0:
		raise ValueError("length must be greater than zero")

	return [amplitude] * length


def sine(
	fs: float,
	f0: float,
	amplitude: int,
	count: int,
) -> list[int]:
	"""Return a deterministically quantized integer sine sequence."""
	if fs <= 0:
		raise ValueError("fs must be greater than zero")

	if count <= 0:
		raise ValueError("count must be greater than zero")

	sample_indices = np.arange(count)

	samples = np.rint(
		amplitude
		* np.sin(
			2
			* np.pi
			* f0
			* sample_indices
			/ fs
		)
	).astype(int)

	return samples.tolist()