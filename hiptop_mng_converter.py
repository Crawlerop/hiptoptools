import os
import zlib
import typing
import struct
import sys
import io

def rgb565toi24(data):
	offset = 0
	outp = io.BytesIO()
	while offset<len(data):
		inp = struct.unpack("<H", data[offset:offset+2])[0]
		rgb = ( ((inp & 0x001F) << 3), ((inp & 0x07E0) >> 3), ((inp & 0xF800) >> 8) )
		outp.write(struct.pack("<BBB", *rgb))
		offset += 2
	return outp.getvalue()

def write_png_packet(chunk: str,data: typing.Union[bytes,bytearray]):
    return struct.pack(">L", len(data))+chunk.encode("ascii")+data+struct.pack(">L", zlib.crc32(chunk.encode("ascii")+data))
    
def write_itxt_packet(cat: str, text: str):
    return write_png_packet("iTXt", cat.encode("ascii")+b"\0\0\0\0\0"+text.encode("ascii"))

def read_png_packet(fd: io.IOBase):
    chunk_size = struct.unpack(">L", fd.read(4))[0]
    chunk_name = fd.read(4).decode("ascii")
    chunk_data = fd.read(chunk_size)    
    assert struct.unpack(">L", fd.read(4))[0] == zlib.crc32(chunk_name.encode("ascii")+chunk_data)
    return (chunk_name, chunk_data)

FIX_RESOLUTION = True

if __name__ == "__main__":
    f_desc = open(sys.argv[1], "rb")
    assert f_desc.read(8) == b"\x8A\x4D\x4E\x47\x0D\x0A\x1A\x0A"
    output = bytearray(b"\x8A\x4D\x4E\x47\x0D\x0A\x1A\x0A")

    DPLT_FOUND = False
    DPLT_FOUND_COUNT = 0
    DPLT_COLORS = 0

    mhdr_data = b""

    FIRST_BASE = False

    while True:
        chunk_name, chunk_data = read_png_packet(f_desc) 
        if chunk_name == "MHDR":
            mhdr_data = chunk_data
            output += write_png_packet(chunk_name, chunk_data)
            output += write_itxt_packet("Converter", "Danger Hiptop MNG Image Converter")  

        elif chunk_name == "DpLT": # Dagger Hiptop exclusive
            DPLT_FOUND = True
            DPLT_COLORS = int(len(chunk_data)/2)
            DPLT_FOUND_COUNT += 1

            output += write_png_packet("PLTE", rgb565toi24(chunk_data))     

        elif chunk_name == "tRNS":
            if DPLT_FOUND:
                output += write_png_packet(chunk_name, chunk_data[:DPLT_COLORS])
            else:
                output += write_png_packet(chunk_name, chunk_data)
                
        elif chunk_name == "IHDR":
            if not FIRST_BASE and FIX_RESOLUTION:
                FIRST_BASE = True
                output[0x10:0x30] = write_png_packet("MHDR", chunk_data[:8]+mhdr_data[8:])[8:]
            output += write_png_packet(chunk_name, chunk_data)
        elif chunk_name == "IEND":                     
            DPLT_FOUND = False
            DPLT_COLORS = 0

            output += write_png_packet(chunk_name, chunk_data)
        else:
            output += write_png_packet(chunk_name, chunk_data)

        if chunk_name == "MEND":
            break

    if DPLT_FOUND_COUNT >= 1: # Convert to common MNG
        open(sys.argv[2], "wb").write(output)
        #if os.system(f"pngcheck.win64.exe -vv {sys.argv[2]}") != 0: input()
    else: # No action needed
        f_desc.seek(0)
        open(sys.argv[2], "wb").write(f_desc.read())