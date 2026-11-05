use git2::Repository;
use serde_json::{Value, json};
use std::fs;
use std::path::Path;
use std::process::{Command, Output};
use tempfile::TempDir;
use veilguard::model::Model;
use veilguard::{ModelSelection, ScanLimits, scan, scan_with_model};

const VALUE: &str = "AuthoredPrivateSentinel123";
const SOURCE: &str = "token = 'AuthoredPrivateSentinel123'\r\npassword = 'tiny'\r\n";
struct Fixture {
    dir: TempDir,
    repo: Repository,
}
impl Fixture {
    fn new() -> Self {
        let dir = tempfile::tempdir().unwrap();
        let repo = Repository::init(dir.path()).unwrap();
        Self { dir, repo }
    }
    fn stage(&self, path: &str, source: &str) {
        fs::write(self.dir.path().join(path), source).unwrap();
        let mut index = self.repo.index().unwrap();
        index.add_path(Path::new(path)).unwrap();
        index.write().unwrap();
    }
    fn run(&self, extra: &[&str]) -> Output {
        Command::new(env!("CARGO_BIN_EXE_veilguard"))
            .args(["scan", "--staged", "--format", "json", "--repo"])
            .arg(self.dir.path())
            .args(extra)
            .output()
            .unwrap()
    }
}
fn bundle() -> Value {
    let line = SOURCE.lines().next().unwrap();
    let start = line.find(VALUE).unwrap();
    let vector = veilguard::features::from_line(line, start..start + VALUE.len()).unwrap();
    json!({
        "schema":"veilguard.knn-model.v1", "feature_schema":"veilguard.features.v1",
        "feature_names":veilguard::features::NAMES,
        "label_encoding":{"0":"benign_fixture","1":"sensitive_candidate"},
        "status":"experimental_research_only", "model_id":VALUE,
        "corpus_source_sha256":"a".repeat(64), "protocol_sha256":"b".repeat(64),
        "training_partition":"train", "k":1, "weights":"uniform",
        "mean":vec![0;8], "scale":vec![1;8], "raw_min":vec![0;8], "raw_max":vec![100;8],
        "policy":{"review_all":false,"margin":0,"distance_limit":100,"selection_status":"baseline_fixed"},
        "references":[{"id":VALUE,"label":0,"vector":vector.coordinates()}]
    })
}
fn command(args: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_veilguard"))
        .args(args)
        .output()
        .unwrap()
}
fn redacted(output: &Output) {
    assert!(!String::from_utf8_lossy(&output.stdout).contains(VALUE));
    assert!(!String::from_utf8_lossy(&output.stderr).contains(VALUE));
}
fn generic(r: &Value, line: u64) -> &Value {
    r["findings"]
        .as_array()
        .unwrap()
        .iter()
        .find(|f| f["staged_line"] == line)
        .unwrap()
}

#[test]
fn native_low_vote_never_clears_review_or_overrides_rules_and_index_is_unchanged() {
    let f = Fixture::new();
    f.stage(
        "fixture.txt",
        &format!("{SOURCE}access = 'ghp_{}'\n", "A".repeat(36)),
    );
    let model = Model::from_json(&serde_json::to_vec(&bundle()).unwrap()).unwrap();
    let before = fs::read(f.repo.path().join("index")).unwrap();
    // Worktree disagrees with index; inference must still see the staged value.
    fs::write(f.dir.path().join("fixture.txt"), "clean working copy\n").unwrap();
    let plain = scan(f.dir.path(), &ScanLimits::default()).unwrap();
    let report = scan_with_model(
        f.dir.path(),
        &ScanLimits::default(),
        ModelSelection::Ready(&model),
        true,
    )
    .unwrap();
    assert_eq!(report.exit_code(), 1);
    assert_eq!(report.findings.len(), plain.findings.len());
    assert!(report.coverage_complete);
    let r = serde_json::to_value(&report).unwrap();
    let first = generic(&r, 1);
    assert_eq!(first["policy"], "review");
    assert_eq!(first["model"]["score"], 0.0);
    assert_eq!(first["model"]["rank"], 1);
    assert_eq!(first["model"]["nearest"], 0.0);
    assert_eq!(first["model"]["neighbours"][0]["reference"], 1);
    assert_eq!(first["review_reason"], "experimental_review_only");
    assert_eq!(generic(&r, 2)["model_status"], "unsupported");
    assert_eq!(generic(&r, 2)["review_reason"], "short_literal");
    assert_eq!(generic(&r, 3)["policy"], "block");
    assert!(generic(&r, 3)["model"].is_null());
    for (a, b) in plain.findings.iter().zip(&report.findings) {
        assert_eq!((&a.id, a.rule_id, a.policy), (&b.id, b.rule_id, b.policy));
    }
    assert!(!serde_json::to_string(&report).unwrap().contains(VALUE));
    assert!(!report.text().contains(VALUE));
    assert_eq!(before, fs::read(f.repo.path().join("index")).unwrap());
    assert_eq!(
        fs::read_to_string(f.dir.path().join("fixture.txt")).unwrap(),
        "clean working copy\n"
    );
}

