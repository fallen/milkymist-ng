all: build/top.bit build/top.fpg

build/top.bit build/top.bin:
	./build.py

build/top.fpg: build/top.bin
	make -C tools
	tools/byteswap $< $@

load: build/top.bit
	djtgcfg prog -d Nexys3 -i 0 -f $<

clean:
	rm -rf build/*

.PHONY: load clean all
