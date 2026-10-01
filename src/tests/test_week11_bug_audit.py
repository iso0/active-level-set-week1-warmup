import csv, hashlib, io, json
import pytest
import src.week11_bug_audit as audit

IDS = tuple(f"sim-{i:03d}" for i in range(185))

def raw(rows):
    stream=io.StringIO(newline=""); writer=csv.writer(stream,lineterminator="\n")
    writer.writerow(audit.EXPECTED_HEADER); writer.writerows(rows); return stream.getvalue().encode()

def row(sim,t,*,bf="true",fin="true",labels=("other-a","other-b","other-c")):
    return [sim,f"hash-{sim}","SECRET-P","SECRET-VX","SECRET-LS","SECRET-ST",bf,fin,t,*labels]

def project(data):
    return audit.project_bug_only(data,IDS,expected_sha256=hashlib.sha256(data).hexdigest(),expected_size=len(data))

def test_bug_projection_discards_nonbug_categories_and_inputs():
    rows=[row(sim,10) for sim in IDS]+[row("sim-000",20,labels=("other",audit.SCREENSHOT_BUG,"hidden-physical"))]
    result=project(raw(rows)); affected=result["affected"][0]
    assert result["summary"]["bug_affected_simulations"]==1
    assert affected["first_bug_annotation_ordinal"]==1 and affected["preceding_non_bug_annotation_ordinal"]==0
    assert "SECRET" not in repr(result) and "hidden-physical" not in repr(result)

def test_status_is_separate_and_new_bug_literal_is_reported():
    rows=[row(sim,10) for sim in IDS]
    rows[0]=row("sim-000",10,bf="false")
    rows[1]=row("sim-001",10,labels=("Wall Bugs", "other", "other"))
    result=project(raw(rows)); summary=result["summary"]
    assert summary["bug_affected_simulations"]==1 and summary["representation_mismatch"]
    assert summary["unexpected_bug_categories"]==["Wall Bugs"]
    assert summary["frame_status_crosstab"]["bug_free_0__finished_1__any_bug_0__screenshot_bug_0"]==1

def test_beginning_later_and_exact_vs_any_bug_are_counted():
    rows=[row(sim,10) for sim in IDS]
    rows[0]=row("sim-000",10,labels=(audit.SCREENSHOT_BUG,"other","other"))
    rows.append(row("sim-001",20,labels=("other","Technical Bug","other")))
    result=project(raw(rows)); summary=result["summary"]
    assert summary["bug_from_beginning"]==1 and summary["bug_later"]==1
    assert summary["explicit_bug_category_cell_counts"]=={"Screenshot Bug":1,"Technical Bug":1}

def test_identity_header_membership_boolean_and_hash_drift_fail_closed():
    data=raw([row(sim,10) for sim in IDS])
    with pytest.raises(ValueError,match="identity"): audit.project_bug_only(data,IDS,expected_sha256="0"*64,expected_size=len(data))
    changed=data.replace(b"label_final",b"unexpected")
    with pytest.raises(ValueError,match="header"): audit.project_bug_only(changed,IDS,expected_sha256=hashlib.sha256(changed).hexdigest(),expected_size=len(changed))
    rows=[row(sim,10) for sim in IDS]; rows[0][0]="outside"
    with pytest.raises(ValueError,match="allowlist"): project(raw(rows))
    rows=[row(sim,10) for sim in IDS]; rows[0][6]="maybe"
    with pytest.raises(ValueError,match="boolean"): project(raw(rows))
    rows=[row(sim,10) for sim in IDS]+[row("sim-000",20)]; rows[-1][1]="changed"
    with pytest.raises(ValueError,match="source hash changes"): project(raw(rows))

def test_nonmonotonic_or_duplicate_timestep_fails_closed():
    rows=[row(sim,10) for sim in IDS]+[row("sim-000",10,labels=(audit.SCREENSHOT_BUG,"other","other"))]
    with pytest.raises(ValueError,match="strictly increasing"): project(raw(rows))

