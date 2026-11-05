//! Phase One: bounded, rule-only scanning of staged Git object bytes.
//! No provider validation, runtime subprocesses, model or network client.
pub mod git_index;
pub mod report;
mod rules;

pub use git_index::{ScanLimits, scan};
pub use report::Report;
