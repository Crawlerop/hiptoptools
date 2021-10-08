import os
import zlib
import typing
import struct
import sys
import io

def rgb565toi24(data):
	from io import BytesIO
	offset = 0
	outp = BytesIO()
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

if __name__ == "__main__":
    f_desc = open(sys.argv[1], "rb")
    assert f_desc.read(8) == b"\x89\x50\x4E\x47\x0D\x0A\x1A\x0A"
    output = bytearray(b"\x89\x50\x4E\x47\x0D\x0A\x1A\x0A")

    DPLT_FOUND = False
    DPLT_COLORS = 0

    while True:
        chunk_name, chunk_data = read_png_packet(f_desc)        
        if chunk_name == "DpLT": # Dagger Hiptop exclusive
            DPLT_FOUND = True
            DPLT_COLORS = int(len(chunk_data)/2)
            output += write_png_packet("PLTE", rgb565toi24(chunk_data))            
        elif chunk_name == "tRNS":
            if DPLT_FOUND:
                output += write_png_packet(chunk_name, chunk_data[:DPLT_COLORS])
            else:
                output += write_png_packet(chunk_name, chunk_data)
        elif chunk_name == "IDAT":
            output += write_itxt_packet("Converter", "Danger Hiptop PNG Image Converter")            
            output += write_png_packet(chunk_name, chunk_data)
        else:
            output += write_png_packet(chunk_name, chunk_data)

        if chunk_name == "IEND":
            break

    if DPLT_FOUND: # Convert to common PNG
        open(sys.argv[2], "wb").write(output)
        #if os.system(f"pngcheck.win64.exe -vv {sys.argv[2]}") != 0: input()
    else: # No action needed
        f_desc.seek(0)
        open(sys.argv[2], "wb").write(f_desc.read())