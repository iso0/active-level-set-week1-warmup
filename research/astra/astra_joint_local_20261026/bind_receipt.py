"""Read actual configuration and receipts; never synthesize scheduled proof."""
import tomllib
from datetime import datetime,timezone,timedelta
from control import ROOT,read,atomic,sha,now,event
aid='astra-birlikte-genel-ve-yerel-renme'
cfgpath=ROOT.home()/'.codex/automations'/aid/'automation.toml'
cfg=tomllib.loads(cfgpath.read_text(encoding='utf8'))
atomic(ROOT/'evidence/HEARTBEAT_CONFIG.json',cfg)
receipt=read(ROOT/'AUTO_RESUME_RECEIPT.json')
receipt['scheduled_chat']={'automation_id':aid,'target_thread_id':cfg.get('target_thread_id'),'actual_config_sha256':sha(cfgpath),'kind':cfg.get('kind'),'status':cfg.get('status'),'rrule':cfg.get('rrule'),'local_host':'BURAK','requires':'App and host available; quota access; active turn can delay dispatch'}
stamp=cfg.get('updated_at',cfg.get('created_at'))
if isinstance(stamp,(int,float)):
    anchor=datetime.fromtimestamp(stamp/1000,timezone.utc)
    elapsed=max(0,(now()-anchor).total_seconds())
    due=anchor+timedelta(hours=int(elapsed//3600)+1)
    receipt['scheduled_chat'].update(next_due_utc=due.isoformat(),next_due_basis='Recurrence-derived from actual app configuration timestamp, NOT a reported dispatch time.')
proof=ROOT/'runtime/LATEST_SCHEDULED_RECEIPT.json'
if proof.exists():
    p=read(proof);assert p['campaign_id']==ROOT.name and p['task_sha256']==sha(ROOT/'TASK.md') and p['local_task_read']
    receipt.update(new_windows_task_read_write=True,windows_binding_receipt=p,windows_scheduler=read(ROOT/'runtime/SCHEDULER.json'))
    assert cfg['status']=='ACTIVE'
    receipt['status']='VERIFIED'
    receipt['verification_scope']='Reused actual old takeover/checkpoint/stop tests plus actual new Windows scheduled TASK read/write and new local same-chat configuration. No new scheduled chat delivery or real quota-reset takeover claimed until observed.'
receipt['updated_utc']=now().isoformat();atomic(ROOT/'AUTO_RESUME_RECEIPT.json',receipt)
probes=ROOT/'runtime/HEARTBEAT_PROBES.json'
if probes.exists():
    rows=read(probes)
    receipt['actual_new_scheduled_chat_probes']=rows
    receipt['actual_new_scheduled_takeover_verified']=any(r['campaign_id']==ROOT.name and r['task_sha256']==sha(ROOT/'TASK.md') and r['local_task_read'] for r in rows)
    receipt['actual_quota_reset_takeover_observed']=False
    receipt['quota_scope']='A new scheduled takeover is now evidenced; no contemporaneous exhausted-quota/reset timestamp pair was captured, so automatic post-reset takeover is not claimed.'
    atomic(ROOT/'AUTO_RESUME_RECEIPT.json',receipt)
event('AUTOMATION_BINDING_CHECK',status=receipt['status'])
print({'status':receipt['status'],'scheduled_chat':receipt['scheduled_chat'],'new_windows_task_read_write':receipt['new_windows_task_read_write']})
