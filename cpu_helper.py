def imm(val):
	"""Load immediate value"""
	return val

def zp(addr, mem):
	"""Return value at zero page address"""
	return mem.read(addr % 0x100)

def zpx(addr, mem, x):
	"""Return value at zero page address offset by x"""
	return mem.read((addr + x) % 0x100)

def abs(addr, mem):
	"""Return value at address"""
	return mem.read(addr)

def absxy(addr, mem, x):
	"""Return value at address and whether we page crossed"""
	pc = False
	if (addr & 0xFF) + x > 0xFF:
		pc = True
		
	return (mem.read(addr + x), pc)

def indx(addr, mem, x):
	"""Return indexed indirect value at offset x from addr"""
	# Indexed indirect x
	# https://www.c64-wiki.com/wiki/Indexed-indirect_addressing
	addr += x
	
	lower = mem.read(addr % 0x100)
	upper = mem.read((addr + 1) % 0x100)
			
	addr = (upper << 8) + lower
	
	return mem.read(addr)

def indy(addr, mem, y):
	"""Return indirect indexed value for y from addr, and whether we page crossed"""
	# Indirect indexed y
	# https://www.c64-wiki.com/wiki/Indirect-indexed_addressing
	lower = mem.read(addr % 0x100)
	upper = mem.read((addr + 1) % 0x100)
	
	addr = (upper << 8) + lower
	addr += y
	
	pc = False
	if lower + y > 0xFF:
		pc = True
		
	return (mem.read(addr), pc)

