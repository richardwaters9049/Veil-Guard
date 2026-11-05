//! Bounded staged scanner and versioned eight-feature research primitives.
//! No provider validation, runtime subprocesses, model or network client.
mod candidates;
pub mod features;
pub mod git_index;
mod privacy;
pub mod report;
mod repository;
mod rules;

pub use git_index::{ScanLimits, scan};
pub use report::Report;
