use clap::{Parser, Subcommand, ValueEnum, error::ErrorKind};
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::process::ExitCode;
use veilguard::{ModelSelection, ScanLimits, scan_with_model};
use veilguard::{explanation, local_input, model::Model};

macro_rules! safe_error {
    ($($argument:tt)*) => {{
        let _ = writeln!(io::stderr(), $($argument)*);
    }};
}

#[derive(Parser)]
#[command(
    name = "veilguard",
    version,
    about = "Offline staged-Git credential review"
)]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Scan staged object bytes. Exit 0 is not a guarantee of no secrets.
    Scan {
        #[arg(long, required = true)]
        staged: bool,
        #[arg(long, default_value = ".")]
        repo: PathBuf,
        #[arg(long, value_enum, default_value = "text")]
        format: Format,
        /// Write a new report; refuse existing files and symlinks.
        #[arg(long)]
        output: Option<PathBuf>,
        /// Explicit local experimental bundle; failure preserves rule-only scanning.
        #[arg(long)]
        model: Option<PathBuf>,
        /// Retain at most five numerical neighbour explanations per scored finding.
        #[arg(long, requires = "model")]
        explanations: bool,
    },
    /// Explain an existing redacted v3 report without reading repository source.
    Explain {
        #[arg(long)]
        report: PathBuf,
        #[arg(long)]
        finding: String,
        #[arg(long, value_enum, default_value = "text")]
        format: Format,
    },
    /// Explicit hook management; never invoked by scanning.
    Hooks {
        #[command(subcommand)]
        command: HookCommand,
    },
    /// Inspect a local experimental model without printing its reference vectors.
    Model {
        #[command(subcommand)]
        command: ModelCommand,
    },
}

#[derive(Subcommand)]
enum ModelCommand {
    Inspect { path: PathBuf },
}

#[derive(Subcommand)]
enum HookCommand {
    Install {
        #[arg(long, default_value = ".")]
        repo: PathBuf,
    },
    Uninstall {
        #[arg(long, default_value = ".")]
        repo: PathBuf,
    },
    Manual,
}

#[derive(Clone, Copy, ValueEnum)]
enum Format {
    Text,
    Json,
}

fn save_new(path: &Path, content: &[u8]) -> io::Result<()> {
    let parent = path
        .parent()
        .filter(|p| !p.as_os_str().is_empty())
        .unwrap_or(Path::new("."));
    let mut temp = tempfile::NamedTempFile::new_in(parent)?;
    temp.write_all(content)?;
    temp.as_file().sync_all()?;
    temp.persist_noclobber(path).map_err(|e| e.error)?;
    Ok(())
}

