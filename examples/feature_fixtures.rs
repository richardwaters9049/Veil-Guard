//! Development harness: ONLY compile-time authored synthetic fixtures.
//! No repository reads, stdin, arbitrary fixture paths or raw source output.
use serde_json::{Value, json};
use veilguard::features;
fn vector(value: &Value) -> Vec<f64> {
    value
        .as_array()
        .expect("authored array")
        .iter()
        .map(|v| v.as_f64().expect("number"))
        .collect()
}
fn main() {
    if std::env::args_os().len() != 1 {
        eprintln!("This harness accepts only compiled-in synthetic fixtures.");
        std::process::exit(2);
    }
    let fixtures: Value =
        serde_json::from_str(include_str!("../research/fixtures/features-v1.json"))
            .expect("authored fixtures");
    assert_eq!(fixtures["feature_schema"], features::SCHEMA);
    let cases: Vec<Value> = fixtures["cases"]
        .as_array()
        .expect("cases")
        .iter()
        .map(|case| {
            let line = case["line"].as_str().expect("line");
            let span = case["start"].as_u64().expect("start") as usize
                ..case["end"].as_u64().expect("end") as usize;
            let result = if case["kind"] == "proximity" {
                features::keyword_proximity(line, span).map(|v| json!(v))
            } else {
                features::from_line(line, span).map(|v| json!(v.coordinates()))
            };
            json!({"id": case["id"], "actual": result.ok()})
        })
        .collect();
    let distances: Vec<Value> = fixtures["distance_cases"].as_array().expect("distances").iter().map(|case| {
        let z = features::standardise(&vector(&case["values"]), &vector(&case["means"]), &vector(&case["scales"])).expect("authored scaler");
        let terms = features::squared_distance_contributions(&z, &vector(&case["neighbour"])).expect("authored neighbour");
        json!({"id": case["id"], "standardised": z, "contributions": terms, "squared_distance": terms.iter().sum::<f64>()})
    }).collect();
    println!(
        "{}",
        json!({"schema": "veilguard.feature-parity.v1", "feature_schema": features::SCHEMA,
        "names": features::NAMES, "keywords": features::KEYWORDS, "placeholders": features::PLACEHOLDERS,
        "cases": cases, "distance_cases": distances})
    );
}
