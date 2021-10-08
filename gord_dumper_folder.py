import sys
import struct
import os
import io
import zlib
import typing

''' MNG DPLT Conversion Routines '''

FIX_RESOLUTION = True

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

def DPLT_Convert_MNG(input: typing.Union[bytes, bytearray]):
    f_desc = io.BytesIO(input)
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
            output += write_itxt_packet("Tool", "Hiptop GORD Dumper") 

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
        return output
        #if os.system(f"pngcheck.win64.exe -vv {sys.argv[2]}") != 0: input()
    else: # No action needed
        return input

''' end MNG DPLT Conversion '''

if __name__ == "__main__":
    fd = open(sys.argv[1], "rb")
    assert fd.read(4) == b"GORD"
    assert struct.unpack("<L", fd.read(4))[0] == os.path.getsize(sys.argv[1])-0x18
    fd.read(0x10)
        
    gord_type = fd.read(4)
    gord_size = struct.unpack("<L", fd.read(4))[0]

    if gord_type == b"DBIN":
        open(sys.argv[2], "wb").write(fd.read(gord_size))
    elif gord_type == b"FACT":
        gord_fs = io.BytesIO(fd.read(gord_size))
        file_id = 1
        output = bytearray(gord_fs.read(0x30000))
        ext = "bin"
        out_check = False
        is_ZLIB = False

        IPATH = f"{sys.argv[1]}_extracted/"
        if not os.path.exists(IPATH): os.mkdir(IPATH)        
        while gord_fs.tell()<gord_size:                
            gord_fs.read(0xc)
            blk_size = struct.unpack("<L", gord_fs.read(4))[0]
            output += gord_fs.read(blk_size)
            if out_check:                    
                if output[:4] == b"\x8aMNG":
                    ext = "mng"
                elif output[:4] == b"IREZ":
                    ext = "rmf"
                elif output[:4] == b"ZLIB":
                    is_ZLIB = True
                elif output[:4] == b"BNDL":
                    ext = "bndl"
                elif output[:4] == b"J4FF":
                    ext = "rdb"     
                else:
                    ext = "bin"
                out_check = False
            
            padding_required = 0xff0-blk_size                
            gord_fs.read(padding_required)

            if blk_size < 0xff0:
                if is_ZLIB:
                    output = zlib.decompress(output[8:])
                    if output[:4] == b"\x8aMNG":
                        ext = "mng"
                    elif output[:4] == b"IREZ":
                        ext = "rmf"
                    elif output[:4] == b"BNDL":
                        ext = "bndl"
                    elif output[:4] == b"J4FF":
                        ext = "rdb"    
                    else:
                        ext = "bin"

                if ext == "rmf":                        
                    if output[-0x3f:].find(b"BANK") != -1:
                        ext = "hsb"

                if ext == "mng":
                    output = DPLT_Convert_MNG(output)        
                
                open(f"{IPATH}{file_id}.{ext}", "wb").write(output)
                file_id += 1
                output = b""
                out_check = True
                is_ZLIB = False
                    

            
    else:
        raise Exception(f"Unknown GORD type: {gord_type.decode('ascii')}")
