from fractions import Fraction
from math import ceil
from operator import itemgetter

from migen.fhdl.structure import *
from migen.fhdl.module import Module
from migen.bus import wishbone, csr, wishbone2csr
from migen.bank import csrgen

from milkymist import m1crg, lm32, uart, flash
from cif import get_macros

version = get_macros("common/version.h")["VERSION"][1:-1]

clk_freq = (83 + Fraction(1, 3))*1000000
sram_size = 4096 # in bytes
l2_size = 8192 # in bytes

clk_period_ns = 1000000000/clk_freq
def ns(t, margin=True):
	if margin:
		t += clk_period_ns/2
	return ceil(t/clk_period_ns)

class Nexys3ClockPads:
	def __init__(self, platform):
		self.clk100 = platform.request("clk100", 0)
		self.trigger_reset = platform.request("user_btn", 1)
		self.flash_rst_n = platform.request("flash_rst_n")

class SoC(Module):
	csr_base = 0xe0000000
	csr_map = {
		"crg":					0,
		"uart":					1,
	}

	interrupt_map = {}

	def __init__(self, platform):
		#
		# WISHBONE
		#
		self.submodules.cpu = lm32.LM32()
		self.submodules.flash = flash.Flash(platform.request("flash"), 24)
		self.submodules.sram = wishbone.SRAM(sram_size)
		self.submodules.wishbone2csr = wishbone2csr.WB2CSR()
		
		# flash        0x00000000 (shadow @0x80000000)
		# SRAM/debug   0x10000000 (shadow @0x90000000)
		# USB          0x20000000 (shadow @0xa0000000)
		# Ethernet     0x30000000 (shadow @0xb0000000)
		# SDRAM        0x40000000 (shadow @0xc0000000)
		# CSR bridge   0x60000000 (shadow @0xe0000000)
		self.submodules.wishbonecon = wishbone.InterconnectShared(
			[
				self.cpu.ibus,
				self.cpu.dbus
			], [
				(lambda a: a[26:29] == 0, self.flash.bus),
				(lambda a: a[26:29] == 1, self.sram.bus),
				(lambda a: a[27:29] == 3, self.wishbone2csr.wishbone)
			],
			register=True)
		
		#
		# CSR
		#
		self.submodules.crg = m1crg.M1CRG(Nexys3ClockPads(platform), clk_freq)
		self.submodules.uart = uart.UART(platform.request("serial"), clk_freq, baud=115200)

		self.submodules.csrbankarray = csrgen.BankArray(self,
			lambda name, memory: self.csr_map[name if memory is None else name + "_" + memory.name_override])
		self.submodules.csrcon = csr.Interconnect(self.wishbone2csr.csr, self.csrbankarray.get_buses())

		#
		# Interrupts
		#
		#for k, v in sorted(self.interrupt_map.items(), key=itemgetter(1)):
		#	if hasattr(self, k):
		#		self.comb += self.cpu.interrupt[v].eq(getattr(self, k).ev.irq)
