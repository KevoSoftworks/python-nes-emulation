import re

from opcodes6502 import opcodes
import cpu as processor

def format_log(cpu):
	return f"{cpu.pc:04X} A:{cpu.acc:02X} X:{cpu.x:02X} Y:{cpu.y:02X} P:{cpu.flag.get_byte():02X} SP:{cpu.sp:02X} CYC:{cpu.cycles}\n"

"""
    iNES format:
        16: Header
        0 | 512: Trainer
        16384 * x: PRG ROM
        8192 * y: CHR ROM
        ...
        
    Header format:
        b0 - b3: 0x4E 0x45 0x52 0x1A
        b4: PRG ROM x
        b5: CHR ROM y
        b6 - b10: Flags 6-10
    
    Flag 6 format:
        bit 0: (0)-horizontal mirroring; (1)-vertical mirroring
        bit 1: persistent memory
        bit 2: trainer
        bit 3: ignore mirror; use 4-screen VRAM
        bit 4-7: lower nibble of mapper no.
    Flag 7 format:
        bit 0: VS Unisystem
        bit 1: Playchoice (NES 2.0)
        bit 2-3: if 10, NES 2.0 format
        bit 4-7: upper nibble of mapper no.
    Flag 8:
        0-7: PRG RAM size
    Flag 9:
        0: (0)NTSC, (1): PAL
"""
def load_image(name):
	raw = []
	with open(name, 'rb') as file:
		raw = file.read()
		
	return raw

filename = "dk.nes"
raw = load_image(filename)

# Parse header data
const = raw[0:4]
prg_size = raw[4]
chr_size = raw[5]
flag_mirroring = raw[6] & 0b00000001
flag_persistent_mem = raw[6] & 0b00000010
flag_trainer = raw[6] & 0b00001000
flag_mirroring_ignore = raw[6] & 0b00001000
flag_vs_unisystem = raw[7] & 0b00000001
flag_playchoice = raw[7] & 0b00000010
flag_nes2 = raw[7] & 0b00001100
flag_mapper = (raw[7] & 0b11110000) << 4 + raw[6] & 0b11110000
flag_prg_ram_size = raw[8]
flag_tv_mode = raw[9] & 0b00000001

prg_start = 16 + flag_trainer * 512
prg_len = 16384 * prg_size

chr_start = prg_start + prg_len
chr_len = 8192 * chr_size

PRG = raw[prg_start:prg_start+prg_len]
CHR = raw[chr_start:chr_start+chr_len]

print(f"Header:\n", \
	  f"Header constant: {const.decode('UTF-8')}\n", \
	  f"Image type: {'NES 2.0' if flag_nes2 else 'iNES'}\n", \
	  f"PRG ROM Size: {prg_len/1024} KiB\n", \
	  f"CHR ROM Size: {chr_len/1024} KiB\n", \
	  f"PRG RAM Size: {flag_prg_ram_size/1024 if flag_prg_ram_size else 'n.a.'}\n",\
	  f"Persistent Memory: {'Yes' if flag_persistent_mem else 'No'}\n", \
	  f"Mirroring mode: {flag_mirroring}\n", \
	  f"Mapper: {flag_mapper} ")

if flag_mapper != 0:
	raise NotImplementedError("Only mapper 0 images are supported");

# Map memory
raw_mem = bytearray(0xFFFF+1)
raw_mem[0x8000:] = PRG
if prg_size == 1:
	raw_mem[0xC000:] = PRG
	
#raw_mem[0x2002] = 0x80 # Negative num for testing purposes

mem = processor.Memory(raw_mem)

cpu = processor.CPU(mem)
if filename == "nestest.nes":
	cpu.pc = 0xC000
	
#log = open("nestest.log", "r")

while True:
	"""raw_line = log.readline()
	logline = re.sub(r"^([0-9A-F]{4})(?:.*)(A\:[0-9A-F]{2}.*)(?:\sPPU.*CYC\:[0-9]*)", r"\1 \2", raw_line)
	curline = re.sub(" CYC:[0-9]*", "", format_log(cpu))
	
	if logline != curline:
		print("Log inconsistency")
		print("(PC, A, X, Y, Flags, Stack Pointer)")
		print("Got")
		print(curline)
		print("Expected")
		print(logline)
		break
	"""
	cpu.run()
	# loc = 0x00	# This is only required for the first n tests
	"""loc = 0x02

	if cpu.mem.read(loc) != 0x00 or cpu.mem.read(loc+1) != 0x00:
		print(f"----------Test error 0x{cpu.mem.read(loc):02X}, 0x{cpu.mem.read(loc+1):02X} ----------")
		cpu.mem.write(loc, 0)
		break
	"""
#log.close()

"""
nmi_vector = cpu_mem[0xFFFA] + (cpu_mem[0xFFFB] << 8)
reset_vector = cpu_mem[0xFFFC] + (cpu_mem[0xFFFD] << 8)
irq_vector = cpu_mem[0xFFFE] + (cpu_mem[0xFFFF] << 8)
print(f"Reset: {reset_vector:04x}")

with open("binary.txt", "w+") as file:
	pc = reset_vector
	while pc <= 0xFFFF:
		cur_opcode = opcodes[cpu_mem[pc]]
		line = f"({cpu_mem[pc]:02X}) {cur_opcode[0]}"
		
		if cur_opcode[1] > 1:
			line += " 0x" + "".join(format(x, "02X") for x in cpu_mem[pc+cur_opcode[1]-1:pc:-1])
			
		line += "\n"
		
		file.write(line)
		pc += cur_opcode[1]
"""