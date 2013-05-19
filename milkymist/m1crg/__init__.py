from fractions import Fraction

from migen.fhdl.structure import *
from migen.fhdl.specials import Instance
from migen.fhdl.module import Module
from migen.bank.description import *

class M1CRG(Module, AutoCSR):
	def __init__(self, pads, outfreq1x):
		self.clock_domains.cd_sys = ClockDomain()
		self.clock_domains.cd_sys2x_270 = ClockDomain()
		self.clock_domains.cd_sys4x_wr = ClockDomain()
		self.clock_domains.cd_sys4x_rd = ClockDomain()
		self.clock_domains.cd_eth_rx = ClockDomain()
		self.clock_domains.cd_eth_tx = ClockDomain()
		self.clock_domains.cd_vga = ClockDomain(reset_less=True)

		self.clk4x_wr_strb = Signal()
		self.clk4x_rd_strb = Signal()

		self._r_cmd_data = CSRStorage(10)
		self._r_send_cmd_data = CSR()
		self._r_send_go = CSR()
		self._r_status = CSRStatus(3)

		###
		
		infreq = 100*1000000
		ratio = Fraction(outfreq1x)/Fraction(infreq)
		in_period = float(Fraction(1000000000)/Fraction(infreq))

		vga_progdata = Signal()
		vga_progen = Signal()
		vga_progdone = Signal()
		vga_locked = Signal()

		self.specials += Instance("m1crg",
			Instance.Parameter("in_period", in_period),
			Instance.Parameter("f_mult", ratio.numerator),
			Instance.Parameter("f_div", ratio.denominator),
			Instance.Input("clk100_pad", pads.clk100),
			Instance.Input("trigger_reset", pads.trigger_reset),
			Instance.Output("sys_clk", self.cd_sys.clk),
			Instance.Output("sys_rst", self.cd_sys.rst))
#			Instance.Output("flash_rst", pads.flash_rst))

		remaining_bits = Signal(max=11)
		transmitting = Signal()
		self.comb += transmitting.eq(remaining_bits != 0)
		sr = Signal(10)
		self.sync += [
			If(self._r_send_cmd_data.re,
				remaining_bits.eq(10),
				sr.eq(self._r_cmd_data.storage)
			).Elif(transmitting,
				remaining_bits.eq(remaining_bits - 1),
				sr.eq(sr[1:])
			)
		]
		self.comb += [
			vga_progdata.eq(transmitting & sr[0]),
			vga_progen.eq(transmitting | self._r_send_go.re)
		]

		# enforce gap between commands
		busy_counter = Signal(max=14)
		busy = Signal()
		self.comb += busy.eq(busy_counter != 0)
		self.sync += If(self._r_send_cmd_data.re,
				busy_counter.eq(13)
			).Elif(busy,
				busy_counter.eq(busy_counter - 1)
			)

		self.comb += self._r_status.status.eq(Cat(busy, vga_progdone, vga_locked))
