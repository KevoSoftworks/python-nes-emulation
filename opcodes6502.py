# Source: http://www.6502.org/tutorials/6502opcodes.html

# Format: Mnemonic, Length, Cycles, Additional cycles if page boundary crossed
opcodes = {
	0x69: ("ADC", 2, 2, 0),
	0x65: ("ADC", 2, 3, 0),
	0x75: ("ADC", 2, 4, 0),
	0x6D: ("ADC", 3, 4, 0),
	0x7D: ("ADC", 3, 4, 1),
	0x79: ("ADC", 3, 4, 1),
	0x61: ("ADC", 2, 6, 0),
	0x71: ("ADC", 2, 5, 1),
	
	0x29: ("AND", 2, 2, 0),
	0x25: ("AND", 2, 3, 0),
	0x35: ("AND", 2, 4, 0),
	0x2D: ("AND", 3, 4, 0),
	0x3D: ("AND", 3, 4, 1),
	0x39: ("AND", 3, 4, 1),
	0x21: ("AND", 2, 6, 0),
	0x31: ("AND", 2, 5, 1),
	
	0x0A: ("ASL", 1, 2, 0),
	0x06: ("ASL", 2, 5, 0),
	0x16: ("ASL", 2, 6, 0),
	0x0E: ("ASL", 3, 6, 0),
	0x1E: ("ASL", 3, 7, 0),
	
	0x24: ("BIT", 2, 3, 0),
	0x2C: ("BIT", 3, 4, 0),
	
	0x10: ("BPL", 2, 2, 1),
	0x30: ("BMI", 2, 2, 1),
	0x50: ("BVC", 2, 2, 1),
	0x70: ("BVS", 2, 2, 1),
	0x90: ("BCC", 2, 2, 1),
	0xB0: ("BCS", 2, 2, 1),
	0xD0: ("BNE", 2, 2, 1),
	0xF0: ("BEQ", 2, 2, 1),
	
	0x00: ("BRK", 1, 7, 0),
	
	0xC9: ("CMP", 2, 2, 0),
	0xC5: ("CMP", 2, 3, 0),
	0xD5: ("CMP", 2, 4, 0),
	0xCD: ("CMP", 3, 4, 0),
	0xDD: ("CMP", 3, 4, 1),
	0xD9: ("CMP", 3, 4, 1),
	0xC1: ("CMP", 2, 6, 0),
	0xD1: ("CMP", 2, 5, 1),
	
	0xE0: ("CPX", 2, 2, 0),
	0xE4: ("CPX", 2, 3, 0),
	0xEC: ("CPX", 3, 4, 0),
	
	0xC0: ("CPY", 2, 2, 0),
	0xC4: ("CPY", 2, 3, 0),
	0xCC: ("CPY", 3, 4, 0),
	
	0xC6: ("DEC", 2, 5, 0),
	0xD6: ("DEC", 2, 6, 0),
	0xCE: ("DEC", 3, 6, 0),
	0xDE: ("DEC", 3, 7, 0),
	
	0x49: ("EOR", 2, 2, 0),
	0x45: ("EOR", 2, 3, 0),
	0x55: ("EOR", 2, 4, 0),
	0x4D: ("EOR", 3, 4, 0),
	0x5D: ("EOR", 3, 4, 1),
	0x59: ("EOR", 3, 4, 1),
	0x41: ("EOR", 2, 6, 0),
	0x51: ("EOR", 2, 5, 1),
	
	0x18: ("CLC", 1, 2, 0),
	0x38: ("SEC", 1, 2, 0),
	0x58: ("CLI", 1, 2, 0),
	0x78: ("SEI", 1, 2, 0),
	0xB8: ("CLV", 1, 2, 0),
	0xD8: ("CLD", 1, 2, 0),
	0xF8: ("SED", 1, 2, 0),
	
	0xE6: ("INC", 2, 5, 0),
	0xF6: ("INC", 2, 6, 0),
	0xEE: ("INC", 3, 6, 0),
	0xFE: ("INC", 3, 7, 0),
	
	0x4C: ("JMP", 3, 3, 0),
	0x6C: ("JMP", 3, 5, 0),
	
	0x20: ("JSR", 3, 6, 0),
	
	0xA9: ("LDA", 2, 2, 0),
	0xA5: ("LDA", 2, 3, 0),
	0xB5: ("LDA", 2, 4, 0),
	0xAD: ("LDA", 3, 4, 0),
	0xBD: ("LDA", 3, 4, 1),
	0xB9: ("LDA", 3, 4, 1),
	0xA1: ("LDA", 2, 6, 0),
	0xB1: ("LDA", 2, 5, 1),
	
	0xA2: ("LDX", 2, 2, 0),
	0xA6: ("LDX", 2, 3, 0),
	0xB6: ("LDX", 2, 4, 0),
	0xAE: ("LDX", 3, 4, 0),
	0xBE: ("LDX", 3, 4, 1),
	
	0xA0: ("LDY", 2, 2, 0),
	0xA4: ("LDY", 2, 3, 0),
	0xB4: ("LDY", 2, 4, 0),
	0xAC: ("LDY", 3, 4, 0),
	0xBC: ("LDY", 3, 4, 1),
	
	0x4A: ("LSR", 1, 2, 0),
	0x46: ("LSR", 2, 5, 0),
	0x56: ("LSR", 2, 6, 0),
	0x4E: ("LSR", 3, 6, 0),
	0x5E: ("LSR", 3, 7, 0),
	
	0xEA: ("NOP", 1, 2, 0),
	
	0x09: ("ORA", 2, 2, 0),
	0x05: ("ORA", 2, 3, 0),
	0x15: ("ORA", 2, 4, 0),
	0x0D: ("ORA", 3, 4, 0),
	0x1D: ("ORA", 3, 4, 1),
	0x19: ("ORA", 3, 4, 1),
	0x01: ("ORA", 2, 6, 0),
	0x11: ("ORA", 2, 5, 1),
	
	0xAA: ("TAX", 1, 2, 0),
	0x8A: ("TXA", 1, 2, 0),
	0xCA: ("DEX", 1, 2, 0),
	0xE8: ("INX", 1, 2, 0),
	0xA8: ("TAY", 1, 2, 0),
	0x98: ("TYA", 1, 2, 0),
	0x88: ("DEY", 1, 2, 0),
	0xC8: ("INY", 1, 2, 0),
	
	0x2A: ("ROL", 1, 2, 0),
	0x26: ("ROL", 2, 5, 0),
	0x36: ("ROL", 2, 6, 0),
	0x2E: ("ROL", 3, 6, 0),
	0x3E: ("ROL", 3, 7, 0),
	
	0x6A: ("ROR", 1, 2, 0),
	0x66: ("ROR", 2, 5, 0),
	0x76: ("ROR", 2, 6, 0),
	0x6E: ("ROR", 3, 6, 0),
	0x7E: ("ROR", 3, 7, 0),
	
	0x40: ("RTI", 1, 6, 0),
	
	0x60: ("RTS", 1, 6, 0),
	
	0xE9: ("SBC", 2, 2, 0),
	0xE5: ("SBC", 2, 3, 0),
	0xF5: ("SBC", 2, 4, 0),
	0xED: ("SBC", 3, 4, 0),
	0xFD: ("SBC", 3, 4, 1),
	0xF9: ("SBC", 3, 4, 1),
	0xE1: ("SBC", 2, 6, 0),
	0xF1: ("SBC", 2, 5, 1),
	
	0x85: ("STA", 2, 3, 0),
	0x95: ("STA", 2, 4, 0),
	0x8D: ("STA", 3, 4, 0),
	0x9D: ("STA", 3, 5, 0),
	0x99: ("STA", 3, 5, 0),
	0x81: ("STA", 2, 6, 0),
	0x91: ("STA", 2, 6, 0),
	
	0x9A: ("TXS", 1, 2, 0),
	0xBA: ("TSX", 1, 2, 0),
	0x48: ("PHA", 1, 3, 0),
	0x68: ("PLA", 1, 4, 0),
	0x08: ("PHP", 1, 3, 0),
	0x28: ("PLP", 1, 4, 0),
	
	0x86: ("STX", 2, 3, 0),
	0x96: ("STX", 2, 4, 0),
	0x8E: ("STX", 3, 4, 0),
	
	0x84: ("STY", 2, 3, 0),
	0x94: ("STY", 2, 4, 0),
	0x8C: ("STY", 3, 4, 0),
	
	# The following opcodes are considered illegal,
	# i.e. opcodes which are not defined in the MOS6502
	# documentation. Mnemonics, addresses and behaviour
	# are taken from the "NMOS 6510 Unintended Opcodes" PDF,
	# for which the opcodes and behaviours should be similar
	# to the 6502
	
	0x07: ("iSLO", 2, 5, 0),
	0x17: ("iSLO", 2, 6, 0),
	0x03: ("iSLO", 2, 8, 0),
	0x13: ("iSLO", 2, 8, 0),
	0x0F: ("iSLO", 3, 6, 0),
	0x1F: ("iSLO", 3, 7, 0),
	0x1B: ("iSLO", 3, 7, 0),
	
	0x27: ("iRLA", 2, 5, 0),
	0x37: ("iRLA", 2, 6, 0),
	0x23: ("iRLA", 2, 8, 0),
	0x33: ("iRLA", 2, 8, 0),
	0x2F: ("iRLA", 3, 6, 0),
	0x3F: ("iRLA", 3, 7, 0),
	0x3B: ("iRLA", 3, 7, 0),
	
	0x47: ("iSRE", 2, 5, 0),
	0x57: ("iSRE", 2, 6, 0),
	0x43: ("iSRE", 2, 8, 0),
	0x53: ("iSRE", 2, 8, 0),
	0x4F: ("iSRE", 3, 6, 0),
	0x5F: ("iSRE", 3, 7, 0),
	0x5B: ("iSRE", 3, 7, 0),
	
	0x67: ("iRRA", 2, 5, 0),
	0x77: ("iRRA", 2, 6, 0),
	0x63: ("iRRA", 2, 8, 0),
	0x73: ("iRRA", 2, 8, 0),
	0x6F: ("iRRA", 3, 6, 0),
	0x7F: ("iRRA", 3, 7, 0),
	0x7B: ("iRRA", 3, 7, 0),
	
	0x87: ("iSAX", 2, 3, 0),
	0x97: ("iSAX", 2, 4, 0),
	0x83: ("iSAX", 2, 6, 0),
	0x8F: ("iSAX", 3, 4, 0),
	
	0xA7: ("iLAX", 2, 3, 0),
	0xB7: ("iLAX", 2, 4, 0),
	0xA3: ("iLAX", 2, 6, 0),
	0xB3: ("iLAX", 2, 5, 1),
	0xAF: ("iLAX", 3, 4, 0),
	0xBF: ("iLAX", 3, 4, 1),
	
	0xC7: ("iDCP", 2, 5, 0),
	0xD7: ("iDCP", 2, 6, 0),
	0xC3: ("iDCP", 2, 8, 0),
	0xD3: ("iDCP", 2, 8, 0),
	0xCF: ("iDCP", 3, 6, 0),
	0xDF: ("iDCP", 3, 7, 0),
	0xDB: ("iDCP", 3, 7, 0),
	
	0xE7: ("iISC", 2, 5, 0),
	0xF7: ("iISC", 2, 6, 0),
	0xE3: ("iISC", 2, 8, 0),
	0xF3: ("iISC", 2, 8, 0),
	0xEF: ("iISC", 3, 6, 0),
	0xFF: ("iISC", 3, 7, 0),
	0xFB: ("iISC", 3, 7, 0),
	
	0x0B: ("iANC", 2, 2, 0),
	0x2B: ("iANC", 2, 2, 0),
	
	0x4B: ("iALR", 2, 2, 0),
	
	0x6B: ("iARR", 2, 2, 0),
	
	0xCB: ("iSBX", 2, 2, 0),
	
	0xEB: ("iSBC", 2, 2, 0),
	
	0xBB: ("iLAS", 3, 4, 1),
	
	0x1A: ("iNOP", 1, 2, 0),
	0x3A: ("iNOP", 1, 2, 0),
	0x5A: ("iNOP", 1, 2, 0),
	0x7A: ("iNOP", 1, 2, 0),
	0xDA: ("iNOP", 1, 2, 0),
	0xFA: ("iNOP", 1, 2, 0),
	0x80: ("iNOP", 2, 2, 0),
	0x82: ("iNOP", 2, 2, 0), # Might JAM
	0xC2: ("iNOP", 2, 2, 0), # Might JAM
	0xE2: ("iNOP", 2, 2, 0), # Might JAM
	0x89: ("iNOP", 2, 2, 0),
	0x04: ("iNOP", 2, 3, 0),
	0x44: ("iNOP", 2, 3, 0),
	0x64: ("iNOP", 2, 3, 0),
	0x14: ("iNOP", 2, 4, 0),
	0x34: ("iNOP", 2, 4, 0),
	0x54: ("iNOP", 2, 4, 0),
	0x74: ("iNOP", 2, 4, 0),
	0xD4: ("iNOP", 2, 4, 0),
	0xF4: ("iNOP", 2, 4, 0),
	0x0C: ("iNOP", 3, 4, 0),
	0x1C: ("iNOP", 3, 4, 1),
	0x3C: ("iNOP", 3, 4, 1),
	0x5C: ("iNOP", 3, 4, 1),
	0x7C: ("iNOP", 3, 4, 1),
	0xDC: ("iNOP", 3, 4, 1),
	0xFC: ("iNOP", 3, 4, 1),
	
	0x02: ("iJAM", 1, 0, 0),
	0x12: ("iJAM", 1, 0, 0),
	0x22: ("iJAM", 1, 0, 0),
	0x32: ("iJAM", 1, 0, 0),
	0x42: ("iJAM", 1, 0, 0),
	0x52: ("iJAM", 1, 0, 0),
	0x62: ("iJAM", 1, 0, 0),
	0x72: ("iJAM", 1, 0, 0),
	0x92: ("iJAM", 1, 0, 0),
	0xB2: ("iJAM", 1, 0, 0),
	0xD2: ("iJAM", 1, 0, 0),
	0xF2: ("iJAM", 1, 0, 0)
	
}