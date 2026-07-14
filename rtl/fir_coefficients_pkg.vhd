library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;


package fir_coefficients_pkg is

	constant C_FIR_TAPS : positive := 31;

	constant C_FIR_COEFFICIENT_WIDTH : positive := 18;
	constant C_FIR_FRACTIONAL_BITS   : positive := 17;

	subtype t_fir_coefficient is signed(
		C_FIR_COEFFICIENT_WIDTH - 1 downto 0
	);

	type t_fir_coefficient_array is array (
		natural range <>
	) of t_fir_coefficient;

	constant C_FIR_COEFFICIENTS_Q17 :
		t_fir_coefficient_array(
			0 to C_FIR_TAPS - 1
		) := (
			to_signed(   0, C_FIR_COEFFICIENT_WIDTH),
			to_signed(   0, C_FIR_COEFFICIENT_WIDTH),
			to_signed(   0, C_FIR_COEFFICIENT_WIDTH),
			to_signed(  -1, C_FIR_COEFFICIENT_WIDTH),
			to_signed(   0, C_FIR_COEFFICIENT_WIDTH),
			to_signed(   3, C_FIR_COEFFICIENT_WIDTH),
			to_signed(   2, C_FIR_COEFFICIENT_WIDTH),
			to_signed(  -5, C_FIR_COEFFICIENT_WIDTH),
			to_signed(  -5, C_FIR_COEFFICIENT_WIDTH),
			to_signed(   8, C_FIR_COEFFICIENT_WIDTH),
			to_signed(  12, C_FIR_COEFFICIENT_WIDTH),
			to_signed( -10, C_FIR_COEFFICIENT_WIDTH),
			to_signed( -29, C_FIR_COEFFICIENT_WIDTH),
			to_signed(   6, C_FIR_COEFFICIENT_WIDTH),
			to_signed(  84, C_FIR_COEFFICIENT_WIDTH),
			to_signed( 127, C_FIR_COEFFICIENT_WIDTH),
			to_signed(  84, C_FIR_COEFFICIENT_WIDTH),
			to_signed(   6, C_FIR_COEFFICIENT_WIDTH),
			to_signed( -29, C_FIR_COEFFICIENT_WIDTH),
			to_signed( -10, C_FIR_COEFFICIENT_WIDTH),
			to_signed(  12, C_FIR_COEFFICIENT_WIDTH),
			to_signed(   8, C_FIR_COEFFICIENT_WIDTH),
			to_signed(  -5, C_FIR_COEFFICIENT_WIDTH),
			to_signed(  -5, C_FIR_COEFFICIENT_WIDTH),
			to_signed(   2, C_FIR_COEFFICIENT_WIDTH),
			to_signed(   3, C_FIR_COEFFICIENT_WIDTH),
			to_signed(   0, C_FIR_COEFFICIENT_WIDTH),
			to_signed(  -1, C_FIR_COEFFICIENT_WIDTH),
			to_signed(   0, C_FIR_COEFFICIENT_WIDTH),
			to_signed(   0, C_FIR_COEFFICIENT_WIDTH),
			to_signed(   0, C_FIR_COEFFICIENT_WIDTH)
		);

end package fir_coefficients_pkg;


package body fir_coefficients_pkg is
end package body fir_coefficients_pkg;
