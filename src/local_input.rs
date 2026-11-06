//! Explicit local inputs only: bounded, regular, non-symlink files.
use std::fs::OpenOptions;
use std::io::Read;
use std::path::Path;

pub fn read(path: &Path, maximum: usize) -> Result<Vec<u8>, &'static str> {
    let mut options = OpenOptions::new();
    options.read(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options.custom_flags(libc::O_NONBLOCK | libc::O_NOFOLLOW);
    }
    let file = options.open(path).map_err(|_| "input_unavailable")?;
    let metadata = file.metadata().map_err(|_| "input_unavailable")?;
    if !metadata.is_file() || metadata.len() > maximum as u64 {
        return Err("input_type_or_size");
    }
    let mut bytes = Vec::new();
    file.take(maximum as u64 + 1)
        .read_to_end(&mut bytes)
        .map_err(|_| "input_unavailable")?;
    if bytes.len() > maximum {
        return Err("input_type_or_size");
    }
    Ok(bytes)
}
