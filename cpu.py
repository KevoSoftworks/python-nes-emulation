from opcodes6502 import opcodes
from byte_math import signed_byte_to_int
from cpu_helper import imm, zp, zpx, abs, absxy, indx, indy
import ppu as graphics

class Memory:
	"""
	!! The CPU is little-endian !! (byte 0x1234 will be represented in memory
	as 0x34 0x12)
	
	NES CPU map:
		0x0000 - 0x07FF: 2KiB internal RAM
		0x0800 - 0x1FFF: 3x mirror of 0x0000 - 0x07FF
		0x2000 - 0x2007: NES PPU Registers
		0x2008 - 0x3FFF: Mirrors of 0x2000 - 0x2007
		0x4000 - 0x4017: APU and I/O registers
		0x4018 - 0x401F: Disabled APU and I/O functionality
		0x4020 - 0xFFFF: ROM, RAM and mapper registers
			For map 0:
				0x6000 - 0x7FFF: PRG RAM (mirrored as required)
				0x8000 - 0xBFFF: First 16KiB of ROM
				0xC000 - 0xFFFF: Last 16KiB of ROM or Mirror of first 16KiB
		
		0xFFFA - 0xFFFB: NMI vector
		0xFFFC - 0xFFFD: Reset vector
		0xFFFE - 0xFFFF: IRQ vector
	"""
	
	mem = bytearray(0xFFFF+1)
	is_mirror = False
	ppu = None
	
	def __init__(self, mem, is_mirror = False):
		if len(mem) != len(self.mem):
			raise Exception(f"Memory::__init__: Invalid memory length, expecting {len(self.mem)}, got {len(mem)}")
			
		self.mem = mem
		self.is_mirror = is_mirror
	
	def _set_ppu(self, ppu):
		self.ppu = ppu
		
	def page_num(self, addr):
		return addr // 0xFF
		
	def map_byte(self, byte):
		# 0x0000 - 0x1FFF (4 mirrors)
		if byte >= 0 and byte <= 0x1FFF:
			return byte % 0x0800
		
		# 0x2000 - 0x3FFF (8 byte mirrors)
		if byte >= 0x2000 and byte <= 0x3FFF:
			return ((byte - 0x2000) % 0x08) + 0x2000
		
		# 0x8000 - 0xFFFF (mirror if required)
		if self.is_mirror and byte >= 0xC000 and byte <= 0xFFFF:
			return byte - 0x4000
		
		# No further mapping required
		return byte
		
	def read(self, byte):
		mapped = self.map_byte(byte)
		
		if mapped in graphics.REGISTERS:
			#print(f"Mem read at byte {byte:04X} in PPU")
			return self.ppu.handle_read(byte)
		
		return self.mem[mapped]
	
	def write(self, byte, data):
		if byte >= 0x8000:
			print(f"Memory::write: Trying to write {data} at 0x{byte:04X} in Read-Only Memory")
			return
		
		mapped = self.map_byte(byte)
		
		if mapped in graphics.REGISTERS:
			#print(f"Mem write at byte {byte:04X} in PPU")
			return self.ppu.handle_write(byte, data)
		
		self.mem[mapped] = data % 0x100
		
class Flag:
	N = 128	# Negative
	V = 64	# Overflow
	_ = 32	# unused
	B = 16	# 
	D = 8	# Decimal mode
	I = 4	# Interrupt disable
	Z = 2	# Zero
	C = 1	# Carry
	
	INIT_FLAGS = [_, I]
	VALUES = [N, V, _, B, D, I, Z, C]
	
	# See: https://stackoverflow.com/questions/16913423/why-is-the-initial-state-of-the-interrupt-flag-of-the-6502-a-1
	enabled_flags = INIT_FLAGS[:]
	
	@staticmethod
	def byte_to_str(byte):
		flags = ["N", "V", "_", "B", "D", "I", "Z", "C"]
		values = Flag.VALUES
		
		set_flags = [flags[index] for index, value in enumerate(values) if byte & value]
		
		return " ".join(set_flags)
	
	def __str__(self):
		return f"Flags: (0x{self.get_byte():02X}) [{Flag.byte_to_str(self.get_byte())}]"
	
	def get_byte(self):
		return sum(self.enabled_flags)
	
	def set_byte(self, byte):
		self.enabled_flags = Flag.INIT_FLAGS[:]
		
		if byte & Flag.N:
			self.set(Flag.N)
		
		if byte & Flag.V:
			self.set(Flag.V)
		
		if byte & Flag._:
			self.set(Flag._)
		
		if byte & Flag.B:
			self.set(Flag.B)
		
		if byte & Flag.D:
			self.set(Flag.D)
		
		if byte & Flag.I:
			self.set(Flag.I)
		
		if byte & Flag.Z:
			self.set(Flag.Z)
			
		if byte & Flag.C:
			self.set(Flag.C)
	
	def isset(self, flag):
		return flag in self.enabled_flags
	
	def set(self, flag):
		if not self.isset(flag):
			self.enabled_flags.append(flag)
			return True
		
		return False
	
	def clear(self, flag):
		if self.isset(flag):
			self.enabled_flags.remove(flag)
			return True
		
		return False
	
	def toggle(self, flag):
		if self.isset(flag):
			return self.clear(flag)
		
		return self.set(flag)

