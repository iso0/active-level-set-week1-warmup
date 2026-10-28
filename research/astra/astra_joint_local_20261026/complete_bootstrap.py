from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'astra_local_correction_20261024'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf8')
c=json.loads((ROOT/'CAMPAIGN.json').read_text());manifest=[]
for dst in (ROOT/'source_snapshot/previous').rglob('*'):
    if dst.is_file():
        src=OLD/dst.relative_to(ROOT/'source_snapshot/previous');assert sha(src)==sha(dst)
        manifest.append({'source':str(src),'copy':str(dst.relative_to(ROOT)),'sha256':sha(dst)})
for src in sorted((OLD/'results').glob('unit__dev_v1_*.json')):
    obj=json.loads(src.read_text())
    if 'family' not in obj:continue
    uid=obj['id'];dest=ROOT/'data/dev'/uid;dest.mkdir(parents=True,exist_ok=True)
    for source,name in [(src,'parent.json'),(OLD/'results/dev_v1'/uid/'world.npz','world.npz')]:
        dst=dest/name
        if dst.exists():assert sha(dst)==sha(source)
        else:shutil.copyfile(source,dst)
        manifest.append({'source':str(source),'copy':str(dst.relative_to(ROOT)),'sha256':sha(dst)})
write(ROOT/'source_snapshot/PREVIOUS_MANIFEST.json',manifest)
for name in ['control.py','queue_store.py','resources.py','run_queue.py']:
    if not (ROOT/name).exists():shutil.copyfile(ROOT/'source_snapshot/previous'/name,ROOT/name)
write(ROOT/'AUTO_RESUME_RECEIPT.json',{'status':'PENDING_NEW_BINDING','campaign_id':ROOT.name,'reused_verified_evidence':'source_snapshot/previous/AUTO_RESUME_RECEIPT.json','actual_new_scheduled_chat_probes':[],'actual_quota_reset_takeover_observed':False,'simulated_quota_test':'Historical software test PASS; not actual quota exhaustion','new_windows_task_read_write':False})
(ROOT/'NEXT_ACTION.md').write_text('Verify new-target local read/write, create owned hourly same-chat heartbeat, finish model/protocol and independent references; freeze before comparisons. Do not reopen old queues.\n',encoding='utf8')
(ROOT/'EVENTS.jsonl').write_text(json.dumps({'utc':c['started_utc'],'event':'CAMPAIGN_STARTED','deadline_utc':c['deadline_utc'],'prior_campaign_closed':True})+'\n'+json.dumps({'event':'BOOTSTRAP_REPAIRED','reason':'Reference unit has no family/id; filtered metadata, no numerical computation occurred; original start preserved.'})+'\n',encoding='utf8')
(ROOT/'.gitignore').write_text('.venv/\n__pycache__/\n*.pyc\nruntime/*.lck\nruntime/logs/\n*.tmp\n',encoding='utf8')
print(json.dumps({'copied_files':len(manifest),'dev_paths':len(list((ROOT/'data/dev').glob('*/parent.json'))),'deadline_utc':c['deadline_utc']}))
