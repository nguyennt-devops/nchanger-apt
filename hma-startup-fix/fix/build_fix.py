"""Build the ARM64 compatibility shim and add its dependency to a framework copy."""
import hashlib
import json
import struct
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
ORIGINAL_SHA256="1b092b0e3fbe1d5f8837d08f7241aea195aec27fc3d01d857acfbf799abb8f0a"
DEPENDENCY="@loader_path/HmaGoHeapFix.dylib"


def add_dependency(data, name):
    data=bytearray(data)
    magic,cpu,sub,typ,ncmds,sizeofcmds,flags,reserved=struct.unpack_from('<8I',data)
    if magic!=0xfeedfacf or cpu!=0x100000c:
        raise ValueError('Expected thin ARM64 Mach-O')
    end=32+sizeofcmds
    first_section=len(data)
    offset=32
    for _ in range(ncmds):
        cmd,size=struct.unpack_from('<II',data,offset)
        if size<8 or offset+size>end:raise ValueError('Invalid load command')
        if cmd==0xc:
            nameoff=struct.unpack_from('<I',data,offset+8)[0]
            old=data[offset+nameoff:offset+size].split(b'\0',1)[0].decode()
            if old==name:raise ValueError('Dependency already present')
        if cmd==25:
            nsects=struct.unpack_from('<I',data,offset+64)[0]
            for index in range(nsects):
                section=offset+72+index*80
                fileoff=struct.unpack_from('<I',data,section+48)[0]
                if fileoff:first_section=min(first_section,fileoff)
        offset+=size
    if offset!=end:raise ValueError('Load command sizes do not match header')
    size=(24+len(name.encode())+1+7)&~7
    if end+size>first_section or any(data[end:end+size]):
        raise ValueError('Insufficient zero header padding; refusing to move existing data')
    command=struct.pack('<6I',0xc,size,24,0,0x10000,0x10000)+name.encode()+b'\0'
    data[end:end+size]=command.ljust(size,b'\0')
    struct.pack_into('<II',data,16,ncmds+1,sizeofcmds+size)
    return bytes(data),{'offset':end,'size':size,'firstSection':first_section,'dependency':name}


def main():
    source=ROOT/'HMASecureVPN.app/Frameworks/MimicNetworking.framework/MimicNetworking'
    data=source.read_bytes()
    if hashlib.sha256(data).hexdigest()!=ORIGINAL_SHA256:
        raise ValueError('Original framework hash mismatch; refusing to patch')
    output=ROOT/'artifacts/fix-build';output.mkdir(exist_ok=True)
    dylib=output/'HmaGoHeapFix.dylib'
    cmd=[sys.executable,'-m','ziglang','cc','-target','aarch64-ios.15.0','-dynamiclib','-nostdlib',
         '-fno-stack-protector','-O2','-Wl,-undefined,dynamic_lookup','-Wl,-install_name,@loader_path/HmaGoHeapFix.dylib',
         str(ROOT/'fix/HmaGoHeapFix.c'),'-o',str(dylib)]
    subprocess.run(cmd,check=True)
    patched,info=add_dependency(data,DEPENDENCY)
    (output/'MimicNetworking').write_bytes(patched)
    info.update({'originalSHA256':ORIGINAL_SHA256,'patchedSHA256':hashlib.sha256(patched).hexdigest(),
                 'shimSHA256':hashlib.sha256(dylib.read_bytes()).hexdigest(),'buildCommand':cmd})
    (output/'patch-manifest.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
    print(json.dumps(info,indent=2))


if __name__=='__main__':main()