#[test]
fn cli_missing_corrupt_oversized_and_no_model_preserve_scan_and_exit_code() {
    let f = Fixture::new();
    f.stage("fixture.txt", SOURCE);
    let temp = tempfile::tempdir().unwrap();
    let corrupt = temp.path().join("invalid.json");
    fs::write(&corrupt, VALUE).unwrap();
    let missing = temp.path().join("missing.json");
    let large = temp.path().join("large.json");
    fs::File::create(&large)
        .unwrap()
        .set_len((veilguard::model::MAX_MODEL_BYTES + 1) as u64)
        .unwrap();
    for (path, status) in [
        (None, "not_requested"),
        (Some(&missing), "unavailable"),
        (Some(&corrupt), "invalid"),
        (Some(&large), "unavailable"),
    ] {
        let output = if let Some(path) = path {
            f.run(&["--model", path.to_str().unwrap()])
        } else {
            f.run(&[])
        };
        assert_eq!(output.status.code(), Some(0));
        redacted(&output);
        let report: Value = serde_json::from_slice(&output.stdout).unwrap();
        assert_eq!(report["model_status"], status);
        assert_eq!(report["coverage_complete"], true);
        assert_eq!(report["findings"].as_array().unwrap().len(), 2);
        assert!(report["findings"][0]["model"].is_null());
    }
    f.stage("block.txt", &format!("ghp_{}\n", "A".repeat(36)));
    assert_eq!(
        f.run(&["--model", missing.to_str().unwrap()]).status.code(),
        Some(1)
    );
}

#[test]
fn failed_inference_is_degraded_but_preserves_usable_review() {
    let f = Fixture::new();
    f.stage("fixture.txt", SOURCE);
    let mut b = bundle();
    b["mean"] = json!(vec![1e308; 8]);
    b["references"][0]["vector"] = json!(vec![1e308; 8]);
    let m = Model::from_json(&serde_json::to_vec(&b).unwrap()).unwrap();
    let report = scan_with_model(
        f.dir.path(),
        &ScanLimits::default(),
        ModelSelection::Ready(&m),
        true,
    )
    .unwrap();
    assert_eq!(report.model_status, "degraded");
    assert!(report.coverage_complete);
    assert_eq!(report.exit_code(), 0);
    assert_eq!(report.findings[0].model_status, "inference_failed");
    assert_eq!(report.findings[0].review_reason, Some("inference_failed"));
    assert!(report.findings[0].model.is_none());
}

#[test]
fn frozen_model_still_reviews_every_candidate_and_omits_default_neighbour_details() {
    let f = Fixture::new();
    f.stage("fixture.txt", SOURCE);
    let path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("research/results/synthetic-v1/development/model.json");
    let output = f.run(&["--model", path.to_str().unwrap()]);
    redacted(&output);
    assert_eq!(output.status.code(), Some(0));
    let r: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(r["model_status"], "experimental");
    assert_eq!(generic(&r, 1)["review_reason"], "validation_policy_unmet");
    assert_eq!(generic(&r, 1)["policy"], "review");
    assert!(generic(&r, 1)["model"]["neighbours"].is_null());
    assert!(generic(&r, 1)["model"].get("prediction").is_none());
}

