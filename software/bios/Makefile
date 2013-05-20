M2DIR=../..
include $(M2DIR)/software/common.mak

OBJECTS=crt0.o isr.o main.o boot-helper.o boot.o

all: bios.bin

# pull in dependency info for *existing* .o files
-include $(OBJECTS:.o=.d)

%.bin: %.elf
	$(OBJCOPY) -O binary $< $@
	chmod -x $@

bios.elf: linker.ld $(OBJECTS) libs

%.elf:
	$(LD) $(LDFLAGS) -T $< -N -o $@ $(OBJECTS) \
		-L$(M2DIR)/software/libbase \
		-L$(M2DIR)/software/libcompiler-rt \
		-lbase -lcompiler-rt
	chmod -x $@

main.o: main.c
	$(compile-dep)

%.o: %.c
	$(compile-dep)

%.o: %.S
	$(assemble)

libs:
	$(MAKE) -C $(M2DIR)/software/libcompiler-rt
	$(MAKE) -C $(M2DIR)/software/libbase

clean:
	$(RM) $(OBJECTS) $(OBJECTS:.o=.d) bios.elf bios.bin .*~ *~

.PHONY: all main.o clean libs
