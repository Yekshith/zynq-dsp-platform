library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;


entity cic_fir_pipeline is
	generic (
		G_CIC_R              : positive := 8;
		G_CIC_N              : positive := 3;
		G_CIC_M              : positive := 1;
		G_INPUT_WIDTH        : positive := 12;
		G_CIC_INTERNAL_WIDTH : positive := 21;
		G_PRODUCT_WIDTH      : positive := 39;
		G_ACCUMULATOR_WIDTH  : positive := 44;
		G_FRACTIONAL_BITS    : positive := 17;
		G_OUTPUT_WIDTH       : positive := 16
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
end entity cic_fir_pipeline;


architecture rtl of cic_fir_pipeline is

	signal cic_out_valid : std_logic;

	signal cic_out_sample : signed(
		G_CIC_INTERNAL_WIDTH - 1 downto 0
	);

begin

	u_cic_decimator : entity work.cic_decimator
		generic map (
			G_R              => G_CIC_R,
			G_N              => G_CIC_N,
			G_M              => G_CIC_M,
			G_INPUT_WIDTH    => G_INPUT_WIDTH,
			G_INTERNAL_WIDTH => G_CIC_INTERNAL_WIDTH,
			G_OUTPUT_WIDTH   => G_CIC_INTERNAL_WIDTH
		)
		port map (
			clk        => clk,
			rst        => rst,

			in_valid   => in_valid,
			in_sample  => in_sample,

			out_valid  => cic_out_valid,
			out_sample => cic_out_sample
		);


	u_fir_comp : entity work.fir_comp
		generic map (
			G_INPUT_WIDTH       => G_CIC_INTERNAL_WIDTH,
			G_PRODUCT_WIDTH     => G_PRODUCT_WIDTH,
			G_ACCUMULATOR_WIDTH => G_ACCUMULATOR_WIDTH,
			G_FRACTIONAL_BITS   => G_FRACTIONAL_BITS,
			G_OUTPUT_WIDTH      => G_OUTPUT_WIDTH
		)
		port map (
			clk        => clk,
			rst        => rst,

			in_valid   => cic_out_valid,
			in_sample  => cic_out_sample,

			out_valid  => out_valid,
			out_sample => out_sample
		);

end architecture rtl;
