library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.fir_coefficients_pkg.all;


entity fir_comp is
	generic (
		G_INPUT_WIDTH       : positive := 21;
		G_PRODUCT_WIDTH     : positive := 39;
		G_ACCUMULATOR_WIDTH : positive := 44;
		G_FRACTIONAL_BITS   : positive := 17;
		G_OUTPUT_WIDTH      : positive := 16
	);
	port (
		clk        : in  std_logic;
		rst        : in  std_logic;

		in_valid   : in  std_logic;
		in_sample  : in  signed(
			G_INPUT_WIDTH - 1 downto 0
		);

		out_valid  : out std_logic;
		out_sample : out signed(
			G_OUTPUT_WIDTH - 1 downto 0
		)
	);
end entity fir_comp;


architecture rtl of fir_comp is

	type t_sample_array is array (
		natural range <>
	) of signed(
		G_INPUT_WIDTH - 1 downto 0
	);


	function signed_maximum(
		width : positive
	) return signed is
		variable result : signed(
			width - 1 downto 0
		) := (
			others => '1'
		);
	begin
		result(width - 1) := '0';

		return result;
	end function;


	function signed_minimum(
		width : positive
	) return signed is
		variable result : signed(
			width - 1 downto 0
		) := (
			others => '0'
		);
	begin
		result(width - 1) := '1';

		return result;
	end function;


	constant C_OUTPUT_MAXIMUM : signed(
		G_OUTPUT_WIDTH - 1 downto 0
	) := signed_maximum(
		G_OUTPUT_WIDTH
	);

	constant C_OUTPUT_MINIMUM : signed(
		G_OUTPUT_WIDTH - 1 downto 0
	) := signed_minimum(
		G_OUTPUT_WIDTH
	);

	constant C_ROUNDING_OFFSET_EXTENDED : signed(
		G_ACCUMULATOR_WIDTH downto 0
	) := shift_left(
		to_signed(
			1,
			G_ACCUMULATOR_WIDTH + 1
		),
		G_FRACTIONAL_BITS - 1
	);

	signal sample_history : t_sample_array(
		0 to C_FIR_TAPS - 1
	);

begin

	assert G_FRACTIONAL_BITS =
		C_FIR_FRACTIONAL_BITS
		report
			"G_FRACTIONAL_BITS must match "
			& "the frozen Q17 coefficients"
		severity failure;

	assert G_PRODUCT_WIDTH =
		G_INPUT_WIDTH + C_FIR_COEFFICIENT_WIDTH
		report
			"G_PRODUCT_WIDTH must equal input width "
			& "plus coefficient width"
		severity failure;

	assert G_ACCUMULATOR_WIDTH >=
		G_PRODUCT_WIDTH + 5
		report
			"G_ACCUMULATOR_WIDTH requires at least "
			& "five guard bits for 31 taps"
		severity failure;


	process (clk)
		variable history_work : t_sample_array(
			0 to C_FIR_TAPS - 1
		);

		variable product : signed(
			G_PRODUCT_WIDTH - 1 downto 0
		);

		variable accumulator : signed(
			G_ACCUMULATOR_WIDTH - 1 downto 0
		);

		variable accumulator_extended : signed(
			G_ACCUMULATOR_WIDTH downto 0
		);

		variable rounded_extended : signed(
			G_ACCUMULATOR_WIDTH downto 0
		);
	begin
		if rising_edge(clk) then
			out_valid <= '0';

			if rst = '1' then
				for tap_index in 0 to C_FIR_TAPS - 1 loop
					sample_history(tap_index) <= (
						others => '0'
					);
				end loop;

				out_valid <= '0';

				out_sample <= (
					others => '0'
				);

			elsif in_valid = '1' then
				history_work := sample_history;

				for tap_index in
					C_FIR_TAPS - 1 downto 1
				loop
					history_work(tap_index) :=
						history_work(
							tap_index - 1
						);
				end loop;

				history_work(0) := in_sample;

				sample_history <= history_work;

				accumulator := (
					others => '0'
				);

				for tap_index in 0 to C_FIR_TAPS - 1 loop
					product := resize(
						history_work(tap_index)
						* C_FIR_COEFFICIENTS_Q17(
							tap_index
						),
						G_PRODUCT_WIDTH
					);

					accumulator :=
						accumulator
						+ resize(
							product,
							G_ACCUMULATOR_WIDTH
						);
				end loop;

				accumulator_extended := resize(
					accumulator,
					G_ACCUMULATOR_WIDTH + 1
				);

				if accumulator_extended(
					accumulator_extended'high
				) = '0' then
					rounded_extended := shift_right(
						accumulator_extended
						+ C_ROUNDING_OFFSET_EXTENDED,
						G_FRACTIONAL_BITS
					);

				else
					rounded_extended :=
						-shift_right(
							(-accumulator_extended)
							+ C_ROUNDING_OFFSET_EXTENDED,
							G_FRACTIONAL_BITS
						);
				end if;

				if rounded_extended > resize(
					C_OUTPUT_MAXIMUM,
					rounded_extended'length
				) then
					out_sample <=
						C_OUTPUT_MAXIMUM;

				elsif rounded_extended < resize(
					C_OUTPUT_MINIMUM,
					rounded_extended'length
				) then
					out_sample <=
						C_OUTPUT_MINIMUM;

				else
					out_sample <= resize(
						rounded_extended,
						G_OUTPUT_WIDTH
					);
				end if;

				out_valid <= '1';
			end if;
		end if;
	end process;

end architecture rtl;
