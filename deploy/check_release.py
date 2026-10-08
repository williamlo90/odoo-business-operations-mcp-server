"""Freeze/check the local delivery manifest from Git index blobs; no network calls."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = 'docs/evidence/phase9-manifest.json'
APPLICATION = 'e42441aee2b06483e7158f8ccc4ecc0e632a6041'
PREFIXES = ('backend/','client/','mcp-server/','odoo/','contracts/','skills/')


def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify_files(files):
    for path, expected in files.items():
        if digest(git('show',':'+path)) != expected:
            raise ValueError('release_file_changed:'+path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze',action='store_true',help='Create delivery manifest after staging the complete delivery pack')
    args = parser.parse_args()
    paths = [x for x in git('ls-files','-z').decode().split('\0') if x and x!=MANIFEST]
    if git('diff','--name-only','--',*paths).strip():
        raise ValueError('unstaged_release_changes')
    files = {path:digest(git('show',':'+path)) for path in paths}
    application = [path for path in paths if path.startswith(PREFIXES)]
    for path in application:
        if digest(git('show',APPLICATION+':'+path)) != files[path]:
            raise ValueError('application_changed_since_qualification:'+path)
    demo = json.loads((ROOT/'docs/demo/recording.json').read_text())
    assert demo['passed'] and demo['application_revision']==APPLICATION
    assert demo['ledger_count']==demo['order_count']==1 and len(demo['events'])==9
    cloud = json.loads((ROOT/'deploy/azure/plan.json').read_text())
    assert cloud['provisioning_enabled'] is False and cloud['budget_approved'] is False
    prior = json.loads((ROOT/'docs/evidence/phase8-manifest.json').read_text())
    if args.freeze:
        manifest = {'phase':9,'release_tag':'phase-9-delivery','status':'local-delivery-complete-cloud-design-only',
                    'created_at':datetime.now(timezone.utc).isoformat(),'application_revision':APPLICATION,
                    'hash_basis':'SHA-256 of Git index blob bytes; manifest itself excluded',
                    'qualified_runtime_images':prior['runtime_images'],
                    'application_files_unchanged':len(application),'demo_stages':9,
                    'qualification':'Phase 8 evidence applies to unchanged application code; Phase 9 CLI demo is a separate connected run',
                    'files':files}
        (ROOT/MANIFEST).write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    manifest = json.loads((ROOT/MANIFEST).read_text())
    assert set(manifest['files'])==set(files)
    verify_files(manifest['files'])
    print(json.dumps({'passed':True,'files_checked':len(files),'unchanged_application_files':len(application),
                      'demo_stages':9,'cloud_provisioned':False}))


if __name__=='__main__':
    main()
