"""Combined bit-exact CIC decimator and FIR compensation pipeline."""

from collections.abc import Iterable

from model.cic import CICDecimator
from model.fir import FIRCompensator


class CICFIRPipeline:
	"""Process ADC samples through the CIC and FIR models."""

	def __init__(
		self,
		cic: CICDecimator | None = None,
		fir: FIRCompensator | None = None,
	) -> None:
		self.cic = cic if cic is not None else CICDecimator()
		self.fir = fir if fir is not None else FIRCompensator()

	def reset(self) -> None:
		"""Reset both filters to their defined zero states."""
		self.cic.reset()
		self.fir.reset()

	def process_sample(
		self,
		sample: int,
	) -> int | None:
		"""Process one ADC-rate sample through the complete pipeline."""
		cic_output = self.cic.process_sample(sample)

		if cic_output is None:
			return None

		return self.fir.process_sample(cic_output)

	def process(
		self,
		samples: Iterable[int],
	) -> list[int]:
		"""Process a sequence and return only valid low-rate outputs."""
		outputs: list[int] = []

		for sample in samples:
			result = self.process_sample(sample)

			if result is not None:
				outputs.append(result)

		return outputs