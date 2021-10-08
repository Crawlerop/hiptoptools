import os
import sys
import struct

def main():
    if len(sys.argv) < 2:
        print("Not enough arguments")
        sys.exit(1)	
    ftmp = bytearray()
    inp = open(sys.argv[1], "rb")
    dtbuf = inp.read()
    while dtbuf != b"":
        ftmp += dtbuf
        dtbuf = inp.read()

    if not (os.path.exists(sys.argv[1] + "_ext_bndl")):  os.mkdir(sys.argv[1] + "_ext_bndl")

    offset = ftmp.find(b"BNDLV")	
    cnt = 0	
    while offset != -1:
        cnt += 1
        bndl_size = struct.unpack("<L", ftmp[offset+8:offset+0xc])[0]

        open(f"{sys.argv[1]}_ext_bndl/BNDL_{cnt}.bndl", "wb").write(ftmp[offset:offset+bndl_size])
        #os.system(f"python ../ripbndl.py {sys.argv[1]}_ext_bndl/BNDL_{cnt}.bndl")
        offset = ftmp.find(b"BNDLV", offset+1)	

if __name__ == "__main__":
	main()
