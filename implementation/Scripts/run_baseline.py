"""Build and test the C host programs on Windows, macOS, or Linux."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', help='GCC/Clang executable name or complete path, without flags')
    parser.add_argument('--sanitize', choices=['none','undefined','address'], default='none')
    args = parser.parse_args()
    requested = args.cc or os.environ.get('CC')
    cc = shutil.which(requested) if requested else shutil.which('cc') or shutil.which('gcc') or shutil.which('clang')
    if not cc:
        parser.error('Install a C17 GCC or Clang compiler; use --cc with its executable path.')
    (ROOT/'Runs').mkdir(exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-'),dir=ROOT/'Runs'))
    build = run/'Build'
    build.mkdir()
    report = {'platform':platform.platform(), 'python':sys.version, 'compiler':cc,
              'sanitizer':args.sanitize, 'checks':[], 'status':'INCOMPLETE',
              'scope':'Host C tests only. ARM, Renode, tank feedback, timing and authentication NOT RUN.'}
    def execute(label, command, expected=0, required=None, timeout=30):
        result = subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
        (run/(label+'.stdout.txt')).write_text(result.stdout,encoding='utf-8')
        (run/(label+'.stderr.txt')).write_text(result.stderr,encoding='utf-8')
        ok = result.returncode == expected and (required is None or required in result.stdout)
        report['checks'].append({'id':label,'command':[str(x) for x in command], 'expected_exit':expected,'actual_exit':result.returncode,'passed':ok})
        if not ok:
            raise RuntimeError(f'{label} failed: expected {expected}, got {result.returncode}. See {run}')
        return result.stdout
    try:
        report['compiler_version'] = execute('compiler_version',[cc,'--version'])
        flags = ['-std=c17','-Wall','-Wextra','-Werror','-Wconversion','-Wshadow','-Wstrict-prototypes','-Wpedantic','-O1','-g','-ISource/include']
        if args.sanitize != 'none':
            checks = 'undefined,bounds' if args.sanitize == 'undefined' else 'address,undefined'
            flags += ['-fsanitize='+checks,'-fno-sanitize-recover=all','-fno-omit-frame-pointer']
        exe = {}
        for name in ['scenario','sequence']:
            exe[name] = build/(name+('-runner.exe' if os.name == 'nt' else '-runner'))
            execute('build_'+name,[cc]+flags+['Source/host/'+name+'_runner.c','Source/src/controller.c','-o',str(exe[name])],timeout=60)
        execute('original_15',[str(exe['scenario']),'Source/scenarios/control.csv'],required='PASS: 15 ')
        count = sum(1 for line in (ROOT/'Test_Data/Control/boundaries.csv').read_text().splitlines() if line and not line.startswith('#'))
        execute('boundaries',[str(exe['scenario']),'Test_Data/Control/boundaries.csv'],required=f'PASS: {count} ')
        execute('sequence',[str(exe['sequence']),'Test_Data/Control/sequence.csv'],required='PASS: 18 ')
        manifest = json.loads((ROOT/'Test_Data/Parser/manifest.json').read_text())
        for case in manifest:
            execute('parser_'+Path(case['file']).stem,[str(exe['scenario']),'Test_Data/Parser/'+case['file']],case['expected_exit'])
        execute('missing_file',[str(exe['scenario']),'Test_Data/does-not-exist.csv'],2)
        execute('missing_argument',[str(exe['scenario'])],2)
        execute('extra_argument',[str(exe['scenario']),'Source/scenarios/control.csv','extra'],2)
        report['status']='PASS'
        report['control_cases']=15+count
        report['sequence_steps']=18
        report['parser_files']=len(manifest)
    except (OSError,subprocess.TimeoutExpired,RuntimeError) as error:
        report['status']='FAIL'
        report['error']=str(error)
    report['source_and_data_sha256']={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in ['Source','Test_Data','Scripts'] for p in sorted((ROOT/folder).rglob('*'))
        if p.is_file() and '__pycache__' not in p.parts and 'build' not in p.parts}
    (run/'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(report['status']+': '+report['scope'])
    print('Results: '+str(run))
    if report['status'] != 'PASS':
        print(report.get('error','Test failed'),file=sys.stderr)
        return 1
    print(f"{report['control_cases']} independent cases; 18 sequence steps; {len(manifest)} parser fixtures; 3 invocation errors.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
