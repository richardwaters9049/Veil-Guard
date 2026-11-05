//! Bounded staged scanner and versioned eight-feature research primitives.
//! No provider validation, runtime subprocesses or network client. Experimental model inference is opt-in through the library.
mod candidates;
pub mod features;
pub mod git_index;
pub mod model;
mod privacy;
pub mod report;
mod repository;
mod rules;

pub use git_index::{ScanLimits, scan};
pub use report::Report;