fn run() -> u8 {
    let cli = match Cli::try_parse() {
        Ok(cli) => cli,
        Err(err)
            if matches!(
                err.kind(),
                ErrorKind::DisplayHelp | ErrorKind::DisplayVersion
            ) =>
        {
            return if io::stdout().write_all(err.to_string().as_bytes()).is_ok() {
                0
            } else {
                2
            };
        }
        Err(_) => {
            // Parser errors may contain argument values. Never display the original.
            safe_error!("Veil Guard: invalid arguments; use veilguard --help.");
            return 2;
        }
    };
    let (repo, format, output, model, explanations) = match cli.command {
        Command::Hooks { command } => {
            let result = match command {
                HookCommand::Manual => Ok(veilguard::hooks::MANUAL),
                HookCommand::Install { repo } => std::env::current_exe()
                    .map_err(|_| "hook_executable_unavailable")
                    .and_then(|exe| veilguard::hooks::install(&repo, &exe)),
                HookCommand::Uninstall { repo } => veilguard::hooks::uninstall(&repo),
            };
            return match result {
                Ok(message) => {
                    if writeln!(io::stdout(), "{message}").is_ok() {
                        0
                    } else {
                        2
                    }
                }
                Err(code) => {
                    safe_error!(
                        "Veil Guard: hook operation failed or refused [{code}]; use hooks manual."
                    );
                    2
                }
            };
        }
        Command::Explain {
            report,
            finding,
            format,
        } => {
            let result = local_input::read(&report, explanation::MAX_REPORT_BYTES)
                .and_then(|bytes| explanation::from_report(&bytes, &finding));
            return match result {
                Ok(explanation) => {
                    let content = match format {
                        Format::Text => explanation.text(),
                        Format::Json => match serde_json::to_string_pretty(&explanation) {
                            Ok(text) => text + "\n",
                            Err(_) => return 3,
                        },
                    };
                    if io::stdout().write_all(content.as_bytes()).is_ok() {
                        0
                    } else {
                        2
                    }
                }
                Err(_) => {
                    safe_error!(
                        "Veil Guard: explanation unavailable; invalid, unsupported or missing report/finding."
                    );
                    2
                }
            };
        }
        Command::Model {
            command: ModelCommand::Inspect { path },
        } => {
            let result = local_input::read(&path, veilguard::model::MAX_MODEL_BYTES)
                .ok()
                .and_then(|bytes| Model::from_json(&bytes).ok());
            return match result {
                Some(model) => match serde_json::to_vec_pretty(&model.inspection()) {
                    Ok(mut bytes) => {
                        bytes.push(b'\n');
                        if io::stdout().write_all(&bytes).is_ok() {
                            0
                        } else {
                            2
                        }
                    }
                    Err(_) => 3,
                },
                None => {
                    safe_error!(
                        "Veil Guard: model unavailable or invalid; input details withheld."
                    );
                    2
                }
            };
        }
        Command::Scan {
            staged: _,
            repo,
            format,
            output,
            model,
            explanations,
        } => (repo, format, output, model, explanations),
    };
    let loaded = model.as_ref().map(|path| {
        local_input::read(path, veilguard::model::MAX_MODEL_BYTES)
            .map(|bytes| Model::from_json(&bytes))
    });
    let selection = match &loaded {
        None => ModelSelection::NotRequested,
        Some(Err(_)) => ModelSelection::Unavailable,
        Some(Ok(Err(_))) => ModelSelection::Invalid,
        Some(Ok(Ok(model))) => ModelSelection::Ready(model),
    };
    let report = match scan_with_model(&repo, &ScanLimits::default(), selection, explanations) {
        Ok(report) => report,
        Err(code) => {
            safe_error!("Veil Guard: scan failed [{code}].");
            return 2;
        }
    };
    let content = match format {
        Format::Text => report.text(),
        Format::Json => match serde_json::to_string_pretty(&report) {
            Ok(json) => json + "\n",
            Err(_) => {
                safe_error!("Veil Guard: report serialisation failed.");
                return 3;
            }
        },
    };
    let code = report.exit_code();
    if let Some(output) = output {
        if save_new(&output, content.as_bytes()).is_err() {
            let _ = io::stdout().write_all(content.as_bytes());
            safe_error!("Veil Guard: report file unavailable; existing files are never replaced.");
            return 2;
        }
    } else if io::stdout().write_all(content.as_bytes()).is_err() {
        safe_error!("Veil Guard: report output failed.");
        return 2;
    }
    code
}

fn guarded_run(operation: impl FnOnce() -> u8 + std::panic::UnwindSafe) -> u8 {
    std::panic::set_hook(Box::new(|_| {
        safe_error!("Veil Guard: internal failure; input details withheld.");
    }));
    std::panic::catch_unwind(operation).unwrap_or(3)
}

fn main() -> ExitCode {
    ExitCode::from(guarded_run(run))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn panic_probe_child() {
        if let Ok(value) = std::env::var("VEILGUARD_PANIC_FIXTURE") {
            std::process::exit(i32::from(guarded_run(|| panic!("{value}"))));
        }
    }

    #[test]
    fn panic_guard_returns_three_and_does_not_log_payload_or_backtrace() {
        let sentinel = "authored-private-panic-sentinel";
        let output = std::process::Command::new(std::env::current_exe().unwrap())
            .args(["--exact", "tests::panic_probe_child", "--nocapture"])
            .env("VEILGUARD_PANIC_FIXTURE", sentinel)
            .env("RUST_BACKTRACE", "1")
            .output()
            .unwrap();
        assert_eq!(output.status.code(), Some(3));
        let rendered = String::from_utf8([output.stdout, output.stderr].concat()).unwrap();
        assert!(rendered.contains("input details withheld"));
        assert!(!rendered.contains(sentinel));
        assert!(!rendered.contains("stack backtrace"));
    }
}