#[test]
fn inspect_and_explain_never_echo_source_paths_ids_or_vectors_and_need_no_repository() {
    let f = Fixture::new();
    f.stage("fixture.txt", SOURCE);
    let tmp = tempfile::tempdir().unwrap();
    let model = tmp.path().join("model.json");
    fs::write(&model, serde_json::to_vec(&bundle()).unwrap()).unwrap();
    let inspect = command(&["model", "inspect", model.to_str().unwrap()]);
    redacted(&inspect);
    assert_eq!(inspect.status.code(), Some(0));
    let metadata: Value = serde_json::from_slice(&inspect.stdout).unwrap();
    assert_eq!(metadata["references"], 1);
    assert!(metadata.get("mean").is_none());
    assert!(metadata.get("model_id").is_none());
    let output = f.run(&["--model", model.to_str().unwrap(), "--explanations"]);
    assert_eq!(output.status.code(), Some(0));
    redacted(&output);
    let mut report: Value = serde_json::from_slice(&output.stdout).unwrap();
    report["findings"][0]["path"] = json!(format!("{VALUE}\u{1b}[2J"));
    report["untrusted_snippet"] = json!(VALUE);
    let saved = tmp.path().join("saved.json");
    fs::write(&saved, serde_json::to_vec(&report).unwrap()).unwrap();
    drop(f.repo);
    fs::remove_dir_all(f.dir.path()).unwrap();
    for format in ["text", "json"] {
        let explanation = command(&[
            "explain",
            "--report",
            saved.to_str().unwrap(),
            "--finding",
            "finding-00001",
            "--format",
            format,
        ]);
        assert_eq!(explanation.status.code(), Some(0));
        redacted(&explanation);
        let text = String::from_utf8(explanation.stdout).unwrap();
        assert!(text.contains("contribution"));
        assert!(!text.contains("[2J"));
        assert!(!text.contains("fixture.txt"));
    }
    // A forged free-text field must fail closed rather than reach the terminal.
    report["findings"][0]["review_reason"] = json!(VALUE);
    fs::write(&saved, serde_json::to_vec(&report).unwrap()).unwrap();
    let output = command(&[
        "explain",
        "--report",
        saved.to_str().unwrap(),
        "--finding",
        "finding-00001",
    ]);
    assert_eq!(output.status.code(), Some(2));
    assert!(output.stdout.is_empty());
    redacted(&output);
}

#[test]
fn explanation_rejects_invalid_numeric_evidence_duplicate_ids_and_legacy_reports() {
    let f = Fixture::new();
    f.stage("fixture.txt", SOURCE);
    let model = Model::from_json(&serde_json::to_vec(&bundle()).unwrap()).unwrap();
    let r = scan_with_model(
        f.dir.path(),
        &ScanLimits::default(),
        ModelSelection::Ready(&model),
        true,
    )
    .unwrap();
    let value = serde_json::to_value(r).unwrap();
    for (pointer, change) in [
        ("/report_schema", json!("veilguard.report.v2")),
        ("/findings/0/model/score", json!(2)),
        ("/findings/0/model/neighbours/0/contributions/0", json!(-1)),
        ("/findings/0/model/rank", json!(0)),
        ("/findings/0/model/neighbours/0/reference", json!(VALUE)),
        ("/findings/0/model_status", json!(VALUE)),
    ] {
        let mut bad = value.clone();
        *bad.pointer_mut(pointer).unwrap() = change;
        assert!(
            veilguard::explanation::from_report(
                &serde_json::to_vec(&bad).unwrap(),
                "finding-00001"
            )
            .is_err(),
            "{pointer}"
        );
    }
    let mut duplicate = value.clone();
    duplicate["findings"][1] = duplicate["findings"][0].clone();
    assert!(
        veilguard::explanation::from_report(
            &serde_json::to_vec(&duplicate).unwrap(),
            "finding-00001"
        )
        .is_err()
    );
    for id in [VALUE, "finding-1", "finding-00000", "finding-99999"] {
        assert!(
            veilguard::explanation::from_report(&serde_json::to_vec(&value).unwrap(), id).is_err()
        );
    }
}

