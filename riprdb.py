import sys
import struct
import os
import typing
import io
import csv
import zlib

RES_STRING = 1
RES_BITMAP = 2
RES_WAVE = 3
RES_SEQ = 4
RES_INT = 5
RES_MENU = 7
RES_STRTABLE = 8
RES_ALERT = 9
RES_DIALOG = 10
RES_SCREEN = 11
RES_STRINGARRAY = 12
RES_BITMAPS = 13
RES_RINGTONES = 14
RES_INPUTS = 15
RES_SPLASH = 16
RES_JAVA = 17
RES_CONTAINER = 18

RES_TYPES = {	
    1:"Strings",
	2:"Bitmaps",
	3:"Wave",
	4:"MIDI/RMF",
	5:"Integer",
	7:"Menu",
	8:"String Table",
	9:"Alert",
	10:"Dialog",
	11:"Screen",		
	12:"String Array",
	13:"Bitmap Array",
	14:"Ringtones",	
	15:"Text Inputs",
    16:"Splash Screen",
	17:"Java Files",
	18:"Container"
}

''' LZSS Decompression Routine '''

P = 1
N = 4096
F = 18
THRESHOLD = 2

NIL = N

def lzss_decompress(input: typing.Union[bytes, bytearray]):
    input_buf = io.BytesIO(input)
    output_buf = bytearray()
    
    flags = 0
    r = N - F
    text_buf = bytearray(N+F-1)

    for i in range(N-F):
        text_buf[i] = 0x20    
    
    input_bit = b""

    while True:
        flags >>= 1
        if ((flags) & 256) == 0:
            input_bit = input_buf.read(1)
            if input_bit == b"": break
            flags = input_bit[0] | 0xff00
        if flags & 1:
            input_bit = input_buf.read(1)
            if input_bit == b"": break
            output_buf += input_bit

            text_buf[r] = input_bit[0]
            
            r += 1
            r &= (N - 1)
        else:            
            input_bit = input_buf.read(1)
            if input_bit == b"": break
            i = struct.unpack("<B", input_bit)[0]

            input_bit = input_buf.read(1)
            if input_bit == b"": break
            j = struct.unpack("<B", input_bit)[0]

            i |= (j & 0xf0) << 4
            j = (j & 0x0f) + THRESHOLD

            k = 0
            while k <= j:
                input_bit = struct.pack("<B", text_buf[(i + k) & (N - 1)])
                output_buf += input_bit   
                text_buf[r] = input_bit[0]

                r += 1
                r &= (N - 1)
                k += 1

    return output_buf

''' End LZSS Decompression '''

''' DPLT Conversion Routines '''

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

def DPLT_Convert(input: typing.Union[bytes, bytearray]):
    f_desc = io.BytesIO(input)
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
            output += write_itxt_packet("Tool", "Hiptop RDB Extractor")            
            output += write_png_packet(chunk_name, chunk_data)
        else:
            output += write_png_packet(chunk_name, chunk_data)

        if chunk_name == "IEND":
            break

    if DPLT_FOUND: # Convert to common PNG
        return output
        #if os.system(f"pngcheck.win64.exe -vv {sys.argv[2]}") != 0: input()
    else: # No action needed
        return input

''' end DPLT Conversion '''

