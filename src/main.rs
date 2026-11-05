use clap::{Parser, Subcommand, ValueEnum, error::ErrorKind};
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::process::ExitCode;
use veilguard::{ScanLimits, scan};

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
    },
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
            eprintln!("Veil Guard: invalid arguments; use veilguard --help.");
            return 2;
        }
    };
    let Command::Scan {
        staged: _,
        repo,
        format,
        output,
    } = cli.command;
    let report = match scan(&repo, &ScanLimits::default()) {
        Ok(report) => report,
        Err(code) => {
            eprintln!("Veil Guard: scan failed [{code}].");
            return 2;
        }
    };
    let content = match format {
        Format::Text => report.text(),
        Format::Json => match serde_json::to_string_pretty(&report) {
            Ok(json) => json + "\n",
            Err(_) => {
                eprintln!("Veil Guard: report serialisation failed.");
                return 3;
            }
        },
    };
    let code = report.exit_code();
    if let Some(output) = output {
        if save_new(&output, content.as_bytes()).is_err() {
            let _ = io::stdout().write_all(content.as_bytes());
            eprintln!("Veil Guard: report file unavailable; existing files are never replaced.");
            return 2;
        }
    } else if io::stdout().write_all(content.as_bytes()).is_err() {
        eprintln!("Veil Guard: report output failed.");
        return 2;
    }
    code
}

fn main() -> ExitCode {
    std::panic::set_hook(Box::new(|_| {
        eprintln!("Veil Guard: internal failure; input details withheld.");
    }));
    let code = std::panic::catch_unwind(run).unwrap_or(3);
    ExitCode::from(code)
}
