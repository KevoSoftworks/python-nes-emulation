"""
	Convert two's complement byte into a python integer
"""
def signed_byte_to_int(byte, byte_len):
	mask = 2**(byte_len - 1)
	return -(byte & mask) + (byte & ~mask)