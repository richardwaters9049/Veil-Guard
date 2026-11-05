use serde_json::Value;
use veilguard::features::{self, FeatureError};
fn close(actual: f64, expected: f64) {
    assert!(actual.is_finite() && (actual - expected).abs() <= 1e-9);
}
#[test]
fn authored_eight_coordinate_and_context_fixtures() {
    let fixture: Value =
        serde_json::from_str(include_str!("../research/fixtures/features-v1.json")).unwrap();
    assert_eq!(fixture["feature_schema"], features::SCHEMA);
    for case in fixture["cases"].as_array().unwrap() {
        let line = case["line"].as_str().unwrap();
        let span = case["start"].as_u64().unwrap() as usize..case["end"].as_u64().unwrap() as usize;
        if case["kind"] == "proximity" {
            close(
                features::keyword_proximity(line, span).unwrap(),
                case["expected"].as_f64().unwrap(),
            );
        } else {
            let result = features::from_line(line, span);
            if case["expected"].is_null() {
                assert!(result.is_err(), "fixture ID: {}", case["id"]);
            } else {
                assert!(result.is_ok(), "fixture ID: {}", case["id"]);
                let actual = result.ok().unwrap();
                let expected = case["expected"].as_array().unwrap();
                assert_eq!(expected.len(), 8);
                for (value, target) in actual.coordinates().iter().zip(expected) {
                    close(*value, target.as_f64().unwrap());
                }
            }
        }
    }
}
#[test]
fn invalid_context_is_rejected_without_source_in_errors() {
    for span in [0..0, std::ops::Range { start: 9, end: 1 }, 0..99, 1..9] {
        let error = features::from_line("é", span).err().unwrap();
        assert_eq!(error, FeatureError::InvalidContext);
        assert_eq!(format!("{error:?}"), "InvalidContext");
    }
    assert!(features::from_line(&" ".repeat(1_048_577), 1..9).is_err());
}
#[test]
fn dimension_finiteness_scale_and_overflow_are_checked() {
    for invalid in [
        vec![0.0; 7],
        vec![0.0; 9],
        vec![f64::NAN; 8],
        vec![f64::INFINITY; 8],
    ] {
        assert!(features::standardise(&invalid, &[0.0; 8], &[1.0; 8]).is_err());
        assert!(features::squared_distance_contributions(&invalid, &[0.0; 8]).is_err());
    }
    for invalid in [0.0, -1.0, f64::NAN, f64::INFINITY] {
        assert!(features::standardise(&[0.0; 8], &[0.0; 8], &[invalid; 8]).is_err());
    }
    assert!(features::standardise(&[f64::MAX; 8], &[-f64::MAX; 8], &[1.0; 8]).is_err());
    assert!(features::squared_distance_contributions(&[1e154; 8], &[0.0; 8]).is_err());
}
#[test]
fn scaling_and_distance_contributions_have_hand_worked_results() {
    let x = [3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0];
    let z = features::standardise(
        &x,
        &[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
        &[1.0, 2.0, 4.0, 0.5, 1.0, 2.0, 4.0, 0.5],
    )
    .unwrap();
    assert_eq!(z, [2.0, 1.0, 0.5, 4.0, 2.0, 1.0, 0.5, 4.0]);
    let terms = features::squared_distance_contributions(&z, &[0.0; 8]).unwrap();
    assert_eq!(terms, [4.0, 1.0, 0.25, 16.0, 4.0, 1.0, 0.25, 16.0]);
    close(terms.iter().sum(), 42.5);
    assert_eq!(
        features::squared_distance_contributions(&z, &z).unwrap(),
        [0.0; 8]
    );
    assert_eq!(
        features::squared_distance_contributions(&[0.0; 8], &z).unwrap(),
        terms
    );
}