if __name__ == "__main__":
    fd = open(sys.argv[1], "rb")
    assert fd.read(4) == b"J4FF"
    fd.read(0xc)    
    num_res = struct.unpack("<L", fd.read(4))[0]
    #print(num_res)

    extracted_path = f"{sys.argv[1]}_extracted/"   
    os.makedirs(extracted_path, exist_ok=True) 
    
    for _ in range(num_res):
        
        PATH_STR = ""
        STR_WRITER = None                

        res_type = struct.unpack("<L", fd.read(4))[0]
        res_count = struct.unpack("<L", fd.read(4))[0]        

        '''
        print(f"Resource Type: {RES_TYPES[res_type]}")
        print(f"Resource Count: {res_count}")
        '''

        if res_type == RES_STRING:            
            STR_WRITER = csv.DictWriter(open(f"{extracted_path}/strings.csv", "w", encoding="utf-8", newline="\x0a"), fieldnames=["id","string"])
            STR_WRITER.writeheader()

        elif res_type == RES_BITMAP:
            PATH_STR = "Bitmaps"

        elif res_type == RES_WAVE:
            PATH_STR = "Waves"

        elif res_type == RES_SEQ:
            PATH_STR = "Sequences"

        elif res_type == RES_INT:            
            STR_WRITER = csv.DictWriter(open(f"{extracted_path}/integers.csv", "w", newline="\x0a"), fieldnames=["id","integer"])
            STR_WRITER.writeheader()    

        elif res_type == RES_MENU:
            PATH_STR = "Menus"      

        elif res_type == RES_STRTABLE:
            PATH_STR = "StringTables"

        elif res_type == RES_ALERT:
            PATH_STR = "Alerts"

        elif res_type == RES_DIALOG:
            PATH_STR = "Dialogs"

        elif res_type == RES_SCREEN:
            PATH_STR = "Screens"      

        elif res_type == RES_STRINGARRAY:
            PATH_STR = "StringArrays"

        elif res_type == RES_BITMAPS:
            PATH_STR = "BitmapArrays"
        
        elif res_type == RES_RINGTONES:
            PATH_STR = "RingtoneTables"

        elif res_type == RES_INPUTS:
            PATH_STR = "AlertInputs"

        elif res_type == RES_SPLASH:
            PATH_STR = "Splash"

        else:
            PATH_STR = f"Misc_{res_type}"

        if PATH_STR:
            os.makedirs(f"{extracted_path}/{PATH_STR}/", exist_ok=True)

        for _ in range(res_count):
            res_id = struct.unpack("<l", fd.read(4))[0]

            res_size = struct.unpack("<L", fd.read(4))[0]
            res_offset = struct.unpack("<L", fd.read(4))[0]
            res_data = bytearray()

            res_compressed = res_size >= 0x1000000
            
            if res_compressed:
                res_size -= 0x1000000

            '''
            print(f"Resource Type: {RES_TYPES[res_type]}")
            print("")
            print(f"Resource ID: {res_id}")
            print(f"Resource Size: {res_size}")
            print(f"Resource Offset: {res_offset}")
            print(f"LZSS-Compressed Resource: {res_compressed}")
            print("")
            '''
            
            prev_offset = fd.tell()
            fd.seek(res_offset)
            res_data += fd.read(res_size)            

            if res_compressed:
                res_data = lzss_decompress(res_data[8:])

            if res_type == RES_STRING:
                STR_WRITER.writerow({"id":res_id,"string":res_data.decode("utf-8").replace("\x0a","\x0d\x0a")})                
            
            elif res_type == RES_BITMAP:
                if res_data[:4] == b"\x89PNG":
                    open(f"{extracted_path}/{PATH_STR}/{res_id}.png", "wb").write(DPLT_Convert(res_data))
                else:
                    open(f"{extracted_path}/{PATH_STR}/{res_id}.img", "wb").write(res_data)

            elif res_type == RES_WAVE:
                if res_data[:4] == b"RIFF" and res_data[8:0x10] == b"WAVEfmt ":
                    open(f"{extracted_path}/{PATH_STR}/{res_id}.wav", "wb").write(res_data)
                elif res_data[:3] == b"ID3" or res_data[:2] in [b"\xff\xfb", b"\xff\xf3", b"\xff\xe3"]:
                    open(f"{extracted_path}/{PATH_STR}/{res_id}.mp3", "wb").write(res_data)
                else:
                    open(f"{extracted_path}/{PATH_STR}/{res_id}.snd", "wb").write(res_data)

            elif res_type == RES_SEQ:
                if res_data[:4] == b"MThd":
                    open(f"{extracted_path}/{PATH_STR}/{res_id}.mid", "wb").write(res_data)
                elif res_data[:4] == b"IREZ":
                    open(f"{extracted_path}/{PATH_STR}/{res_id}.rmf", "wb").write(res_data)
                elif res_data[:4] == b"XMF_":
                    open(f"{extracted_path}/{PATH_STR}/{res_id}.mxmf", "wb").write(res_data)
                else:
                    open(f"{extracted_path}/{PATH_STR}/{res_id}.seq", "wb").write(res_data)

            elif res_type == RES_INT:
                STR_WRITER.writerow({"id":res_id,"integer":struct.unpack("<l", res_data)[0]})                
            
            elif res_type == RES_STRINGARRAY or res_type == RES_BITMAPS:
                array_data = io.BytesIO(res_data)
                array_length = struct.unpack("<L", array_data.read(4))[0]     

                if res_type == RES_STRINGARRAY:
                    STR_WRITER = csv.DictWriter(open(f"{extracted_path}/{PATH_STR}/{res_id}.csv", "w", newline="\x0a", encoding="utf-8"), fieldnames=["id","string"])
                    STR_WRITER.writeheader()

                for i in range(array_length):
                    index_size = struct.unpack("<L", array_data.read(4))[0]
                    index_data = array_data.read(index_size)
                    
                    if res_type == RES_STRINGARRAY:
                        STR_WRITER.writerow({"id": i+1, "string": index_data.decode("utf-8")})
                    elif res_type == RES_BITMAPS:
                        if index_data[:4] == b"\x89PNG":
                            open(f"{extracted_path}/{PATH_STR}/{res_id}_{i+1}.png", "wb").write(DPLT_Convert(index_data))
                        else:
                            open(f"{extracted_path}/{PATH_STR}/{res_id}_{i+1}.img", "wb").write(index_data)

            elif PATH_STR:
                open(f"{extracted_path}/{PATH_STR}/{res_id}.dat", "wb").write(res_data)

            '''
            print("Resource Data: ")
            print(res_data)
            print("")
            '''

            fd.seek(prev_offset)

        if res_type == RES_STRING:
            del STR_WRITER 
            