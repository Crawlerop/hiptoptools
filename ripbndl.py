import sys
import struct
import os
import zlib
import io

if __name__ == "__main__":
    fd = open(sys.argv[1], "rb")
    assert fd.read(4) == b"BNDL"
    version = fd.read(2).decode("ascii")
    fd.read(2)
    assert struct.unpack("<L", fd.read(4))[0] == os.path.getsize(sys.argv[1])
    fd.read(0x24)

    bndl_name = fd.read(0x40).replace(b"\0", b"").decode("ascii")
    bndl_build = fd.read(0x20).replace(b"\0", b"").decode("ascii")
    fd.read(0x20)

    print(f"BNDL Name: {bndl_name}")
    print(f"BNDL Build: {bndl_build}")

    assert fd.read(4) == b"MAIN"
    b_size = struct.unpack("<L", fd.read(4))[0]
    compression = fd.read(4)
    fd.read(4)

    assert fd.read(4) == b"RSRC"
    r_size = struct.unpack("<L", fd.read(4))[0]
    compression_res = fd.read(4)
    fd.read(4)
    
    fd.read(0x30)

    if version != "V1":
        fd.read(0xc if b_size else 0x8)

    if b_size >= 1:
        if compression == b"ZLIB":
            open(f"{sys.argv[1]}.app", "wb").write(zlib.decompress(fd.read(b_size)))
        elif compression == b"NONE":
            open(f"{sys.argv[1]}.app", "wb").write(fd.read(b_size))
    
    bndl_io = None    

    if r_size >= 1:
        if compression_res == b"ZLIB":
            bndl_io = io.BytesIO(zlib.decompress(fd.read(r_size)))
        elif compression_res == b"NONE":
            bndl_io = io.BytesIO(fd.read(r_size))

    bndl_id = 1
    bndl_io_size = len(bndl_io.getvalue())
    while bndl_io.tell()<bndl_io_size:
        prev_offset = bndl_io.tell()        
        bndl_io.read(0x8)
        bndl_size = struct.unpack("<L", bndl_io.read(4))[0]
        bndl_io.seek(prev_offset)
        open(f"{sys.argv[1]}_{bndl_id}.rdb", "wb").write(bndl_io.read(bndl_size))
        #print(bndl_id)
        #os.system(f"python ../riprdb.py {sys.argv[1]}_{bndl_id}.rdb")
        bndl_id += 1