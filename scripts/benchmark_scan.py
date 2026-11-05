"""Measure fresh scanner processes on authored staged fixtures, never user source."""
import argparse
import json
import math
from pathlib import Path
import platform
import re
import statistics
import subprocess
import tempfile
import time
import release_support as s


def measure(directory, model):
    with tempfile.TemporaryDirectory(prefix="veilguard-timing-") as temp:
        log=Path(temp)/"time.txt"
        if platform.system()=="Darwin":
            timer=["/usr/bin/time","-l","-o",str(log)]
            unit=1
        elif platform.system()=="Linux":
            timer=["/usr/bin/time","-f","%M maximum resident set size","-o",str(log)]
            unit=1024
        else: raise ValueError("unsupported_host")
        command=timer+[str(s.BINARY),"scan","--staged","--repo",str(directory),"--format","json"]
        if model:command += ["--model",str(s.MODEL)]
        start=time.perf_counter()
        result=subprocess.run(command,env=s.clean_env(),capture_output=True,timeout=45)
        elapsed=time.perf_counter()-start
        report=json.loads(result.stdout)
        assert b"VG_DEMO_" not in result.stdout+result.stderr
        rss=int(re.search(r"(\d+)\s+maximum resident set size",log.read_text())[1])*unit
        return {"seconds":elapsed,"peak_rss_bytes":rss,"exit_code":result.returncode,
                "coverage_complete":report["coverage_complete"],"candidates":report["candidates"],
                "findings":len(report["findings"]),"model_status":report["model_status"]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",required=True,type=Path)
    parser.add_argument("--runs",type=int,default=20)
    args=parser.parse_args()
    if not 20<=args.runs<=100:parser.error("runs must be 20–100")
    output=s.new_directory(args.output)
    workloads=[]
    for rows in (100,1000,10000):
        for model in (False,True):
            with tempfile.TemporaryDirectory(prefix="veilguard-benchmark-") as temporary:
                directory=Path(temporary)
                s.fixture(directory,rows)
                before=s.snapshot(directory)
                first=measure(directory,model)
                repeats=[measure(directory,model) for _ in range(args.runs)]
                assert before==s.snapshot(directory),"source_or_index_changed"
                p95=sorted(r["seconds"] for r in repeats)[math.ceil(.95*len(repeats))-1]
                peak=max(r["peak_rss_bytes"] for r in repeats)
                complete=all(r["exit_code"]==0 and r["coverage_complete"] and r["candidates"]==rows
                             for r in [first,*repeats])
                workloads.append({"rows":rows,"files":math.ceil(rows/500),"model_enabled":model,
                    "fixture_recipe":"one ASCII quoted generic literal/line; VG_DEMO ordinal values v1",
                    "first_observed_process":first,"repeated_fresh_processes":repeats,
                    "median_seconds":statistics.median(r["seconds"] for r in repeats),
                    "p95_seconds_nearest_rank":p95,"maximum_peak_rss_bytes":peak,
                    "all_scans_complete":complete,
                    "target_latency_pass":complete and p95<=2.0,
                    "target_memory_pass":complete and peak<=150*1024*1024})
                print(f"Measured {rows} rows; model={model}; p95={p95:.3f}s; peak={peak/1024/1024:.1f}MiB.",flush=True)
    cpu=s.run(["sysctl","-n","machdep.cpu.brand_string"]).stdout.decode().strip() if platform.system()=="Darwin" else platform.processor()
    s.save(output/"benchmark.json",{"schema":"veilguard.benchmark.v1","recorded_at":s.now(),
        "host":s.host(),"cpu":cpu,"binary_sha256":s.sha(s.BINARY),"model_sha256":s.sha(s.MODEL),
        "source_identity":s.identity(),"runs_per_workload":args.runs,
        "measurement":"wall-clock around OS time utility plus new scanner process; max RSS of scanner process",
        "cache_limits":"First observed execution has uncontrolled OS cache state. Repeats use fresh processes after priming. No cache eviction; true filesystem-cold and in-process-warm latency are not measured.",
        "limits":"Local synthetic workloads only; 20–100 repeats support exploratory p95, not production guarantees. Hardware load uncontrolled. Setup/build excluded; startup, Git reads, feature extraction and model loading/inference included.",
        "workloads":workloads})
    return 0

if __name__=="__main__":raise SystemExit(main())
