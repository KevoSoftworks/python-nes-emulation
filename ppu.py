"""
CPU-PPU interface:
	The 6502 interfaces with the PPU using 8 registers at 0x2000 to 0x2007
	in the CPU address range (and being mirrored). Furthermore, there is
	a register (0x4014) which allows DMA writes into the PPU OAM.
	
	0x2000: PPUCTRL: Various flags (w)
	0x2001: PPUMASK: Rendering masks (w)
	0x2002: PPUSTATUS: Various PPU status information (r)
	0x2003: OAMADDR: addr of OAM to access (w)
	0x2004: OAMDATA: data to write or data at addr to read (rw)
	0x2005: PPUSCROLL: set coordinate of pixel to be rendered at (0,0) (w 2x)
	0x2006: PPUADDR: set 16-bit addr in PPU to manipulate (w 2x, high byte first)
	0x2007: PPUDATA: data to write or data at addr to read (rw)
	0x4014: OAMDMA: Write 256 bytes of CPU memory to PPU OAM (w).
				Takes the high byte of CPU mem as input, writes 0xXX00 - 0xXXFF
	
For now, we assume NTSC timing due to the documentation on nesdev.
The PPU renders 262 scanlines per frame, with each scanline taking 341 PPU cycles.
Every PPU clock cycle produces a pixel. 20 VBlank scanlines are rendered in NTSC.
"""

REGISTERS = (0x2000, 0x2001, 0x2002, 0x2003, 0x2004, 0x2005, 0x2006, 0x2007, 0x4014)
SCANLINES_PER_FRAME = 262
CYCLES_PER_SCANLINE = 341
CYCLES_PER_FRAME = CYCLES_PER_SCANLINE * SCANLINES_PER_FRAME
CYCLE_POSTRENDER = 240 * CYCLES_PER_SCANLINE
CYCLE_VBLANK = 241 * CYCLES_PER_SCANLINE

class Memory:
	pass

class PPU:	
	control = 0x00 	# Status register PPUCTRL
	mask = 0x00 		# Mask register PPUMASK
	status = 0x00 	# Status register PPUSTATUS
	
	cycles = 0
	
	def __init__(self):
		self.mem = Memory()
	
	def handle_read(self, addr):
		if addr == 0x2002:
			return self.status
	
	def handle_write(self, addr, data):
		if addr == 0x2000:
			self.control = data
		elif addr == 0x2001:
			self.mask = data
			
	def run(self, cpu):
		if self.cycles % CYCLES_PER_FRAME > CYCLE_POSTRENDER:
			# Post render and VBlank
			self.status |= 0x80
			
			if self.cycles % CYCLES_PER_FRAME == CYCLE_VBLANK and self.control & 0x80:
				cpu.handle_nmi()
		else:
			self.status &= ~0x80
		
		self.cycles += 1