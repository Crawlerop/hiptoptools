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

    if not (os.path.exists(sys.argv[1] + "_ext_png")):  os.mkdir(sys.argv[1] + "_ext_png")


    offset = ftmp.find(b"IHDR")	
    cnt = 0	
    while offset != -1:
        cnt += 1
        nextifeg = ftmp.find(b"IEND", offset+1)
        if nextifeg == -1:
            nextifeg = None
        else:
            nextifeg += 8
        open(f"{sys.argv[1]}_ext_png/PNG_{cnt}.png", "wb").write(b"\x89\x50\x4E\x47\x0D\x0A\x1A\x0A"+ftmp[offset-4:nextifeg])
        offset = ftmp.find(b"IHDR", offset+1)	

if __name__ == "__main__":
	main()
