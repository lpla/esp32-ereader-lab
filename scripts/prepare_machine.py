"""Pin and build full CrossPoint C3 firmware without editing the user's checkout."""
import argparse,hashlib,json,subprocess,re
from pathlib import Path
from run_lab import ROOT,IMAGE

HEAD='223c20b4864da9e7ee400d8234f7544fbbe54b62'
SDK='aef1a6c89e36f331b2e1aacbbf7ce0debdeb732a'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
 p=argparse.ArgumentParser();p.add_argument('--package',action='store_true');a=p.parse_args()
 project=ROOT/'tools/crosspoint-machine'
 if not a.package:
  if not project.exists():subprocess.run(['git','clone','https://github.com/crosspoint-reader/crosspoint-reader.git',str(project)],check=True)
  subprocess.run(['git','checkout','--detach',HEAD],cwd=project,check=True)
  subprocess.run(['git','submodule','update','--init','freeink-sdk'],cwd=project,check=True)
  subprocess.run(['pio','run','-d',str(project),'-e','default'],check=True)
 for directory,expected in ((project,HEAD),(project/'freeink-sdk',SDK)):
  actual=subprocess.check_output(['git','rev-parse','HEAD'],cwd=directory,text=True).strip()
  if actual!=expected:raise ValueError('Source pin mismatch')
  dirty=subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=directory,text=True)
  if dirty:raise ValueError('Tracked source is modified')
 if (project/'platformio.local.ini').exists():raise ValueError('Unsupported local build overrides')
 build=project/'.pio/build/default';factory=build/'firmware.factory.bin'
 elf=build/'firmware.elf'
 elf_rel=elf.relative_to(ROOT)
 nm=subprocess.check_output(['docker','run','--rm','--network','none','-v',f'{ROOT}:/work',IMAGE,'riscv64-linux-gnu-nm','-C',str(elf_rel)],text=True)
 all_symbols={m[3]:int(m[1],16) for line in nm.splitlines() if (m:=re.match(r'^([0-9a-f]+)\s+([A-Za-z])\s+(.+)$',line))}
 required=json.loads((ROOT/'adapters/crosspoint-symbols.json').read_text())
 symbols={name:all_symbols[name] for name in required}
 layout=subprocess.check_output(['docker','run','--rm','--network','none','-v',f'{ROOT}:/work',IMAGE,'gdb-multiarch','-q','-nx','-batch','-ex',f'file {elf_rel}','-ex','ptype /o SdSpiCard','-ex','ptype /o freeink::FreeInkDisplay'],text=True)
 for offset,member in [(12,'m_curSector'),(16,'m_dedicatedSpi'),(17,'m_beginCalled'),(18,'m_csPin'),(19,'m_errorCode'),(20,'m_spiActive'),(21,'m_state'),(22,'m_status'),(23,'m_type'),(69,'_inverted'),(72,'displayWidth'),(74,'displayHeight'),(88,'frameBuffer')]:
  if not re.search(r'/\*\s*'+str(offset)+r'\s*\|[^\n]*\*/[^\n]*\b'+member+r';',layout):raise ValueError(f'Unsupported ABI member: {member}')
 data=factory.read_bytes()
 if len(data)>16*1024*1024:raise ValueError('Firmware exceeds physical flash')
 image=ROOT/'firmware/crosspoint-machine.bin';image.parent.mkdir(exist_ok=True)
 image.write_bytes(data+b'\xff'*(16*1024*1024-len(data)))
 manifest=dict(symbols=symbols,abi_layout_verified=True,crosspoint=HEAD,sdk=SDK,environment='default',factory_bytes=len(data),
               flash_bytes=image.stat().st_size,flash_sha256=digest(image),factory_sha256=digest(factory),
               elf_sha256=digest(build/'firmware.elf'),factory_prefix_preserved=image.read_bytes()[:len(data)]==data)
 (ROOT/'firmware/crosspoint-machine.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(json.dumps(manifest,indent=2))


if __name__=='__main__':main()
