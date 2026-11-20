"""Build a rootless Debian package with only the shim and verified header delta."""
import gzip
import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path, PurePosixPath

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from fix.build_fix import add_dependency,DEPENDENCY,ORIGINAL_SHA256
IDENTIFIER='store.nguyennt.hmaheapfix'
VERSION='1.0.1'
ARCH='iphoneos-arm64'


def archive(files):
    buffer=io.BytesIO()
    with tarfile.open(fileobj=buffer,mode='w',format=tarfile.USTAR_FORMAT) as tar:
        directories=set()
        for name,_,_ in files:
            directories.update(str(p) for p in PurePosixPath(name).parents if str(p)!='.')
        for name in sorted(directories,key=lambda p:(p.count('/'),p)):
            info=tarfile.TarInfo('./'+name+'/')
            info.type=tarfile.DIRTYPE;info.mode=0o755;info.uid=info.gid=0;info.mtime=0
            tar.addfile(info)
        for name,data,mode in files:
            info=tarfile.TarInfo('./'+name)
            info.size=len(data);info.mode=mode;info.uid=info.gid=0;info.mtime=0
            tar.addfile(info,io.BytesIO(data))
    return gzip.compress(buffer.getvalue(),mtime=0)


def deb(members):
    result=bytearray(b'!<arch>\n')
    for name,data in members:
        header=f'{name+"/":<16}{0:<12}{0:<6}{0:<6}{"100644":<8}{len(data):<10}`\n'.encode()
        assert len(header)==60
        result+=header+data
        if len(data)%2:result+=b'\n'
    return bytes(result)


def main():
    original=(ROOT/'HMASecureVPN.app/Frameworks/MimicNetworking.framework/MimicNetworking').read_bytes()
    assert hashlib.sha256(original).hexdigest()==ORIGINAL_SHA256
    patched,change=add_dependency(original,DEPENDENCY)
    assert change['offset']==5832 and change['size']==56
    assert hashlib.sha256(patched).hexdigest()=='76aa2afe5d494622cc314476226be7b4a7a715e2e293858ae63538fe25e12792'
    helper=(ROOT/'artifacts/fix-build/signed/HmaGoHeapFix.dylib').read_bytes()
    prefix='var/jb/usr/libexec/hma-heap-fix/'
    files=[(prefix+'HmaGoHeapFix.dylib',helper,0o644),
           (prefix+'header-counts.bin',patched[16:24],0o644),
           (prefix+'load-command.bin',patched[5832:5888],0o644)]
    for name in ['install.sh','remove.sh']:
        files.append((prefix+name,(ROOT/'packaging'/name).read_bytes().replace(b'\r\n',b'\n'),0o755))
    files.append(('var/jb/usr/share/doc/'+IDENTIFIER+'/README.txt',
                  (ROOT/'packaging/README.txt').read_bytes().replace(b'\r\n',b'\n'),0o644))
    control=[]
    control.append(('control',(ROOT/'packaging/control').read_bytes().replace(b'\r\n',b'\n'),0o644))
    for name in ['preinst','postinst','prerm']:
        control.append((name,(ROOT/'packaging'/name).read_bytes().replace(b'\r\n',b'\n'),0o755))
    md5=''.join(hashlib.md5(data).hexdigest()+'  '+name+'\n' for name,data,_ in files)
    control.append(('md5sums',md5.encode(),0o644))
    payload=deb([('debian-binary',b'2.0\n'),('control.tar.gz',archive(control)),('data.tar.gz',archive(files))])
    out=ROOT/'dist';out.mkdir(exist_ok=True)
    path=out/f'{IDENTIFIER}_{VERSION}_{ARCH}.deb';path.write_bytes(payload)
    result={'file':path.name,'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest(),
            'originalFrameworkSHA256':ORIGINAL_SHA256,'unsignedPatchedFrameworkSHA256':hashlib.sha256(patched).hexdigest(),
            'helperSHA256':hashlib.sha256(helper).hexdigest(),'payloadFiles':[name for name,_,_ in files]}
    (out/'package-manifest.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
