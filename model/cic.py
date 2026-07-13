def wrap_signed(value: int, width: int) -> int:
	"""Wrap an integer to a signed two's-complement value of the given width."""
	if width <= 0:
		raise ValueError("width must be greater than zero")

	modulus = 1 << width
	wrapped = value % modulus
	sign_boundary = 1 << (width - 1)

	if wrapped >= sign_boundary:
		wrapped = wrapped - modulus

	return wrapped


class CICDecimator:
	def __init__(
		self,
		r: int = 8,
		n: int = 3,
		m: int = 1,
		input_width: int = 12,
		internal_width: int = 21,
		output_width: int = 21,
	) -> None:
		if r <= 0:
			raise ValueError("r must be greater than zero")

		if n <= 0:
			raise ValueError("n must be greater than zero")

		if m <= 0:
			raise ValueError("m must be greater than zero")

		if input_width <= 0:
			raise ValueError("input_width must be greater than zero")

		if internal_width <= 0:
			raise ValueError("internal_width must be greater than zero")

		if output_width <= 0:
			raise ValueError("output_width must be greater than zero")

		if output_width != internal_width:
			raise ValueError(
				"output_width must equal internal_width for CIC v0.1"
			)

		self.r = r
		self.n = n
		self.m = m
		self.input_width = input_width
		self.internal_width = internal_width
		self.output_width = output_width

		self.reset()

	def reset(self) -> None:
		"""Clear all CIC state and restart the decimation counter."""
		self.integrators = [0 for _ in range(self.n)]

		self.comb_delays = [
			[0 for _ in range(self.m)]
			for _ in range(self.n)
		]

		self.counter = 0

	def process_sample(self, sample: int) -> int | None:
		minimum_input = -(1 << (self.input_width - 1))
		maximum_input = (1 << (self.input_width - 1)) - 1

		if sample < minimum_input or sample > maximum_input:
			raise ValueError(
				f"sample must be between {minimum_input} and {maximum_input}"
			)

		stage_input = sample

		for stage in range(self.n):
			self.integrators[stage] = wrap_signed(
				self.integrators[stage] + stage_input,
				self.internal_width,
			)

			stage_input = self.integrators[stage]

		if self.counter != self.r - 1:
			self.counter += 1
			return None

		self.counter = 0
		comb_input = stage_input

		for stage in range(self.n):
			delay_line = self.comb_delays[stage]

			delayed_value = delay_line.pop(0)
			delay_line.append(comb_input)

			comb_output = wrap_signed(
				comb_input - delayed_value,
				self.internal_width,
			)

			comb_input = comb_output

		return wrap_signed(comb_input, self.output_width)