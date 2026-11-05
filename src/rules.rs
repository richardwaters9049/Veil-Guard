use regex::Regex;
use std::collections::BTreeSet;
use std::sync::LazyLock;

static PAT: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"\bghp_[A-Za-z0-9]{36}\b").expect("static rule"));
static KEY: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----$")
        .expect("static rule")
});
static ASSIGNMENT: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"^\s*["']?([A-Za-z_][A-Za-z0-9_.-]*)["']?\s*[:=]\s*(\S.*?)\s*$"#)
        .expect("static rule")
});

pub struct RuleFinding {
    pub line: u32,
    pub rule: &'static str,
    pub policy: &'static str,
}

fn sensitive_key(key: &str) -> bool {
    const WORDS: [&str; 7] = [
        "password",
        "passwd",
        "secret",
        "token",
        "credential",
        "apikey",
        "privatekey",
    ];
    let mut separated = String::new();
    let mut previous_lower = false;
    for c in key.chars() {
        if c.is_ascii_uppercase() && previous_lower {
            separated.push(' ');
        }
        if c.is_ascii_alphanumeric() {
            separated.push(c.to_ascii_lowercase());
        } else {
            separated.push(' ');
        }
        previous_lower = c.is_ascii_lowercase();
    }
    let tokens: Vec<_> = separated.split_whitespace().collect();
    tokens.iter().any(|t| WORDS.contains(t))
        || tokens
            .windows(2)
            .any(|w| WORDS.contains(&format!("{}{}", w[0], w[1]).as_str()))
}

/// Scope: one finding per physical line/rule, not a candidate count or 8D extractor.
/// Assignment values are deliberately never copied into a finding.
pub fn detect(text: &str, changed: &BTreeSet<u32>, cap: usize) -> (Vec<RuleFinding>, bool) {
    let mut found = Vec::new();
    let mut key_start: Option<(u32, String)> = None;
    let mut key_changed = None;
    let mut last_line = 0;
    for (i, line) in text.split('\n').enumerate() {
        let number = (i + 1) as u32;
        last_line = number;
        let trimmed = line.trim();
        if key_start.is_none() && KEY.is_match(trimmed) {
            key_start = Some((number, trimmed.replacen("BEGIN", "END", 1)));
            key_changed = None;
        }
        if key_start.is_some() && changed.contains(&number) && key_changed.is_none() {
            key_changed = Some(number);
        }
        if let Some((_, end)) = &key_start
            && trimmed == end
        {
            if let Some(changed_line) = key_changed {
                if found.len() == cap {
                    return (found, true);
                }
                found.push(RuleFinding {
                    line: changed_line,
                    rule: "private-key-marker",
                    policy: "block",
                });
            }
            key_start = None;
            key_changed = None;
        }
        if !changed.contains(&number) {
            continue;
        }
        let matched_pat = PAT.is_match(line);
        if matched_pat {
            if found.len() == cap {
                return (found, true);
            }
            found.push(RuleFinding {
                line: number,
                rule: "github-pat-shape",
                policy: "block",
            });
        }
        if !matched_pat
            && let Some(captures) = ASSIGNMENT.captures(line)
            && sensitive_key(&captures[1])
        {
            if found.len() == cap {
                return (found, true);
            }
            found.push(RuleFinding {
                line: number,
                rule: "sensitive-assignment",
                policy: "review",
            });
        }
    }
    // An unterminated private-key block is still a conservative marker warning.
    if key_start.is_some() && key_changed.is_some_and(|n| n <= last_line) {
        if found.len() == cap {
            return (found, true);
        }
        found.push(RuleFinding {
            line: key_changed.expect("checked above"),
            rule: "private-key-marker",
            policy: "block",
        });
    }
    found.sort_by_key(|f| (f.line, f.rule));
    (found, false)
}
