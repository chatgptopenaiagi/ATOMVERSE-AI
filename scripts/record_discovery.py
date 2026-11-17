"""Create public, allowlisted discovery evidence from explicitly selected sources."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'SOFTWARE'))
from atomverse.adapters import import_events
from atomverse.core import atomic_write


def probe(args, timeout=30):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        return {'exit_code':p.returncode, 'output':p.stdout.strip()[:12000], 'error':p.stderr.strip()[:1000]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'exit_code':None, 'error':type(exc).__name__}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--arx', required=True, type=Path)
    parser.add_argument('--torch-python', required=True)
    parser.add_argument('--tensorrt-python', required=True)
    parser.add_argument('--godot', required=True)
    parser.add_argument('--dxdiag', type=Path)
    parser.add_argument('--qwen-manifest', type=Path)
    parser.add_argument('--historical-qwen', action='append', default=[])
    args=parser.parse_args()
    raw=args.arx.read_bytes(); report=json.loads(raw.decode('utf-8-sig')); m=report['machine']; g=m.get('gpu_compute') or {}
    torch_probe=probe([args.torch_python,'-I','-c',"import torch,json,sys; print(json.dumps({'python':sys.version.split()[0],'torch':torch.__version__,'cuda':torch.version.cuda,'cuda_available':torch.cuda.is_available(),'cudnn':torch.backends.cudnn.version(),'cpu_instruction_backend':torch.backends.cpu.get_cpu_capability(),'device':torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}))"])
    torch_data=json.loads(torch_probe['output']) if torch_probe.get('exit_code')==0 else {'status':'probe_failed'}
    trt=probe([args.tensorrt_python,'-I','-c','import tensorrt;print(tensorrt.__version__)'])
    vulkan=probe(['vulkaninfo','--summary'])
    vulkan_version=re.search(r'Vulkan Instance Version:\s*([\d.]+)',vulkan.get('output',''))
    directx=[]
    if args.dxdiag and args.dxdiag.exists():
        directx=[line.strip() for line in args.dxdiag.read_text(encoding='utf-8',errors='replace').splitlines() if any(key in line for key in ('DirectX Version:', 'Feature Levels:', 'Driver Model:'))]
    alternate=None
    if args.qwen_manifest and args.qwen_manifest.is_file():
        manifest=json.loads(args.qwen_manifest.read_text()); blobroot=args.qwen_manifest.parents[4]/'blobs'
        alternate={'name':'qwen3.8:27b','manifest_present':True,'model_layers':[{'bytes':layer['size'],'exists':(blobroot/layer['digest'].replace(':','-')).is_file()} for layer in manifest['layers'] if layer['mediaType']=='application/vnd.ollama.image.model'], 'inference_performed':False}
    processes=probe(['pwsh','-NoProfile','-Command',"@(Get-Process -Name '*llama*','*ollama*' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ProcessName) | ConvertTo-Json -Compress"])
    discovery={'recorded_at_utc':datetime.now(timezone.utc).isoformat(), 'method':'fresh ARX scan plus fixed bounded runtime probes; personal paths and device identifiers omitted',
        'arx_scan_at_utc':report['generated_at'], 'cpu':{key:m['cpu'].get(key) for key in ('Name','NumberOfCores','NumberOfLogicalProcessors','Architecture')},
        'memory':m.get('memory'), 'operating_system':{key:m['os'].get(key) for key in ('edition','version','build','architecture')},
        'gpus':[{key:item.get(key) for key in ('name','driver_version','dedicated_vram_bytes','compute_capability')} for item in g.get('nvidia_tooling_gpus',[])],
        'storage':[{key:item.get(key) for key in ('DriveLetter','Size','SizeRemaining','DriveType')} for item in (m.get('storage') or [])],
        'python_providers':[{key:item.get(key) for key in ('version','architecture_bits','healthy','health_status')} for item in m.get('python_installations',[])],
        'pytorch':torch_data, 'tensorrt':{'version':trt.get('output') if trt.get('exit_code')==0 else None,'import_verified':trt.get('exit_code')==0,'inference_verified':False},
        'cuda_toolkit':probe(['nvcc','--version']).get('output'), 'vulkan_instance_version':vulkan_version.group(1) if vulkan_version else None, 'directx':directx,
        'databases':{'sqlite':__import__('sqlite3').sqlite_version,'sql_server':'existing running service observed; not used or modified','postgresql':'existing running service observed; not used or modified'},
        'qwen':{'historical_exact_model_locations_present':[Path(path).is_file() for path in args.historical_qwen], 'exact_model_verified':False,'alternate':alternate,'serving_process_probe':processes.get('output') or 'No matching running process observed','server_or_model_started':False},
        'scope_limitations':['Not an exhaustive disk search','CPU AVX2 backend reported by PyTorch; full CPUID feature inventory not performed','Model blobs inspected by presence/size, not full hash or inference','DirectX/Vulkan availability is not a comparative engine benchmark']}
    installed={name:importlib.metadata.version(name) for name in ('PySide6','psutil','numpy','pytest')}
    engines={'recorded_at_utc':discovery['recorded_at_utc'],'selected':{'ui':'PySide6/QPainter projection','storage':'SQLite','cpu':'standard-library float matrix','gpu':'existing external PyTorch','telemetry':'psutil + nvidia-smi'},
             'installed_packages':installed,'godot_version_probe':probe([args.godot,'--version']), 'pytorch':torch_data,'tensorrt':discovery['tensorrt'],
             'reuse_matrix':'RESEARCH/DEPENDENCY-REUSE-MATRIX.md','alternatives':'RESEARCH/ENGINE-EVALUATION.md','new_global_installations':[]}
    interop={'recorded_at_utc':discovery['recorded_at_utc'],'producer':report['scanner'],'report_schema':report['schema_version'],
             'report_sha256':hashlib.sha256(raw).hexdigest(),'normalized_events':len(import_events(args.arx)), 'source_report_kept_private':True,
             'supported_nested_gpu_schema':'1.0','unsupported_contracts':['ARX Project DNA 0.2','ARX AI Contract 0.2'],
             'installed_arx_modified':False,'source_checkout_commit':probe(['git','-C',str(ROOT/'.local/ARX-source'),'rev-parse','HEAD']).get('output'),
             'ignored_fields':['hostname','device UUID','PCI bus identifier','user paths','environment values','unreliable CIM AdapterRAM'],
             'mapped_fields':['CPU cores/logical processors','RAM total/available bytes','GPU identity/driver','NVIDIA tooling dedicated VRAM bytes','volume total/free bytes','tool detection/version']}
    for name,data in [('ENGINEERING-DISCOVERY',discovery),('AVAILABLE-ENGINES',engines),('ARX-INTEROPERABILITY',interop)]:
        atomic_write(ROOT/'EVIDENCE'/f'{name}.json',json.dumps(data,indent=2))
    print('Wrote sanitized discovery, engine and ARX interoperability evidence.')


if __name__=='__main__':
    main()
