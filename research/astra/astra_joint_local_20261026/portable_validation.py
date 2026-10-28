from control import ROOT,atomic,now
def run_unit(u,q,slot):
    q.reserve(u['id'],'TEST_V1__reference_solves',100,2000)
    q.reserve(u['id'],'PORTABLE__model_requests',16,16)
    from portable_check import run
    result=run(ROOT);result['utc']=now().isoformat()
    atomic(ROOT/'evidence/PORTABLE_CHECK.json',result)
    return result
