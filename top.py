from operator import itemgetter
from migen.fhdl.specials import Instance
from migen.fhdl.structure import *
from migen.fhdl.module import Module
from migen.bus import wishbone, csr, wishbone2csr
from migen.bank import csrgen
from milkymist import lm32, uart, identifier, timer

#version = get_macros("common/version.h")["VERSION"][1:-1]
version = "2.0"

clk_freq = 100*1000000
sram_size = 4096 # in bytes , 4 kB
rom_size = 16384*2 # in bytes , 32 kB

class CRG(Module):
	def __init__(self, clock_pad):
		self.clock_domains.cd_sys = ClockDomain()
		self.comb += self.cd_sys.clk.eq(clock_pad)
		self.specials += Instance("SRL16E",
				Instance.Parameter("INIT", 0xffff),
				Instance.Input("CLK", ClockSignal()),
				Instance.Input("CE", 1),
				Instance.Input("D", 0),
				Instance.Input("A0", 1),
				Instance.Input("A1", 1),
				Instance.Input("A2", 1),
				Instance.Input("A3", 1),
				Instance.Output("Q", self.cd_sys.rst)
			)

class SoC(Module):
	csr_base = 0xe0000000
	csr_map = {
		"uart":					1,
		"identifier":			3,
		"timer0":				4,
	}

	interrupt_map = {
		"uart":			0,
		"timer0":		1
	}

	def __init__(self, rom_data, platform):
		# Clock and reset generator
		self.submodules.crg = CRG(platform.request("clk100"))

		#
		# WISHBONE
		#
		self.submodules.cpu = lm32.LM32()
		self.submodules.rom = wishbone.SRAM(rom_size, read_only=True, init=rom_data)
		self.submodules.sram = wishbone.SRAM(sram_size)
		self.submodules.wishbone2csr = wishbone2csr.WB2CSR()		

		# ROM          0x00000000 (shadow @0x80000000)
		# SRAM/debug   0x10000000 (shadow @0x90000000)
		# CSR bridge   0x60000000 (shadow @0xe0000000)
		self.submodules.wishbonecon = wishbone.InterconnectShared(
			[
				self.cpu.ibus,
				self.cpu.dbus
			], [
				(lambda a: a[26:29] == 0, self.rom.bus),
				(lambda a: a[26:29] == 1, self.sram.bus),
				(lambda a: a[27:29] == 3, self.wishbone2csr.wishbone)
			],
			register=True)

		#
		# CSR
		#
		self.submodules.uart = uart.UART(platform.request("serial"), clk_freq, baud=115200)
		self.submodules.identifier = identifier.Identifier(0x5041, version, int(clk_freq))
		self.submodules.timer0 = timer.Timer()

		self.submodules.csrbankarray = csrgen.BankArray(self,
			lambda name, memory: self.csr_map[name if memory is None else name + "_" + memory.name_override])
		self.submodules.csrcon = csr.Interconnect(self.wishbone2csr.csr, self.csrbankarray.get_buses())

		#
		# Interrupts
		#
		for k, v in sorted(self.interrupt_map.items(), key=itemgetter(1)):
			if hasattr(self, k):
				self.comb += self.cpu.interrupt[v].eq(getattr(self, k).ev.irq)