def test_timing_enrichment_projects_frames_and_numeric_integrity_without_labels():
    sim=IDS[0]
    affected=[{"simulation_id":sim,"annotation_count":2,"first_bug_annotation_ordinal":1}]
    bug_frames=[{"simulation_id":sim,"annotation_ordinal":1,"timestep":20.0,"explicit_bug_token_1":True,"explicit_bug_token_2":False,"explicit_bug_token_final":False}]
    monitor=[]
    payloads={
        "iter":b"10\n15\n20\n30\n", "time":b"0.1\n0.15\n0.2\n0.3\n",
        "bounds":b"0,1,0,1,0,1\n0,1,0,1,0,1\n-1e31,1e31,-1e31,1e31,-1e31,1e31\n0,1,0,1,0,1\n",
        "frames":b"frame_idx,timestep,label,front_filename,side_filename,top_filename\n0,10,SECRET,a,b,c\n1,20,HIDDEN,d,e,f\n",
    }
    for name,oid in (("iter.dat","iter"),("time.dat","time"),("position-bounds_melt.dat","bounds")):
        monitor.append({"path":f"{sim}/monitor/{name}","oid":oid})
    directory=[{"path":f"{sim}/frames.csv","oid":"frames"}]
    result=audit.enrich_technical_timing(affected,bug_frames,monitor,directory,fetcher=lambda path:payloads[path.split("/")[-1].replace("iter.dat","iter").replace("time.dat","time").replace("position-bounds_melt.dat","bounds").replace("frames.csv","frames")],include_bounds=True)
    assert result["affected"][0]["confirmed_first_bug_frame_idx"]==1
    assert result["affected"][0]["first_bug_physical_time_seconds"]==pytest.approx(0.2)
    assert result["affected"][0]["preceding_non_bug_physical_time_seconds"]==pytest.approx(0.1)
    assert result["affected"][0]["numeric_prebug_integrity_pass"] is True
    assert "SECRET" not in repr(result) and "HIDDEN" not in repr(result)

def test_finalize_preserves_contrary_status_and_writes_complete_outputs(tmp_path):
    rows=[row(sim,10) for sim in IDS]
    rows[0]=row("sim-000",10,bf="false")
    rows[1]=row("sim-001",10,labels=(audit.SCREENSHOT_BUG,"other","other"))
    result=project(raw(rows))
    result["affected"][0].update(first_bug_fraction_of_annotation_span=0.5,
        first_bug_physical_time_seconds=0.2, annotation_count=2)
    result["integrity"]=[{"simulation_id":"sim-001","bounds_integrity_status":"NOT_RUN_REMOTE_FETCH_TIMEOUT"}]
    manifest=tmp_path/"manifest.csv"
    with manifest.open("w",encoding="utf-8",newline="") as stream:
        writer=csv.writer(stream,lineterminator="\n")
        writer.writerow(["sim_id","config_token","group_token","P","VX","LS","ST"])
        for sim in IDS: writer.writerow([sim,sim,f"group-{sim}",1,1,1,1])
    audit.finalize_result(result,manifest)
    statuses={item["simulation_id"]:item["technical_usability_status"] for item in result["status_rows"]}
    assert statuses["sim-000"]=="UNRESOLVED" and statuses["sim-001"]=="UNRESOLVED"
    assert result["summary"]["usability_counts"]=={"KEEP":183,"KEEP_WITH_TRUNCATION":0,"EXCLUDE":0,"UNRESOLVED":2}
    output=tmp_path/"result"
    audit.write_outputs(result,output,{"unique_payload_downloads":0,"payloads":[]})
    assert (output/"prebug_numeric_integrity.csv").is_file()
    assert json.loads((output/"bug_audit_summary.json").read_text())["clearly_usable_whole_run_cohort"]==183
