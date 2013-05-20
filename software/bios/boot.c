#include <stdio.h>
#include <console.h>
#include <uart.h>
#include <system.h>
#include <crc.h>
#include <sfl.h>
#include <string.h>
#include <irq.h>

#include <hw/mem.h>
#include <hw/csr.h>

#include "boot.h"

extern void boot_helper(unsigned int r1, unsigned int r2, unsigned int r3, unsigned int addr);

static void __attribute__((noreturn)) boot(unsigned int r1, unsigned int r2, unsigned int r3, unsigned int addr)
{
	printf("Executing booted program.\n");
	uart_sync();
	irq_setmask(0);
	irq_setie(0);
	boot_helper(r1, r2, r3, addr);
	while(1);
}

static int check_ack(void)
{
	int recognized;
	static const char str[SFL_MAGIC_LEN] = SFL_MAGIC_ACK;

	timer0_en_write(0);
	timer0_reload_write(0);
	timer0_load_write(identifier_frequency_read()/4);
	timer0_en_write(1);
	timer0_update_value_write(1);
	recognized = 0;
	while(timer0_value_read()) {
		if(uart_read_nonblock()) {
			char c;
			c = uart_read();
			if(c == str[recognized]) {
				recognized++;
				if(recognized == SFL_MAGIC_LEN)
					return 1;
			} else {
				if(c == str[0])
					recognized = 1;
				else
					recognized = 0;
			}
		}
		timer0_update_value_write(1);
	}
	return 0;
}

#define MAX_FAILED 5

void serialboot(void)
{
	struct sfl_frame frame;
	int failed;
	unsigned int cmdline_adr, initrdstart_adr, initrdend_adr;
	static const char str[SFL_MAGIC_LEN+1] = SFL_MAGIC_REQ;
	const char *c;

	printf("Booting from serial...\n");

	c = str;
	while(*c) {
		uart_write(*c);
		c++;
	}
	if(!check_ack()) {
		printf("Timeout\n");
		return;
	}

	failed = 0;
	cmdline_adr = initrdstart_adr = initrdend_adr = 0;
	while(1) {
		int i;
		int actualcrc;
		int goodcrc;

		/* Grab one frame */
		frame.length = uart_read();
		frame.crc[0] = uart_read();
		frame.crc[1] = uart_read();
		frame.cmd = uart_read();
		for(i=0;i<frame.length;i++)
			frame.payload[i] = uart_read();

		/* Check CRC */
		actualcrc = ((int)frame.crc[0] << 8)|(int)frame.crc[1];
		goodcrc = crc16(&frame.cmd, frame.length+1);
		if(actualcrc != goodcrc) {
			failed++;
			if(failed == MAX_FAILED) {
				printf("Too many consecutive errors, aborting");
				return;
			}
			uart_write(SFL_ACK_CRCERROR);
			continue;
		}

		/* CRC OK */
		switch(frame.cmd) {
			case SFL_CMD_ABORT:
				failed = 0;
				uart_write(SFL_ACK_SUCCESS);
				return;
			case SFL_CMD_LOAD: {
				char *writepointer;

				failed = 0;
				writepointer = (char *)(
					 ((unsigned int)frame.payload[0] << 24)
					|((unsigned int)frame.payload[1] << 16)
					|((unsigned int)frame.payload[2] << 8)
					|((unsigned int)frame.payload[3] << 0));
				for(i=4;i<frame.length;i++)
					*(writepointer++) = frame.payload[i];
				uart_write(SFL_ACK_SUCCESS);
				break;
			}
			case SFL_CMD_JUMP: {
				unsigned int addr;

				failed = 0;
				addr =  ((unsigned int)frame.payload[0] << 24)
					|((unsigned int)frame.payload[1] << 16)
					|((unsigned int)frame.payload[2] << 8)
					|((unsigned int)frame.payload[3] << 0);
				uart_write(SFL_ACK_SUCCESS);
				boot(cmdline_adr, initrdstart_adr, initrdend_adr, addr);
				break;
			}
			case SFL_CMD_CMDLINE:
				failed = 0;
				cmdline_adr =  ((unsigned int)frame.payload[0] << 24)
					      |((unsigned int)frame.payload[1] << 16)
					      |((unsigned int)frame.payload[2] << 8)
					      |((unsigned int)frame.payload[3] << 0);
				uart_write(SFL_ACK_SUCCESS);
				break;
			case SFL_CMD_INITRDSTART:
				failed = 0;
				initrdstart_adr =  ((unsigned int)frame.payload[0] << 24)
					          |((unsigned int)frame.payload[1] << 16)
					          |((unsigned int)frame.payload[2] << 8)
					          |((unsigned int)frame.payload[3] << 0);
				uart_write(SFL_ACK_SUCCESS);
				break;
			case SFL_CMD_INITRDEND:
				failed = 0;
				initrdend_adr =  ((unsigned int)frame.payload[0] << 24)
					        |((unsigned int)frame.payload[1] << 16)
					        |((unsigned int)frame.payload[2] << 8)
					        |((unsigned int)frame.payload[3] << 0);
				uart_write(SFL_ACK_SUCCESS);
				break;
			default:
				failed++;
				if(failed == MAX_FAILED) {
					printf("Too many consecutive errors, aborting");
					return;
				}
				uart_write(SFL_ACK_UNKNOWN);
				break;
		}
	}
}