class CPU:
	# Useful: http://www.emulator101.com/6502-addressing-modes.html
	# http://www.obelisk.me.uk/6502/reference.html
	sp = 0xFD						# Stack pointer (8-bit)
	pc = 0							# Program counter (16-bit)
	pf = 0b00100000					# Processor flags NV-BDIZC (8-bit)
	acc = 0							# Accumulator (8-bit)
	x = 0							# X register (8-bit)
	y = 0							# Y register (8-bit)
	cycles = 0
	
	def __init__(self, mem):
		self.mem = mem
		self.flag = Flag()
		self.pc = self.reset_vector()
		self.ppu = graphics.PPU()
		
		self.mem._set_ppu(self.ppu)
	
	def _format_instr(self, byte):
		instr = self.get_instruction_at(byte)
		return f"Instruction {instr[0]} (0x{byte:02X}) at 0x{self.pc:04X}"
		
	def reset_vector(self):
		return self.mem.read(0xFFFC) + (self.mem.read(0xFFFD) << 8)
	
	def irq_vector(self):
		return self.mem.read(0xFFFE) + (self.mem.read(0xFFFF) << 8)
	
	def nmi_vector(self):
		return self.mem.read(0xFFFA) + (self.mem.read(0xFFFB) << 8)
	
	def get_current_pc_byte(self):
		return self.mem.read(self.pc)
	
	def get_current_instruction(self):
		return self.get_instruction_at(self.pc)
		
	def get_instruction_at(self, loc):
		cur_byte = self.get_current_pc_byte()
		if cur_byte not in opcodes:
			raise Exception(f"CPU::get_instruction_at: {self._format_instr(cur_byte)} is not a valid opcode")
			print(f"CPU::get_instruction_at: {self._format_instr(cur_byte)} is not a valid opcode")
			return opcodes[0xEA]
		
		return opcodes[cur_byte]
	
	def stack_push(self, val):
		if self.sp < 0:
			raise Exception("CPU::stack_push: Stack is full")
		
		self.mem.write(0x100 + self.sp, val % 0x100)
		self.sp -= 1
		
	def stack_pop(self):
		if self.sp == 0xFF:
			raise Exception("CPU::stack_pop: Stack is empty")
		
		self.sp += 1
		return self.mem.read(0x100 + self.sp)
	
	def handle_irq(self):
		self.stack_push(self.pc >> 8)
		self.stack_push(self.pc & 0xFF)
		self.stack_push(self.flag.get_byte())
		
		self.pc = self.irq_vector()
		self.cycles += 7
	
	def handle_nmi(self):
		print("------NMI-------")
		self.stack_push(self.pc >> 8)
		self.stack_push(self.pc & 0xFF)
		self.stack_push(self.flag.get_byte())
		
		self.pc = self.nmi_vector()
		self.cycles += 7
		raise Exception("")
		
	def run(self):
		# Track current cycle count for PPU
		cur_cycles = self.cycles
		
		# Fetch the current instruction and data
		instr = self.get_current_instruction()
		instr_bytes = [self.mem.read(i) for i in range(self.pc + 1, self.pc + instr[1])]
		data = int.from_bytes(instr_bytes, byteorder="little")
		
		# Print some information
		line = "0x" + "".join([format(x, "02X") for x in instr_bytes[::-1]])
		print(f"{self.pc:04X}: ({self.get_current_pc_byte():02X}) {instr[0]} {line if data != 0 else ''}");
		
		if instr[0] == "BRK":
			raise Exception("die")
		
		# Run the instruction, if found and implemented
		handler = getattr(self, "instruction_" + instr[0], self.instruction_not_implemented)
		self.pc, self.cycles = handler(self.get_current_pc_byte(), instr, data)
		
		# Let the PPU catch up. 1 CPU cycle is approx. 3 PPU cycles
		for _ in range(self.cycles - cur_cycles):
			self.ppu.run(self)
		
	
	def instruction_not_implemented(self, byte, instr, *args):
		raise Exception(f"CPU::run: {self._format_instr(byte)} is not implemented")
		
	def instruction_ADC(self, byte, instr, addr):
		pbc = False
		
		if byte == 0x69:
			data = imm(addr)
		elif byte == 0x65:
			data = zp(addr, self.mem)
		elif byte == 0x75:
			data = zpx(addr, self.mem, self.x)
		elif byte == 0x6D:
			data = abs(addr, self.mem)
		elif byte == 0x7D:
			data, pbc = absxy(addr, self.mem, self.x)
		elif byte == 0x79:
			data, pbc = absxy(addr, self.mem, self.y)
		elif byte == 0x61:
			data = indx(addr, self.mem, self.x)
		elif byte == 0x71:
			data, pbc = indy(addr, self.mem, self.y)
		
		old_acc = self.acc
		self.acc += data + self.flag.isset(Flag.C)
		
		# Clear flags
		self.flag.clear(Flag.N)
		self.flag.clear(Flag.Z)
		self.flag.clear(Flag.C)
		self.flag.clear(Flag.V)
		
		if ((old_acc^self.acc) & (data^self.acc)) & 0x80:
			self.flag.set(Flag.V)
		
		if self.acc >= 256:
			self.flag.set(Flag.C)
		
		if self.acc & 128:
			self.flag.set(Flag.N)
			
		self.acc %= 0x100
		
		if self.acc == 0:
			self.flag.set(Flag.Z)

		return self.pc + instr[1], self.cycles + instr[2] + instr[3] * pbc
		
	def instruction_AND(self, byte, instr, addr):
		# Clear flags
		self.flag.clear(Flag.N)
		self.flag.clear(Flag.Z)
		
		# Add x register
		if byte == 0x35 or byte == 0x3D or byte == 0x21:
			addr += self.x
			# Wrap zero page
			if byte == 0x35:
				addr %= 0x100
		
		# Add y register
		if byte == 0x39:
			addr += self.y
		
		# Indexed indirect x
		# https://www.c64-wiki.com/wiki/Indexed-indirect_addressing
		if byte == 0x21:
			lower = self.mem.read(addr % 0x100)
			upper = self.mem.read((addr + 1) % 0x100)
			
			addr = (upper << 8) + lower
		
		# Indirect indexed y
		# https://www.c64-wiki.com/wiki/Indirect-indexed_addressing
		if byte == 0x31:
			lower = self.mem.read(addr % 0x100)
			upper = self.mem.read((addr + 1) % 0x100)
			
			addr = (upper << 8) + lower
			addr += self.y
		
		# Load immediate
		if byte != 0x29:
			data = self.mem.read(addr % 0x10000)
		else:
			data = addr
			
		# Exec AND
		self.acc &= data
					
		if self.acc == 0:
			self.flag.set(Flag.Z)
		
		if self.acc >= 128:
			self.flag.set(Flag.N)
				
		return self.pc + instr[1], self.cycles + instr[2] + instr[3] * (self.mem.page_num(self.pc) != self.mem.page_num(addr))
	
	def instruction_ASL(self, byte, instr, addr):
		# Clear flags
		self.flag.clear(Flag.N)
		self.flag.clear(Flag.Z)
		self.flag.clear(Flag.C)
		
		# Add x register
		if byte == 0x16 or byte == 0x1E:
			addr += self.x
			# Wrap zero page
			if byte == 0x16:
				addr %= 0x100
			
		# Shift Accumulator
		if byte == 0x0A:
			if self.acc & 0x80:
				self.flag.set(Flag.C)
			
			self.acc <<= 1
			self.acc %= 0x100
			
			if self.acc & 0x80:
				self.flag.set(Flag.N)
				
			if self.acc == 0:
				self.flag.set(Flag.Z)
		else:
			# Shift memory
			data = self.mem.read(addr)
			if data & 0x80:
				self.flag.set(Flag.C)
			
			self.mem.write(addr, (data << 1) % 0x100)
			
			if self.mem.read(addr) & 0x80:
				self.flag.set(Flag.N)
				
			if self.mem.read(addr) == 0:
				self.flag.set(Flag.Z)
				
		return self.pc + instr[1], self.cycles + instr[2]
		
	def instruction_BCC(self, byte, instr, addr):
		add_cycles = instr[2]
		new_pc = self.pc + instr[1]
		if not self.flag.isset(Flag.C):
			# See: http://forum.6502.org/viewtopic.php?f=2&t=5373
			# The pc increments afer each byte being read, which means that to
			# calculate the right offset, we assume the pc to be after this instruction
			new_pc += signed_byte_to_int(addr, 8)
			add_cycles += 1
			if self.mem.page_num(self.pc) != self.mem.page_num(new_pc):
				add_cycles += instr[3]
				
		return new_pc, self.cycles + add_cycles	
	
	def instruction_BCS(self, byte, instr, addr):
		add_cycles = instr[2]
		new_pc = self.pc + instr[1]
		if self.flag.isset(Flag.C):
			# See: http://forum.6502.org/viewtopic.php?f=2&t=5373
			# The pc increments afer each byte being read, which means that to
			# calculate the right offset, we assume the pc to be after this instruction
			new_pc += signed_byte_to_int(addr, 8)
			add_cycles += 1
			if self.mem.page_num(self.pc) != self.mem.page_num(new_pc):
				add_cycles += instr[3]
				
		return new_pc, self.cycles + add_cycles	
	
	def instruction_BEQ(self, byte, instr, addr):
		add_cycles = instr[2]
		new_pc = self.pc + instr[1]
		if self.flag.isset(Flag.Z):
			# See: http://forum.6502.org/viewtopic.php?f=2&t=5373
			# The pc increments afer each byte being read, which means that to
			# calculate the right offset, we assume the pc to be after this instruction
			new_pc += signed_byte_to_int(addr, 8)
			add_cycles += 1
			if self.mem.page_num(self.pc) != self.mem.page_num(new_pc):
				add_cycles += instr[3]
				
		return new_pc, self.cycles + add_cycles	
	
	def instruction_BIT(self, byte, instr, addr):
		self.flag.clear(Flag.N)
		self.flag.clear(Flag.V)
		self.flag.clear(Flag.Z)
		
		data = self.mem.read(addr)
		
		if self.acc & data == 0:
			self.flag.set(Flag.Z)
		
		if data & 128:
			self.flag.set(Flag.N)
			
		if data & 64:
			self.flag.set(Flag.V)
			
		return self.pc + instr[1], self.cycles + instr[2]
		
	def instruction_BMI(self, byte, instr, addr):
		add_cycles = instr[2]
		new_pc = self.pc + instr[1]
		if self.flag.isset(Flag.N):
			# See: http://forum.6502.org/viewtopic.php?f=2&t=5373
			# The pc increments afer each byte being read, which means that to
			# calculate the right offset, we assume the pc to be after this instruction
			new_pc += signed_byte_to_int(addr, 8)
			add_cycles += 1
			if self.mem.page_num(self.pc) != self.mem.page_num(new_pc):
				add_cycles += instr[3]
				
		return new_pc, self.cycles + add_cycles	
		
	def instruction_BNE(self, byte, instr, addr):
		add_cycles = instr[2]
		new_pc = self.pc + instr[1]
		if not self.flag.isset(Flag.Z):
			# See: http://forum.6502.org/viewtopic.php?f=2&t=5373
			# The pc increments afer each byte being read, which means that to
			# calculate the right offset, we assume the pc to be after this instruction
			new_pc += signed_byte_to_int(addr, 8)
			add_cycles += 1
			if self.mem.page_num(self.pc) != self.mem.page_num(new_pc):
				add_cycles += instr[3]
				
		return new_pc, self.cycles + add_cycles	
		
	def instruction_BPL(self, byte, instr, addr):
		add_cycles = instr[2]
		new_pc = self.pc + instr[1]
		if not self.flag.isset(Flag.N):
			# See: http://forum.6502.org/viewtopic.php?f=2&t=5373
			# The pc increments afer each byte being read, which means that to
			# calculate the right offset, we assume the pc to be after this instruction
			new_pc += signed_byte_to_int(addr, 8)
			add_cycles += 1
			if self.mem.page_num(self.pc) != self.mem.page_num(new_pc):
				add_cycles += instr[3]
				
		return new_pc, self.cycles + add_cycles			
		
	def instruction_BRK(self, byte, instr, *args):		
		tostack = self.pc + instr[1] + 2
		self.stack_push(tostack >> 8)
		self.stack_push(tostack & 0xFF)
		self.stack_push(self.flag.get_byte() | Flag.B)
		
		self.flag.set(Flag.B)
		
		return self.nmi_vector(), self.cycles + instr[2]
	
	def instruction_BVC(self, byte, instr, addr):
		add_cycles = instr[2]
		new_pc = self.pc + instr[1]
		if not self.flag.isset(Flag.V):
			# See: http://forum.6502.org/viewtopic.php?f=2&t=5373
			# The pc increments afer each byte being read, which means that to
			# calculate the right offset, we assume the pc to be after this instruction
			new_pc += signed_byte_to_int(addr, 8)
			add_cycles += 1
			if self.mem.page_num(self.pc) != self.mem.page_num(new_pc):
				add_cycles += instr[3]
				
		return new_pc, self.cycles + add_cycles	
	
	def instruction_BVS(self, byte, instr, addr):
		add_cycles = instr[2]
		new_pc = self.pc + instr[1]
		if self.flag.isset(Flag.V):
			# See: http://forum.6502.org/viewtopic.php?f=2&t=5373
			# The pc increments afer each byte being read, which means that to
			# calculate the right offset, we assume the pc to be after this instruction
			new_pc += signed_byte_to_int(addr, 8)
			add_cycles += 1
			if self.mem.page_num(self.pc) != self.mem.page_num(new_pc):
				add_cycles += instr[3]
				
		return new_pc, self.cycles + add_cycles	
	
	def instruction_CLC(self, byte, instr, *args):
		self.flag.clear(Flag.C)
		
		return self.pc + instr[1], self.cycles + instr[2]
		
	def instruction_CLD(self, byte, instr, *args):
		self.flag.clear(Flag.D)
		
		return self.pc + instr[1], self.cycles + instr[2]
		
	def instruction_CLI(self, byte, instr, *args):
		self.flag.clear(Flag.I)
		
		return self.pc + instr[1], self.cycles + instr[2]
		
	def instruction_CLV(self, byte, instr, *args):
		self.flag.clear(Flag.V)
		
		return self.pc + instr[1], self.cycles + instr[2]
		
	def instruction_CMP(self, byte, instr, addr):
		# Clear flags
		self.flag.clear(Flag.N)
		self.flag.clear(Flag.Z)
		self.flag.clear(Flag.C)
		
		# Add x register
		if byte == 0xD5 or byte == 0xDD or byte == 0xC1:
			addr += self.x
			# Wrap zero page
			if byte == 0xD5:
				addr %= 0x100
		
		# Add y register
		if byte == 0xD9:
			addr += self.y
		
		# Indexed indirect x
		# https://www.c64-wiki.com/wiki/Indexed-indirect_addressing
		if byte == 0xC1:
			lower = self.mem.read(addr % 0x100)
			upper = self.mem.read((addr + 1) % 0x100)
			
			addr = (upper << 8) + lower
		
		# Indirect indexed y
		# https://www.c64-wiki.com/wiki/Indirect-indexed_addressing
		if byte == 0xD1:
			lower = self.mem.read(addr % 0x100)
			upper = self.mem.read((addr + 1) % 0x100)
			
			addr = (upper << 8) + lower
			addr += self.y
		
		# Load immediate
		if byte != 0xC9:
			data = self.mem.read(addr % 0x10000)
		else:
			data = addr
			
		if self.acc >= data:
			self.flag.set(Flag.C)
		
		if self.acc == data:
			self.flag.set(Flag.Z)
		
		if ((self.acc - data) % 0x100) & 128:
			self.flag.set(Flag.N)
				
		return self.pc + instr[1], self.cycles + instr[2] + instr[3] * (self.mem.page_num(self.pc) != self.mem.page_num(addr))
		
	def instruction_CPX(self, byte, instr, addr):
		# Clear flags
		self.flag.clear(Flag.N)
		self.flag.clear(Flag.Z)
		self.flag.clear(Flag.C)
		
		# Load immediate
		if byte != 0xE0:
			data = self.mem.read(addr % 0x10000)
		else:
			data = addr
			
		if self.x >= data:
			self.flag.set(Flag.C)
		
		if self.x == data:
			self.flag.set(Flag.Z)
		
		if (self.x - data) & 128:
			self.flag.set(Flag.N)
				
		return self.pc + instr[1], self.cycles + instr[2]
		
	def instruction_CPY(self, byte, instr, addr):
		# Clear flags
		self.flag.clear(Flag.N)
		self.flag.clear(Flag.Z)
		self.flag.clear(Flag.C)
		
		# Load immediate
		if byte != 0xC0:
			data = self.mem.read(addr % 0x10000)
		else:
			data = addr
			
		if self.y >= data:
			self.flag.set(Flag.C)

		if self.y == data:
			self.flag.set(Flag.Z)
		
		if (self.y - data) & 128:
			self.flag.set(Flag.N)
				
		return self.pc + instr[1], self.cycles + instr[2]
		
	def instruction_DEC(self, byte, instr, addr):
		# Clear flags
		self.flag.clear(Flag.N)
		self.flag.clear(Flag.Z)
		
		# Add x register
		if byte == 0xD6 or byte == 0xDE:
			addr += self.x
			# Wrap zero page
			if byte == 0xD6:
				addr %= 0x100
				
		# Decrement memory
		self.mem.write(addr, (self.mem.read(addr) - 1) % 0x100)
		
		# Set flags
		if self.mem.read(addr) == 0:
			self.flag.set(Flag.Z)
			
		if self.mem.read(addr) & 0x80:
			self.flag.set(Flag.N)
		
		return self.pc + instr[1], self.cycles + instr[2]
		
	def instruction_DEX(self, byte, instr, *args):
		self.flag.clear(Flag.N)
		self.flag.clear(Flag.Z)
		
		self.x -= 1
		self.x %= 0x100
		
		if self.x == 0:
			self.flag.set(Flag.Z)
		
		if self.x & 0x80:
			self.flag.set(Flag.N)
		
		return self.pc + instr[1], self.cycles + instr[2]
		
	def instruction_DEY(self, byte, instr, *args):
		self.flag.clear(Flag.N)
		self.flag.clear(Flag.Z)
		
		self.y -= 1
		self.y %= 0x100
		
		if self.y == 0:
			self.flag.set(Flag.Z)
		
		if self.y & 0x80:
			self.flag.set(Flag.N)
		
		return self.pc + instr[1], self.cycles + instr[2]
		
	def instruction_EOR(self, byte, instr, addr):
		# Clear flags
		self.flag.clear(Flag.N)
		self.flag.clear(Flag.Z)
		
		# Add x register
		if byte == 0x55 or byte == 0x5D or byte == 0x41:
			addr += self.x
			# Wrap zero page
			if byte == 0x55:
				addr %= 0x100
		
		# Add y register
		if byte == 0x59:
			addr += self.y
			
		# Indexed indirect x
		# https://www.c64-wiki.com/wiki/Indexed-indirect_addressing
		if byte == 0x41:
			lower = self.mem.read(addr % 0x100)
			upper = self.mem.read((addr + 1) % 0x100)
			
			addr = (upper << 8) + lower
		
		# Indirect indexed y
		# https://www.c64-wiki.com/wiki/Indirect-indexed_addressing
		if byte == 0x51:
			lower = self.mem.read(addr % 0x100)
			upper = self.mem.read((addr + 1) % 0x100)
			
			addr = (upper << 8) + lower
			addr += self.y
		
		# Load immediate
		if byte != 0x49:
			data = self.mem.read(addr % 0x10000)
		else:
			data = addr
			
		# Exec XOR
		self.acc ^= data
					
		if self.acc == 0:
			self.flag.set(Flag.Z)
		
		if self.acc >= 128:
			self.flag.set(Flag.N)
				
		return self.pc + instr[1], self.cycles + instr[2] + instr[3] * (self.mem.page_num(self.pc) != self.mem.page_num(addr))
		
	def instruction_INC(self, byte, instr, addr):
		# Clear flags
		self.flag.clear(Flag.N)
		self.flag.clear(Flag.Z)
		
		# Add x register
		if byte == 0xF6 or byte == 0xFE:
			addr += self.x
			# Wrap zero page
			if byte == 0xF6:
				addr %= 0x100
				
		# Increment memory
		self.mem.write(addr, (self.mem.read(addr) + 1) % 0x100)
		
		# Set flags
		if self.mem.read(addr) == 0:
			self.flag.set(Flag.Z)
			
		if self.mem.read(addr) & 0x80:
			self.flag.set(Flag.N)
		
		return self.pc + instr[1], self.cycles + instr[2]
		
	def instruction_INX(self, byte, instr, *args):
		self.flag.clear(Flag.N)
		self.flag.clear(Flag.Z)
		
		self.x += 1
		self.x %= 0x100
		
		if self.x == 0:
			self.flag.set(Flag.Z)
		
		if self.x & 0x80:
			self.flag.set(Flag.N)
		
		return self.pc + instr[1], self.cycles + instr[2]
		
	def instruction_INY(self, byte, instr, *args):
		self.flag.clear(Flag.N)
		self.flag.clear(Flag.Z)
		
		self.y += 1
		self.y %= 0x100
		
		if self.y == 0:
			self.flag.set(Flag.Z)
		
		if self.y & 0x80:
			self.flag.set(Flag.N)
		
		return self.pc + instr[1], self.cycles + instr[2]
		
	def instruction_JMP(self, byte, instr, addr):
		if byte == 0x4C:
			# Absolute jump
			new_pc = addr
		else:
			# Relative jump, including replicating hardware bug where when the lower
			# address is on the last byte of a page, the upper address is taken
			# from the same page, rather than the next one
			broken_addr = (addr & 0xFF00) + ((addr + 1) & 0x00FF)
			low = self.mem.read(addr)
			high = self.mem.read(broken_addr)
			
			new_pc = (high << 8) + low
		
		return new_pc, self.cycles + instr[2]
		
	def instruction_JSR(self, byte, instr, addr):
		# Info: https://stackoverflow.com/questions/21465200/6502-assembler-the-rts-command-and-the-stack
		tostack = self.pc + instr[1] - 1
		self.stack_push(tostack >> 8)
		self.stack_push(tostack & 0xFF)
		
		return addr, self.cycles + instr[2]
		
	def instruction_LDA(self, byte, instr, addr):
		# Clear flags
		self.flag.clear(Flag.N)
		self.flag.clear(Flag.Z)
		
		# Add x register
		if byte == 0xB5 or byte == 0xBD or byte == 0xA1:
			addr += self.x
			# Wrap zero page
			if byte == 0xB5:
				addr %= 0x100
		
		# Add y register
		if byte == 0xB9:
			addr += self.y
			
		# Indexed indirect x
		# https://www.c64-wiki.com/wiki/Indexed-indirect_addressing
		if byte == 0xA1:
			lower = self.mem.read(addr % 0x100)
			upper = self.mem.read((addr + 1) % 0x100)
			
			addr = (upper << 8) + lower
		
		# Indirect indexed y
		# https://www.c64-wiki.com/wiki/Indirect-indexed_addressing
		if byte == 0xB1:
			lower = self.mem.read(addr % 0x100)
			upper = self.mem.read((addr + 1) % 0x100)
			
			addr = (upper << 8) + lower
			addr += self.y
		
		# Load immediate
		if byte != 0xA9:
			data = self.mem.read(addr % 0x10000)
		else:
			data = addr
			
		self.acc = data
		
		if self.acc == 0:
			self.flag.set(Flag.Z)
		
		if self.acc >= 128:
			self.flag.set(Flag.N)
				
		return self.pc + instr[1], self.cycles + instr[2] + instr[3] * (self.mem.page_num(self.pc) != self.mem.page_num(addr))
		
	def instruction_LDX(self, byte, instr, addr):
		# Clear flags
		self.flag.clear(Flag.N)
		self.flag.clear(Flag.Z)
		
		# Add y register
		if byte == 0xB6 or byte == 0xBE:
			addr += self.y
			# Wrap Zero Page
			if byte == 0xB6:
				addr %= 0x100
		
		# Load data from address
		if byte != 0xA2:
			data = self.mem.read(addr)
		else:
			# Load immediate
			data = addr
		
		self.x = data
		
		#Set flags
		if self.x == 0:
			self.flag.set(Flag.Z)
			
		if self.x >= 0x80:
			self.flag.set(Flag.N)
			
		return self.pc + instr[1], self.cycles + instr[2] + instr[3] * (self.mem.page_num(self.pc) != self.mem.page_num(addr))
		
	def instruction_LDY(self, byte, instr, addr):
		# Clear flags
		self.flag.clear(Flag.N)
		self.flag.clear(Flag.Z)
		
		# Add x register
		if byte == 0xB4 or byte == 0xBC:
			addr += self.x
			# Wrap Zero Page
			if byte == 0xB4:
				addr %= 0x100
		
		# Load data from address
		if byte != 0xA0:
			data = self.mem.read(addr)
		else:
			# Load immediate
			data = addr
		
		self.y = data
		
		#Set flags
		if self.y == 0:
			self.flag.set(Flag.Z)
			
		if self.y >= 0x80:
			self.flag.set(Flag.N)
			
		return self.pc + instr[1], self.cycles + instr[2] + instr[3] * (self.mem.page_num(self.pc) != self.mem.page_num(addr))
		
	def instruction_LSR(self, byte, instr, addr):
		# Clear flags
		self.flag.clear(Flag.N)
		self.flag.clear(Flag.Z)
		self.flag.clear(Flag.C)
		
		# Add x register
		if byte == 0x56 or byte == 0x5E:
			addr += self.x
			# Wrap zero page
			if byte == 0x56:
				addr %= 0x100
				
		# Shift value at addr or at acc
		if byte == 0x4A:
			old_data = self.acc
			self.acc >>= 1
			new_data = self.acc
		else:
			old_data = self.mem.read(addr)
			self.mem.write(addr, old_data >> 1)
			new_data = self.mem.read(addr)

		if old_data & 0x01:
			self.flag.set(Flag.C)
			
		if new_data == 0:
			self.flag.set(Flag.Z)
		
		if new_data & 0x80:		# Theoretically, this should never happen
			self.flag.set(Flag.N)
				
		return self.pc + instr[1], self.cycles + instr[2] + instr[3] * (self.mem.page_num(self.pc) != self.mem.page_num(addr))
		
	def instruction_NOP(self, byte, instr, *args):
		return self.pc + instr[1], self.cycles + instr[2]
		
	def instruction_ORA(self, byte, instr, addr):
		# Clear flags
		self.flag.clear(Flag.N)
		self.flag.clear(Flag.Z)
		
		# Add x register
		if byte == 0x15 or byte == 0x1D or byte == 0x01:
			addr += self.x
			# Wrap zero page
			if byte == 0x15:
				addr %= 0x100
		
		# Add y register
		if byte == 0x19:
			addr += self.y
			
		# Indexed indirect x
		# https://www.c64-wiki.com/wiki/Indexed-indirect_addressing
		if byte == 0x01:
			lower = self.mem.read(addr % 0x100)
			upper = self.mem.read((addr + 1) % 0x100)
			
			addr = (upper << 8) + lower
		
		# Indirect indexed y
		# https://www.c64-wiki.com/wiki/Indirect-indexed_addressing
		if byte == 0x11:
			lower = self.mem.read(addr % 0x100)
			upper = self.mem.read((addr + 1) % 0x100)
			
			addr = (upper << 8) + lower
			addr += self.y
		
		# Load immediate
		if byte != 0x09:
			data = self.mem.read(addr % 0x10000)
		else:
			data = addr
			
		self.acc |= data
		
		if self.acc == 0:
			self.flag.set(Flag.Z)
		
		if self.acc >= 128:
			self.flag.set(Flag.N)
				
		return self.pc + instr[1], self.cycles + instr[2] + instr[3] * (self.mem.page_num(self.pc) != self.mem.page_num(addr))
		
	def instruction_PHA(self, byte, instr, *args):
		self.stack_push(self.acc)
		
		return self.pc + instr[1], self.cycles + instr[2]
		
	def instruction_PHP(self, byte, instr, *args):
		# See: https://wiki.nesdev.com/w/index.php/Status_flags#The_B_flag
		self.stack_push(self.flag.get_byte() | Flag.B)
		
		return self.pc + instr[1], self.cycles + instr[2]
		
	def instruction_PLA(self, byte, instr, *args):
		self.flag.clear(Flag.Z)
		self.flag.clear(Flag.N)
		
		self.acc = self.stack_pop()
		
		if self.acc == 0:
			self.flag.set(Flag.Z)
		
		if self.acc & 0x80:
			self.flag.set(Flag.N)
		
		return self.pc + instr[1], self.cycles + instr[2]
		
	def instruction_PLP(self, byte, instr, *args):
		# Ignore B Flag: https://wiki.nesdev.com/w/index.php/Status_flags#The_B_flag
		self.flag.set_byte(self.stack_pop() & ~Flag.B)
		
		return self.pc + instr[1], self.cycles + instr[2]
		
	def instruction_ROL(self, byte, instr, addr):
		# Add x register
		if byte == 0x36 or byte == 0x3E:
			addr += self.x
			# Wrap zero page
			if byte == 0x36:
				addr %= 0x100
				
		# Shift value at addr or at acc
		if byte == 0x2A:
			old_data = self.acc
			self.acc = ((self.acc << 1) + self.flag.isset(Flag.C)) % 0x100
			new_data = self.acc
		else:
			old_data = self.mem.read(addr)
			self.mem.write(addr, ((old_data << 1) + self.flag.isset(Flag.C)) % 0x100)
			new_data = self.mem.read(addr)
			
		# Clear flags
		self.flag.clear(Flag.N)
		self.flag.clear(Flag.Z)
		self.flag.clear(Flag.C)

		if old_data & 0x80:
			self.flag.set(Flag.C)
			
		if new_data == 0:
			self.flag.set(Flag.Z)
		
		if new_data & 0x80:
			self.flag.set(Flag.N)
				
		return self.pc + instr[1], self.cycles + instr[2] + instr[3] * (self.mem.page_num(self.pc) != self.mem.page_num(addr))
		
	def instruction_ROR(self, byte, instr, addr):		
		# Add x register
		if byte == 0x76 or byte == 0x7E:
			addr += self.x
			# Wrap zero page
			if byte == 0x76:
				addr %= 0x100
				
		# Shift value at addr or at acc
		if byte == 0x6A:
			old_data = self.acc
			self.acc = (self.acc >> 1) + (self.flag.isset(Flag.C) << 7)
			new_data = self.acc
		else:
			old_data = self.mem.read(addr)
			self.mem.write(addr, (old_data >> 1) + (self.flag.isset(Flag.C) << 7))
			new_data = self.mem.read(addr)
			
		# Clear flags
		self.flag.clear(Flag.N)
		self.flag.clear(Flag.Z)
		self.flag.clear(Flag.C)

		if old_data & 0x01:
			self.flag.set(Flag.C)
			
		if new_data == 0:
			self.flag.set(Flag.Z)
		
		if new_data & 0x80:
			self.flag.set(Flag.N)
				
		return self.pc + instr[1], self.cycles + instr[2] + instr[3] * (self.mem.page_num(self.pc) != self.mem.page_num(addr))
		
	def instruction_RTI(self, byte, instr, *args):
		# See: https://wiki.nesdev.com/w/index.php/Status_flags#The_B_flag
		flags = self.stack_pop() & ~Flag.B
		new_pc = self.stack_pop() + (self.stack_pop() << 8)
		
		self.flag.set_byte(flags)
		
		return new_pc, self.cycles + instr[2]
		
	def instruction_RTS(self, byte, instr, *args):
		lower = self.stack_pop()
		higher = self.stack_pop()
		new_pc = lower + (higher << 8)
		
		return new_pc + instr[1], self.cycles + instr[2]
		
	def instruction_SBC(self, byte, instr, addr):
		# Add x register
		if byte == 0xF5 or byte == 0xFD or byte == 0xE1:
			addr += self.x
			# Wrap zero page
			if byte == 0xF5:
				addr %= 0x100
		
		# Add y register
		if byte == 0xF9:
			addr += self.y
		
		# Indexed indirect x
		# https://www.c64-wiki.com/wiki/Indexed-indirect_addressing
		if byte == 0xE1:
			lower = self.mem.read(addr % 0x100)
			upper = self.mem.read((addr + 1) % 0x100)
			
			addr = (upper << 8) + lower
		
		# Indirect indexed y
		# https://www.c64-wiki.com/wiki/Indirect-indexed_addressing
		if byte == 0xF1:
			lower = self.mem.read(addr % 0x100)
			upper = self.mem.read((addr + 1) % 0x100)
			
			addr = (upper << 8) + lower
			addr += self.y
		
		# Load immediate
		if byte != 0xE9:
			data = self.mem.read(addr % 0x10000)
		else:
			data = addr

		old_acc = self.acc
		self.acc += ~data + self.flag.isset(Flag.C)
		
		# Clear flags
		self.flag.clear(Flag.N)
		self.flag.clear(Flag.Z)
		self.flag.set(Flag.C) # This should be set before SBC is called, but doesn't seem to be
		self.flag.clear(Flag.V)
		
		if self.acc < 0:
			self.flag.clear(Flag.C)
		
		if self.acc & 128:
			self.flag.set(Flag.N)
			
		self.acc %= 0x100
		
		if self.acc == 0:
			self.flag.set(Flag.Z)
			
		if ((old_acc^self.acc) & ~(data^self.acc)) & 0x80:
			self.flag.set(Flag.V)

		return self.pc + instr[1], self.cycles + instr[2] + instr[3] * (self.mem.page_num(self.pc) != self.mem.page_num(addr))
		
	def instruction_SEC(self, byte, instr, *args):
		self.flag.set(Flag.C)
		
		return self.pc + instr[1], self.cycles + instr[2]
		
	def instruction_SED(self, byte, instr, *args):
		self.flag.set(Flag.D)
		
		return self.pc + instr[1], self.cycles + instr[2]
		
	def instruction_SEI(self, byte, instr, *args):
		self.flag.set(Flag.I)
		
		return self.pc + instr[1], self.cycles + instr[2]
		
	def instruction_STA(self, byte, instr, addr):
		# Add x register
		if byte == 0x95 or byte == 0x9D or byte == 0x81:
			addr = (addr + self.x)
		
		# Wrap Zero Page
		if byte == 0x95:
			addr %= 0x100
		
		# Add y register
		if byte == 0x99:
			addr = (addr + self.y)
			
		# Indexed indirect x
		# https://www.c64-wiki.com/wiki/Indexed-indirect_addressing
		if byte == 0x81:
			lower = self.mem.read(addr % 0x100)
			upper = self.mem.read((addr + 1) % 0x100)
			
			addr = (upper << 8) + lower
		
		# Indirect indexed y
		# https://www.c64-wiki.com/wiki/Indirect-indexed_addressing
		if byte == 0x91:
			lower = self.mem.read(addr % 0x100)
			upper = self.mem.read((addr + 1) % 0x100)
			
			addr = (upper << 8) + lower
			addr += self.y
		
		addr %= 0x10000
		self.mem.write(addr, self.acc)
		
		return self.pc + instr[1], self.cycles + instr[2]
		
	def instruction_STX(self, byte, instr, addr):
		# Add y register
		if byte == 0x96:
			addr += self.y
			addr %= 0x100
		
		addr %= 0x10000
		self.mem.write(addr, self.x)
		
		return self.pc + instr[1], self.cycles + instr[2]
		
	def instruction_STY(self, byte, instr, addr):
		# Add x register
		if byte == 0x94:
			addr += self.x
			addr %= 0x100
		
		addr %= 0x10000
		self.mem.write(addr, self.y)
		
		return self.pc + instr[1], self.cycles + instr[2]
		
	def instruction_TAX(self, byte, instr, *args):
		self.flag.clear(Flag.N)
		self.flag.clear(Flag.Z)
		
		self.x = self.acc
		
		if self.x == 0:
			self.flag.set(Flag.Z)
		
		if self.x >= 0x80:
			self.flag.set(Flag.N)
		
		return self.pc + instr[1], self.cycles + instr[2]
		
	def instruction_TAY(self, byte, instr, *args):
		self.flag.clear(Flag.N)
		self.flag.clear(Flag.Z)
		
		self.y = self.acc
		
		if self.y == 0:
			self.flag.set(Flag.Z)
		
		if self.y >= 0x80:
			self.flag.set(Flag.N)
		
		return self.pc + instr[1], self.cycles + instr[2]
		
	def instruction_TSX(self, byte, instr, *args):
		self.flag.clear(Flag.Z)
		self.flag.clear(Flag.N)
		
		self.x = self.sp
		
		if self.x == 0:
			self.flag.set(Flag.Z)
			
		if self.x & 0x80:
			self.flag.set(Flag.N)
		
		return self.pc + instr[1], self.cycles + instr[2]
		
	def instruction_TXA(self, byte, instr, *args):
		self.flag.clear(Flag.N)
		self.flag.clear(Flag.Z)
		
		self.acc = self.x
		
		if self.acc == 0:
			self.flag.set(Flag.Z)
		
		if self.acc >= 0x80:
			self.flag.set(Flag.N)
		
		return self.pc + instr[1], self.cycles + instr[2]
		
	def instruction_TXS(self, byte, instr, *args):
		self.sp = self.x
		
		return self.pc + instr[1], self.cycles + instr[2]
		
	def instruction_TYA(self, byte, instr, *args):
		self.flag.clear(Flag.N)
		self.flag.clear(Flag.Z)
		
		self.acc = self.y
		
		if self.y == 0:
			self.flag.set(Flag.Z)
		
		if self.y >= 0x80:
			self.flag.set(Flag.N)
		
		return self.pc + instr[1], self.cycles + instr[2]
	
	## Illegal opcodes
	
	def instruction_iDCP(self, byte, instr, addr):
		# Combine DEC and CMP
		# Clear flags
		self.flag.clear(Flag.N)
		self.flag.clear(Flag.Z)
		self.flag.clear(Flag.C)
		
		# Add x register
		if byte == 0xD7 or byte == 0xDF or byte == 0xC3:
			addr += self.x
			# Wrap zero page
			if byte == 0xD7:
				addr %= 0x100
				
		# Add y register
		if byte == 0xD8 or byte == 0xDB:
			addr += self.y
		
		# Indexed indirect x
		# https://www.c64-wiki.com/wiki/Indexed-indirect_addressing
		if byte == 0xC3:
			lower = self.mem.read(addr % 0x100)
			upper = self.mem.read((addr + 1) % 0x100)
			
			addr = (upper << 8) + lower
		
		# Indirect indexed y
		# https://www.c64-wiki.com/wiki/Indirect-indexed_addressing
		if byte == 0xD3:
			lower = self.mem.read(addr % 0x100)
			upper = self.mem.read((addr + 1) % 0x100)
			
			addr = (upper << 8) + lower
			addr += self.y
		
				
		# Decrement memory
		data = (self.mem.read(addr) - 1) % 0x100
		self.mem.write(addr, data)
			
		if self.acc >= data:
			self.flag.set(Flag.C)
		
		if self.acc == data:
			self.flag.set(Flag.Z)
		
		if ((self.acc - data) % 0x100) & 0x80:
			self.flag.set(Flag.N)
		
		return self.pc + instr[1], self.cycles + instr[2]
	
	def instruction_iISC(self, byte, instr, addr):
		# Combine INC and SBC
		# Add x register
		if byte == 0xF7 or byte == 0xFF or byte == 0xE3:
			addr += self.x
			# Wrap zero page
			if byte == 0xF7:
				addr %= 0x100
				
		# Add y register
		if byte == 0xFB:
			addr += self.y
			
		# Indexed indirect x
		# https://www.c64-wiki.com/wiki/Indexed-indirect_addressing
		if byte == 0xE3:
			lower = self.mem.read(addr % 0x100)
			upper = self.mem.read((addr + 1) % 0x100)
			
			addr = (upper << 8) + lower
		
		# Indirect indexed y
		# https://www.c64-wiki.com/wiki/Indirect-indexed_addressing
		if byte == 0xF3:
			lower = self.mem.read(addr % 0x100)
			upper = self.mem.read((addr + 1) % 0x100)
			
			addr = (upper << 8) + lower
			addr += self.y
				
		# Increment memory
		data = (self.mem.read(addr) + 1) % 0x100
		self.mem.write(addr, data)
		
		# SBC
		old_acc = self.acc
		self.acc += ~data + self.flag.isset(Flag.C)
		
		# Clear flags
		self.flag.clear(Flag.N)
		self.flag.clear(Flag.Z)
		self.flag.set(Flag.C) # This should be set before SBC is called, but doesn't seem to be
		self.flag.clear(Flag.V)
		
		if self.acc < 0:
			self.flag.clear(Flag.C)
		
		if self.acc & 128:
			self.flag.set(Flag.N)
			
		self.acc %= 0x100
		
		if self.acc == 0:
			self.flag.set(Flag.Z)
			
		if ((old_acc^self.acc) & ~(data^self.acc)) & 0x80:
			self.flag.set(Flag.V)
			
		return self.pc + instr[1], self.cycles + instr[2]
	
	def instruction_iLAX(self, byte, instr, addr):
		# Combine LDA and LDX
		# Clear flags
		self.flag.clear(Flag.N)
		self.flag.clear(Flag.Z)
		
		# Add y register
		if byte == 0xB7 or byte == 0xBF:
			addr += self.y
			# Check zero page
			if byte == 0xB7:
				addr %= 0x100
			
		# Indexed indirect x
		# https://www.c64-wiki.com/wiki/Indexed-indirect_addressing
		if byte == 0xA3:
			addr += self.x
			
			lower = self.mem.read(addr % 0x100)
			upper = self.mem.read((addr + 1) % 0x100)
			
			addr = (upper << 8) + lower
		
		# Indirect indexed y
		# https://www.c64-wiki.com/wiki/Indirect-indexed_addressing
		if byte == 0xB3:
			lower = self.mem.read(addr % 0x100)
			upper = self.mem.read((addr + 1) % 0x100)
			
			addr = (upper << 8) + lower
			addr += self.y
		
		data = self.mem.read(addr % 0x10000)
			
		self.x = data
		self.acc = data
		
		if data == 0:
			self.flag.set(Flag.Z)
		
		if data >= 0x80:
			self.flag.set(Flag.N)
		
		return self.pc + instr[1], self.cycles + instr[2] + instr[3] * (self.mem.page_num(self.pc) != self.mem.page_num(addr))
	
	def instruction_iNOP(self, byte, instr, addr):
		return self.pc + instr[1], self.cycles + instr[2] + instr[3] * (self.mem.page_num(self.pc) != self.mem.page_num(addr))
	
	def instruction_iRLA(self, byte, instr, addr):
		# Combine ROL and AND
		# Add x register
		if byte == 0x37 or byte == 0x3F or byte == 0x23:
			addr += self.x
			# Wrap zero page
			if byte == 0x37:
				addr %= 0x100
				
		# Add y register
		if byte == 0x3B:
			addr += self.y
		
		# Indexed indirect x
		# https://www.c64-wiki.com/wiki/Indexed-indirect_addressing
		if byte == 0x23:
			lower = self.mem.read(addr % 0x100)
			upper = self.mem.read((addr + 1) % 0x100)
			
			addr = (upper << 8) + lower
		
		# Indirect indexed y
		# https://www.c64-wiki.com/wiki/Indirect-indexed_addressing
		if byte == 0x33:
			lower = self.mem.read(addr % 0x100)
			upper = self.mem.read((addr + 1) % 0x100)
			
			addr = (upper << 8) + lower
			addr += self.y
				
		# Shift value in memory
		old_data = self.mem.read(addr)
		self.mem.write(addr, ((old_data << 1) + self.flag.isset(Flag.C)) % 0x100)
		new_data = self.mem.read(addr)
			
		# Clear flags
		self.flag.clear(Flag.N)
		self.flag.clear(Flag.Z)
		self.flag.clear(Flag.C)

		if old_data & 0x80:
			self.flag.set(Flag.C)
			
		# Exec AND
		self.acc &= new_data
					
		if self.acc == 0:
			self.flag.set(Flag.Z)
		
		if self.acc >= 128:
			self.flag.set(Flag.N)
				
		return self.pc + instr[1], self.cycles + instr[2]
	
	def instruction_iRRA(self, byte, instr, addr):
		# Combine ROR and ADC
		# Add x register
		if byte == 0x77 or byte == 0x7F or byte == 0x63:
			addr += self.x
			# Wrap zero page
			if byte == 0x77:
				addr %= 0x100
		
		# Add y register
		if byte == 0x7B:
			addr += self.y
		
		# Indexed indirect x
		# https://www.c64-wiki.com/wiki/Indexed-indirect_addressing
		if byte == 0x63:
			lower = self.mem.read(addr % 0x100)
			upper = self.mem.read((addr + 1) % 0x100)
			
			addr = (upper << 8) + lower
		
		# Indirect indexed y
		# https://www.c64-wiki.com/wiki/Indirect-indexed_addressing
		if byte == 0x73:
			lower = self.mem.read(addr % 0x100)
			upper = self.mem.read((addr + 1) % 0x100)
			
			addr = (upper << 8) + lower
			addr += self.y
				
		# Shift value in memory
		old_data = self.mem.read(addr)
		self.mem.write(addr, (old_data >> 1) + (self.flag.isset(Flag.C) << 7))
		new_data = self.mem.read(addr)
		
		if old_data & 0x01:
			self.flag.set(Flag.C)
			
		if new_data == 0:
			self.flag.set(Flag.Z)
		
		if new_data & 0x80:
			self.flag.set(Flag.N)
		
		old_acc = self.acc
		self.acc += new_data + self.flag.isset(Flag.C)
		
		# Clear flags
		self.flag.clear(Flag.N)
		self.flag.clear(Flag.Z)
		self.flag.clear(Flag.C)
		self.flag.clear(Flag.V)
		
		if ((old_acc^self.acc) & (new_data^self.acc)) & 0x80:
			self.flag.set(Flag.V)
		
		if self.acc >= 256:
			self.flag.set(Flag.C)
		
		if self.acc & 128:
			self.flag.set(Flag.N)
			
		self.acc %= 0x100
		
		if self.acc == 0:
			self.flag.set(Flag.Z)
				
		return self.pc + instr[1], self.cycles + instr[2]
		
	
	def instruction_iSAX(self, byte, instr, addr):
		# Add y, zeropage
		if byte == 0x97:
			addr += self.y
			addr %= 0x100
		
		# Indexed indirect x
		# https://www.c64-wiki.com/wiki/Indexed-indirect_addressing
		if byte == 0x83:
			addr += self.x
			
			lower = self.mem.read(addr % 0x100)
			upper = self.mem.read((addr + 1) % 0x100)
			
			addr = (upper << 8) + lower
		
		# Store bitwise AND of acc and x
		data = self.acc & self.x
		self.mem.write(addr, data)
			
		return self.pc + instr[1], self.cycles + instr[2]
	
	def instruction_iSBC(self, byte, instr, data):
		# This instruction uses #imm only
		old_acc = self.acc
		self.acc += ~data + self.flag.isset(Flag.C)
		
		# Clear flags
		self.flag.clear(Flag.N)
		self.flag.clear(Flag.Z)
		self.flag.set(Flag.C) # This should be set before SBC is called, but doesn't seem to be
		self.flag.clear(Flag.V)
		
		if self.acc < 0:
			self.flag.clear(Flag.C)
		
		if self.acc & 128:
			self.flag.set(Flag.N)
			
		self.acc %= 0x100
		
		if self.acc == 0:
			self.flag.set(Flag.Z)
			
		if ((old_acc^self.acc) & ~(data^self.acc)) & 0x80:
			self.flag.set(Flag.V)
			
		return self.pc + instr[1], self.cycles + instr[2]
	
	def instruction_iSLO(self, byte, instr, addr):
		# Combine ASL and ORA
		# Clear flags
		self.flag.clear(Flag.N)
		self.flag.clear(Flag.Z)
		self.flag.clear(Flag.C)
		
		# Add x register
		if byte == 0x17 or byte == 0x1F or byte == 0x03:
			addr += self.x
			# Wrap zero page
			if byte == 0x17:
				addr %= 0x100
		
		# Add y register
		if byte == 0x1B:
			addr += self.y
			
		# Indexed indirect x
		# https://www.c64-wiki.com/wiki/Indexed-indirect_addressing
		if byte == 0x03:
			lower = self.mem.read(addr % 0x100)
			upper = self.mem.read((addr + 1) % 0x100)
			
			addr = (upper << 8) + lower
		
		# Indirect indexed y
		# https://www.c64-wiki.com/wiki/Indirect-indexed_addressing
		if byte == 0x13:
			lower = self.mem.read(addr % 0x100)
			upper = self.mem.read((addr + 1) % 0x100)
			
			addr = (upper << 8) + lower
			addr += self.y
		
		# Shift Memory
		data = self.mem.read(addr)
		if data & 0x80:
			self.flag.set(Flag.C)
		
		data = (data << 1) % 0x100
		
		self.mem.write(addr, data)
			
		self.acc |= data
		
		if self.acc == 0:
			self.flag.set(Flag.Z)
		
		if self.acc >= 128:
			self.flag.set(Flag.N)
			
		return self.pc + instr[1], self.cycles + instr[2]
	
	def instruction_iSRE(self, byte, instr, addr):
		# Combine LSR and EOR
		# Clear flags
		self.flag.clear(Flag.N)
		self.flag.clear(Flag.Z)
		self.flag.clear(Flag.C)
		
		# Add x register
		if byte == 0x57 or byte == 0x5F or byte == 0x43:
			addr += self.x
			# Wrap zero page
			if byte == 0x57:
				addr %= 0x100
		
		# Add y register
		if byte == 0x5B:
			addr += self.y
			
		# Indexed indirect x
		# https://www.c64-wiki.com/wiki/Indexed-indirect_addressing
		if byte == 0x43:
			lower = self.mem.read(addr % 0x100)
			upper = self.mem.read((addr + 1) % 0x100)
			
			addr = (upper << 8) + lower
		
		# Indirect indexed y
		# https://www.c64-wiki.com/wiki/Indirect-indexed_addressing
		if byte == 0x53:
			lower = self.mem.read(addr % 0x100)
			upper = self.mem.read((addr + 1) % 0x100)
			
			addr = (upper << 8) + lower
			addr += self.y
				
		# Shift value in memory
		old_data = self.mem.read(addr)
		self.mem.write(addr, old_data >> 1)
		new_data = self.mem.read(addr)

		if old_data & 0x01:
			self.flag.set(Flag.C)
			
		# Exec XOR
		self.acc ^= new_data
					
		if self.acc == 0:
			self.flag.set(Flag.Z)
		
		if self.acc >= 0x80:
			self.flag.set(Flag.N)
				
		return self.pc + instr[1], self.cycles + instr[2]