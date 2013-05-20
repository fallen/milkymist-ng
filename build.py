#!/usr/bin/env python3

import os, struct

from mibuild.platforms import nexys3
from mibuild.tools import write_to_file

import top
import cif

def main():
	bios_file = open("software/bios/bios.bin", "rb")
	bios_data = []
	while True:
		w = bios_file.read(4)
		if not w:
			break
		bios_data.append(struct.unpack(">I", w)[0])
	bios_file.close()

	platform = nexys3.Platform()
	soc = top.SoC(bios_data, platform)

	platform.add_platform_command("""
NET "{clk100}" TNM_NET = "GRPclk100";
TIMESPEC "TSclk100" = PERIOD "GRPclk100" 10 ns HIGH 50%;
""", clk100=platform.lookup_request("clk100"))

	platform.add_sources(os.path.join("verilog", "lm32", "submodule", "rtl"), 
		"lm32_cpu.v", "lm32_instruction_unit.v", "lm32_decoder.v",
		"lm32_load_store_unit.v", "lm32_adder.v", "lm32_addsub.v", "lm32_logic_op.v",
		"lm32_shifter.v", "lm32_multiplier.v", "lm32_mc_arithmetic.v",
		"lm32_interrupt.v", "lm32_ram.v", "lm32_dp_ram.v", "lm32_icache.v",
		"lm32_dcache.v", "lm32_top.v", "lm32_debug.v", "lm32_jtag.v", "jtag_cores.v",
		"jtag_tap_spartan6.v", "lm32_itlb.v", "lm32_dtlb.v")
	platform.add_sources(os.path.join("verilog", "lm32"), "lm32_config.v")

	platform.build_cmdline(soc)
	csr_header = cif.get_csr_header(soc.csr_base, soc.csrbankarray, soc.interrupt_map)
	write_to_file("software/include/hw/csr.h", csr_header)

if __name__ == "__main__":
	main()