#[cfg(unix)]
#[test]
fn input_symlinks_and_fifos_are_refused_without_hanging() {
    use std::os::unix::fs::symlink;
    let tmp = tempfile::tempdir().unwrap();
    let real = tmp.path().join("model.json");
    fs::write(&real, serde_json::to_vec(&bundle()).unwrap()).unwrap();
    let link = tmp.path().join("link");
    symlink(&real, &link).unwrap();
    assert!(veilguard::local_input::read(&link, 1024).is_err());
    let fifo = tmp.path().join("fifo");
    let name = std::ffi::CString::new(fifo.as_os_str().as_encoded_bytes()).unwrap();
    assert_eq!(unsafe { libc::mkfifo(name.as_ptr(), 0o600) }, 0);
    assert!(veilguard::local_input::read(&fifo, 1024).is_err());
    let output = command(&["model", "inspect", fifo.to_str().unwrap()]);
    assert_eq!(output.status.code(), Some(2));
    assert!(output.stdout.is_empty());
}

#[test]
fn ranks_descend_without_changing_ids_and_saved_output_can_be_explained() {
    let f = Fixture::new();
    let second = "token = 'OtherSyntheticValue456'";
    f.stage(
        "fixture.txt",
        &format!("{}\n{second}\n", SOURCE.lines().next().unwrap()),
    );
    let mut b = bundle();
    let start = second.find("OtherSyntheticValue456").unwrap();
    let vector =
        veilguard::features::from_line(second, start..start + "OtherSyntheticValue456".len())
            .unwrap();
    b["references"]
        .as_array_mut()
        .unwrap()
        .push(json!({"id":"positive-example","label":1,"vector":vector.coordinates()}));
    let tmp = tempfile::tempdir().unwrap();
    let path = tmp.path().join("model.json");
    fs::write(&path, serde_json::to_vec(&b).unwrap()).unwrap();
    let saved = tmp.path().join("report.json");
    let output = f.run(&[
        "--model",
        path.to_str().unwrap(),
        "--explanations",
        "--output",
        saved.to_str().unwrap(),
    ]);
    assert_eq!(output.status.code(), Some(0));
    assert!(output.stdout.is_empty());
    let bytes = fs::read(&saved).unwrap();
    assert!(!String::from_utf8_lossy(&bytes).contains(VALUE));
    let r: Value = serde_json::from_slice(&bytes).unwrap();
    assert_eq!(r["findings"][0]["id"], "finding-00001");
    assert_eq!(r["findings"][0]["model"]["rank"], 2);
    assert_eq!(r["findings"][1]["model"]["rank"], 1);
    let output = command(&[
        "explain",
        "--report",
        saved.to_str().unwrap(),
        "--finding",
        "finding-00002",
    ]);
    assert_eq!(output.status.code(), Some(0));
    assert!(String::from_utf8_lossy(&output.stdout).contains("rank: 1"));
    let again = f.run(&[
        "--model",
        path.to_str().unwrap(),
        "--output",
        saved.to_str().unwrap(),
    ]);
    assert_eq!(again.status.code(), Some(2));
    assert_eq!(fs::read(&saved).unwrap(), bytes);
}

#[test]
fn model_evidence_cannot_consume_the_last_slot_needed_by_a_blocking_rule() {
    let f = Fixture::new();
    f.stage("a-review.txt", SOURCE);
    f.stage("z-block.txt", &format!("ghp_{}\n", "A".repeat(36)));
    let model = Model::from_json(&serde_json::to_vec(&bundle()).unwrap()).unwrap();
    let limits = ScanLimits {
        max_findings: 1,
        ..ScanLimits::default()
    };
    let report =
        scan_with_model(f.dir.path(), &limits, ModelSelection::Ready(&model), true).unwrap();
    assert_eq!(report.exit_code(), 2);
    assert!(!report.coverage_complete);
    assert_eq!(report.findings.len(), 1);
    assert_eq!(report.findings[0].policy, "block");
    assert!(report.findings[0].model.is_none());
    assert_eq!(report.findings[0].path, "[path withheld]");
}
