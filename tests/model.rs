use serde_json::{Value, json};
use veilguard::model::{MAX_MODEL_BYTES, Model, ModelError};

fn bundle() -> Value {
    json!({
        "schema":"veilguard.knn-model.v1", "feature_schema":"veilguard.features.v1",
        "feature_names":veilguard::features::NAMES,
        "label_encoding":{"0":"benign_fixture","1":"sensitive_candidate"},
        "status":"experimental_research_only", "model_id":"authored-toy",
        "corpus_source_sha256":"a".repeat(64), "protocol_sha256":"b".repeat(64),
        "training_partition":"train", "k":3, "weights":"inverse_distance",
        "mean":vec![0;8], "scale":vec![1;8], "raw_min":vec![-10;8], "raw_max":vec![10;8],
        "policy":{"review_all":false,"margin":0,"distance_limit":10,"selection_status":"baseline_fixed"},
        "references":[
            {"id":"A","label":1,"vector":[1,0,0,0,0,0,0,0]},
            {"id":"B","label":1,"vector":[0,2,0,0,0,0,0,0]},
            {"id":"C","label":0,"vector":[0,0,2,0,0,0,0,0]}
        ]
    })
}
fn load(value: &Value) -> Model {
    Model::from_json(&serde_json::to_vec(value).unwrap()).unwrap()
}

