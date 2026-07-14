library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;


entity cic_decimator is
	generic (
		G_R              : positive := 8;
		G_N              : positive := 3;
		G_M              : positive := 1;
		G_INPUT_WIDTH    : positive := 12;
		G_INTERNAL_WIDTH : positive := 21;
		G_OUTPUT_WIDTH   : positive := 21
	);
	port (
		clk        : in  std_logic;
		rst        : in  std_logic;

		in_valid   : in  std_logic;
		in_sample  : in  signed(G_INPUT_WIDTH - 1 downto 0);

		out_valid  : out std_logic;
		out_sample : out signed(G_OUTPUT_WIDTH - 1 downto 0)
	);
end entity cic_decimator;


architecture rtl of cic_decimator is

	type t_stage_array is array (
		natural range <>
	) of signed(G_INTERNAL_WIDTH - 1 downto 0);

	type t_comb_delay_array is array (
		natural range <>,
		natural range <>
	) of signed(G_INTERNAL_WIDTH - 1 downto 0);

	signal integrators : t_stage_array(
		0 to G_N - 1
	);

	signal comb_delays : t_comb_delay_array(
		0 to G_N - 1,
		0 to G_M - 1
	);

	signal decimation_counter : natural range 0 to G_R - 1 := 0;

begin

	assert G_OUTPUT_WIDTH = G_INTERNAL_WIDTH
		report
			"G_OUTPUT_WIDTH must equal G_INTERNAL_WIDTH "
			& "for CIC v0.1"
		severity failure;


	process (clk)
		variable integrator_work : t_stage_array(
			0 to G_N - 1
		);

		variable stage_input : signed(
			G_INTERNAL_WIDTH - 1 downto 0
		);

		variable comb_input : signed(
			G_INTERNAL_WIDTH - 1 downto 0
		);

		variable delayed_value : signed(
			G_INTERNAL_WIDTH - 1 downto 0
		);

		variable comb_output : signed(
			G_INTERNAL_WIDTH - 1 downto 0
		);
	begin
		if rising_edge(clk) then
			out_valid <= '0';

			if rst = '1' then
				for stage_index in 0 to G_N - 1 loop
					integrators(stage_index) <= (
						others => '0'
					);

					for delay_index in 0 to G_M - 1 loop
						comb_delays(
							stage_index,
							delay_index
						) <= (
							others => '0'
						);
					end loop;
				end loop;

				decimation_counter <= 0;

				out_valid <= '0';
				out_sample <= (
					others => '0'
				);

			elsif in_valid = '1' then
				integrator_work := integrators;

				stage_input := resize(
					in_sample,
					G_INTERNAL_WIDTH
				);

				for stage_index in 0 to G_N - 1 loop
					integrator_work(stage_index) :=
						integrator_work(stage_index)
						+ stage_input;

					stage_input :=
						integrator_work(stage_index);
				end loop;

				integrators <= integrator_work;

				if decimation_counter = G_R - 1 then
					decimation_counter <= 0;

					comb_input := stage_input;

					for stage_index in 0 to G_N - 1 loop
						delayed_value := comb_delays(
							stage_index,
							0
						);

						for delay_index in 0 to G_M - 2 loop
							comb_delays(
								stage_index,
								delay_index
							) <= comb_delays(
								stage_index,
								delay_index + 1
							);
						end loop;

						comb_delays(
							stage_index,
							G_M - 1
						) <= comb_input;

						comb_output :=
							comb_input
							- delayed_value;

						comb_input := comb_output;
					end loop;

					out_sample <= resize(
						comb_input,
						G_OUTPUT_WIDTH
					);

					out_valid <= '1';

				else
					decimation_counter <=
						decimation_counter + 1;
				end if;
			end if;
		end if;
	end process;

end architecture rtl;