"""Instrument authored fixtures for network/process APIs and hostile Git commands."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import platform
import subprocess
import tempfile
import release_support as s

EVENTS={"socket","connect","sendto","getaddrinfo","fork","vfork","execve","posix_spawn","posix_spawnp"}


def instrument(command,library):
    read,write=os.pipe()
    try:
        env=s.clean_env()
        env["VEILGUARD_GUARD_FD"]=str(write)
        env["DYLD_INSERT_LIBRARIES" if platform.system()=="Darwin" else "LD_PRELOAD"]=str(library)
        result=subprocess.run([str(c) for c in command],env=env,pass_fds=(write,),capture_output=True,timeout=30)
    finally:os.close(write)
    with os.fdopen(read,"rb") as stream: events=stream.read().decode().splitlines()
    assert events.count("guard_loaded")==1 and events.count("guard_finished")==1,"instrumentation_not_active"
    return result,Counter(e for e in events if e not in ("guard_loaded","guard_finished"))


def profile(binary):
    name=str(Path(binary).resolve()).replace("\\","\\\\").replace('"','\\"')
    return f'(version 1)(allow default)(deny network*)(deny process-fork)(deny process-exec)(allow process-exec (literal "{name}"))'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    output=s.new_directory(args.output)
    darwin=platform.system()=="Darwin"
    if not darwin and platform.system()!="Linux":raise ValueError("unsupported_host")
    with tempfile.TemporaryDirectory(prefix="veilguard-runtime-") as temporary:
        root=Path(temporary);library=root/("guard.dylib" if darwin else "guard.so");probe=root/"probe"
        s.run(["cc",*( ["-dynamiclib"] if darwin else ["-shared","-fPIC"]),
               s.ROOT/"scripts/runtime/guard.c","-o",library])
        s.run(["cc",s.ROOT/"scripts/runtime/probe.c","-o",probe,*([] if darwin else ["-ldl"])])
        negative=subprocess.run([str(probe)],env=s.clean_env(),capture_output=True,timeout=30)
        assert negative.returncode==93,"probe_must_refuse_without_guard"
        control,events=instrument([probe],library)
        assert control.returncode==0 and set(events)==EVENTS and all(n==1 for n in events.values()),"positive_control_failed"
        sandbox=False
        if darwin:
            s.run(["/usr/bin/sandbox-exec","-p",profile(probe),probe,"sandbox"])
            sandbox=True
        directory=root/"repository";directory.mkdir();s.fixture(directory,100,blocking=True)
        # Stage before installing tripwires, so fixture setup cannot run them.
        (directory/".gitattributes").write_text("*.txt filter=tripwire diff=tripwire\n")
        s.git(directory,"add","--",".gitattributes")
        marker=root/"repository-command-ran"
        tripwire=root/"tripwire.sh"
        tripwire.write_text(f"#!/bin/sh\nprintf executed > '{marker}'\n")
        tripwire.chmod(0o700)
        for key in ("filter.tripwire.clean","filter.tripwire.smudge","diff.tripwire.textconv",
                    "diff.tripwire.command","diff.external","core.fsmonitor"):
            s.git(directory,"config","--local",key,str(tripwire))
        # A real executable pre-commit hook must remain unexecuted by scan.
        hook=directory/".git/hooks/pre-commit";hook.parent.mkdir(exist_ok=True)
        hook.write_bytes(tripwire.read_bytes());hook.chmod(0o700)
        before=s.snapshot(directory)
        cases=[]
        for model in (False,True):
            command=[s.BINARY,"scan","--staged","--repo",directory,"--format","json"]
            if model:command += ["--model",s.MODEL]
            result,observed=instrument(command,library)
            assert not observed and result.returncode==1
            report=json.loads(result.stdout)
            assert report["coverage_complete"] and any(f["policy"]=="block" for f in report["findings"])
            assert b"VG_DEMO_" not in result.stdout+result.stderr
            if darwin:
                denied=subprocess.run(
                    ["/usr/bin/sandbox-exec","-p",profile(s.BINARY),*[str(c) for c in command]],
                    capture_output=True,env=s.clean_env(),timeout=30)
                assert denied.returncode==1 and json.loads(denied.stdout)==report,"sandbox_scan_changed"
            cases.append({"model_enabled":model,"exit_code":result.returncode,"selected_api_attempts":dict(observed),
                          "coverage_complete":True,"sandbox_replay_passed":sandbox})
        assert before==s.snapshot(directory) and not marker.exists(),"repository_command_or_mutation"
        s.save(output/"runtime.json",{"schema":"veilguard.runtime-evidence.v1","recorded_at":s.now(),
            "host":s.host(),"binary_sha256":s.sha(s.BINARY),"model_sha256":s.sha(s.MODEL),
            "source_identity":s.identity(),"positive_control_events":dict(events),"uninstrumented_probe_refused":True,"cases":cases,
            "repository_command_tripwires":"filters, diff/textconv, fsmonitor and pre-commit; none executed",
            "sandbox":"macOS deny network/fork and foreign exec, positive controlled connect/fork denied" if sandbox else "not_run_on_this_platform",
            "limits":"Dynamic interposition observes selected libc APIs, not every syscall or OS service. macOS sandbox blocks covered network/process operations but is not a source-completeness proof. Linux syscall/network-namespace enforcement remains pending unless separately recorded."})
    print("Runtime controls passed: selected API attempts absent; repository tripwires untouched.")
    return 0

if __name__=="__main__":raise SystemExit(main())