#[test]
fn hand_worked_votes_and_contributions() {
    let mut b = bundle();
    let m = load(&b);
    let p = m.predict(&[0.0; 8]).unwrap();
    assert_eq!(p.score, 0.75);
    assert_eq!(p.prediction, Some(1));
    assert_eq!(
        p.neighbours.iter().map(|n| n.distance).collect::<Vec<_>>(),
        [1.0, 2.0, 2.0]
    );
    assert_eq!(
        p.neighbours[1].contributions,
        [0.0, 4.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    );
    b["weights"] = json!("uniform");
    assert_eq!(load(&b).predict(&[0.0; 8]).unwrap().score, 2.0 / 3.0);
}

#[test]
fn all_exact_matches_vote_beyond_k_and_ties_use_ids() {
    let mut b = bundle();
    b["k"] = json!(1);
    for r in b["references"].as_array_mut().unwrap() {
        r["vector"] = json!(vec![0; 8]);
    }
    let m = load(&b);
    let p = m.predict(&[0.0; 8]).unwrap();
    assert_eq!(p.score, 2.0 / 3.0);
    assert_eq!(p.zero_count, 3);
    assert_eq!(p.review_reason, Some("exact_match_conflict"));
    assert_eq!(p.prediction, None);
    b["references"][0]["vector"] = json!([-1, 0, 0, 0, 0, 0, 0, 0]);
    b["references"][1]["vector"] = json!([1, 0, 0, 0, 0, 0, 0, 0]);
    b["references"].as_array_mut().unwrap().pop();
    b["references"].as_array_mut().unwrap().reverse();
    let m = load(&b);
    assert_eq!(m.predict(&[0.0; 8]).unwrap().neighbours[0].id, "A");
}

#[test]
fn abstention_priority_and_threshold_boundaries() {
    let mut b = bundle();
    b["policy"]["review_all"] = json!(true);
    assert_eq!(
        load(&b).predict(&[20.0; 8]).unwrap().review_reason,
        Some("validation_policy_unmet")
    );
    b["policy"]["review_all"] = json!(false);
    assert_eq!(
        load(&b).predict(&[20.0; 8]).unwrap().review_reason,
        Some("outside_training_support")
    );
    b["policy"]["distance_limit"] = json!(0.5);
    assert_eq!(
        load(&b).predict(&[0.0; 8]).unwrap().review_reason,
        Some("nearest_distance_exceeded")
    );
    b["policy"]["distance_limit"] = json!(1.0);
    b["policy"]["margin"] = json!(0.5);
    assert_eq!(load(&b).predict(&[0.0; 8]).unwrap().review_reason, None);
    b["policy"]["margin"] = json!(0.6);
    assert_eq!(
        load(&b).predict(&[0.0; 8]).unwrap().review_reason,
        Some("low_vote_margin")
    );
}

#[test]
fn strict_bundle_contract_rejects_corruption() {
    let changes = [
        ("/schema", json!("unknown")),
        ("/feature_schema", json!("unknown")),
        ("/feature_names/0", json!("other")),
        ("/label_encoding/0", json!("secret")),
        ("/status", json!("production")),
        ("/training_partition", json!("test")),
        ("/model_id", json!("unsafe/path")),
        ("/corpus_source_sha256", json!("f")),
        ("/protocol_sha256", json!("Z".repeat(64))),
        ("/k", json!(0)),
        ("/k", json!(4)),
        ("/k", json!(true)),
        ("/weights", json!("other")),
        ("/mean", json!(vec![0; 7])),
        ("/scale/0", json!(0)),
        ("/scale/0", json!(-1)),
        ("/raw_min/0", json!(11)),
        ("/policy/margin", json!(1.1)),
        ("/policy/distance_limit", json!(-1)),
        ("/policy/selection_status", json!("other")),
        ("/references/0/label", json!(true)),
        ("/references/0/label", json!(2)),
        ("/references/0/vector/0", json!(false)),
        ("/references/0/id", json!("B")),
        ("/references", json!([])),
        ("/references/0/vector", json!(vec![0; 9])),
    ];
    for (pointer, value) in changes {
        let mut b = bundle();
        *b.pointer_mut(pointer).unwrap() = value;
        assert!(
            matches!(
                Model::from_json(&serde_json::to_vec(&b).unwrap()),
                Err(ModelError::InvalidBundle)
            ),
            "{pointer}"
        );
    }
    let mut b = bundle();
    b["source"] = json!("private");
    assert!(Model::from_json(&serde_json::to_vec(&b).unwrap()).is_err());
    let mut b = bundle();
    b["policy"]["unexpected"] = json!(1);
    assert!(Model::from_json(&serde_json::to_vec(&b).unwrap()).is_err());
    let mut b = bundle();
    b["references"][0]["unexpected"] = json!(1);
    assert!(Model::from_json(&serde_json::to_vec(&b).unwrap()).is_err());
    assert!(Model::from_json(br#"{"schema":"x","schema":"y"}"#).is_err());
    assert!(Model::from_json(b"NaN").is_err());
}

#[test]
fn bounded_input_and_numeric_failure() {
    let bytes = vec![b' '; MAX_MODEL_BYTES + 1];
    assert!(matches!(
        Model::from_reader(bytes.as_slice()),
        Err(ModelError::SizeLimit)
    ));
    let m = load(&bundle());
    assert!(matches!(
        m.predict(&[f64::NAN; 8]),
        Err(ModelError::InvalidQuery)
    ));
    assert!(matches!(
        m.predict(&[1e308; 8]),
        Err(ModelError::NumericOverflow)
    ));
    let mut b = bundle();
    b["scale"][0] = json!(1e-308);
    assert!(matches!(
        load(&b).predict(&[10.0; 8]),
        Err(ModelError::NumericOverflow)
    ));
    let mut b = bundle();
    b["references"][0]["vector"][0] = json!(1e308);
    assert!(matches!(
        load(&b).predict(&[0.0; 8]),
        Err(ModelError::NumericOverflow)
    ));
}

#[test]
fn frozen_export_loads_without_training_or_policy_changes() {
    let bytes = include_bytes!("../research/results/synthetic-v1/development/model.json");
    let m = Model::from_json(bytes).unwrap();
    assert_eq!(m.model_id(), "synthetic-v1-knn-initial");
    assert_eq!(m.reference_count(), 3500);
    assert_eq!(
        m.predict(&[0.0; 8]).unwrap().review_reason,
        Some("validation_policy_unmet")
    );
}
