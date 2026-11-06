//! Research-only bridge for approved synthetic vectors, not source-code input.
use serde::Deserialize;
use std::io::{self, Read, Write};
use veilguard::model::{MAX_MODEL_BYTES, Model};

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Request {
    model: serde_json::Value,
    queries: Vec<[f64; 8]>,
}
fn run() -> Result<(), ()> {
    let mut bytes = Vec::new();
    io::stdin()
        .take((MAX_MODEL_BYTES + 1) as u64)
        .read_to_end(&mut bytes)
        .map_err(|_| ())?;
    if bytes.len() > MAX_MODEL_BYTES {
        return Err(());
    }
    let request: Request = serde_json::from_slice(&bytes).map_err(|_| ())?;
    if request.queries.len() > 10_000 {
        return Err(());
    }
    let model =
        Model::from_json(&serde_json::to_vec(&request.model).map_err(|_| ())?).map_err(|_| ())?;
    // Bound retained diagnostic output as well as request bytes.
    if request.queries.len() * model.neighbour_count() > 100_000 {
        return Err(());
    }
    let predictions = request
        .queries
        .iter()
        .map(|q| model.predict(q))
        .collect::<Result<Vec<_>, _>>()
        .map_err(|_| ())?;
    let output = serde_json::to_vec(&predictions).map_err(|_| ())?;
    io::stdout().write_all(&output).map_err(|_| ())
}
fn main() {
    if run().is_err() {
        eprintln!("Synthetic inference bridge failed; input details withheld.");
        std::process::exit(2);
    }
}
