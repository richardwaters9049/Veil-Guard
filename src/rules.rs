use regex::Regex;
use std::collections::BTreeSet;
use std::ops::Range;
use std::sync::LazyLock;

static PAT: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"\bghp_[A-Za-z0-9]{36}\b").expect("static rule"));
static KEY: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----$")
        .expect("static rule")
});

pub(crate) struct RuleFinding {
    pub line: u32,
    pub column: u32,
    pub end_line: u32,
    pub end_column: u32,
    pub span: Range<usize>,
    pub rule: &'static str,
}

pub(crate) fn detect(text: &str, changed: &BTreeSet<u32>, cap: usize) -> (Vec<RuleFinding>, bool) {
    let mut found = Vec::new();
    let mut key_start: Option<(usize, String)> = None;
    let mut key_changed = None;
    let mut offset = 0;
    let mut last_line = 1;
    let mut last_column = 1;
    for (index, physical) in text.split_inclusive('\n').enumerate() {
        let number = (index + 1) as u32;
        let line = physical.trim_end_matches('\n').trim_end_matches('\r');
        last_line = number;
        last_column = line.len() as u32 + 1;
        let trimmed = line.trim();
        if key_start.is_none() && KEY.is_match(trimmed) {
            key_start = Some((offset, trimmed.replacen("BEGIN", "END", 1)));
            key_changed = None;
        }
        if key_start.is_some() && changed.contains(&number) && key_changed.is_none() {
            key_changed = Some(number);
        }
        if let Some((start, end)) = &key_start
            && trimmed == end
        {
            if let Some(changed_line) = key_changed {
                if found.len() == cap {
                    return (found, true);
                }
                found.push(RuleFinding {
                    line: changed_line,
                    column: 1,
                    end_line: number,
                    end_column: last_column,
                    span: *start..offset + line.len(),
                    rule: "private-key-marker",
                });
            }
            key_start = None;
            key_changed = None;
        }
        if changed.contains(&number) {
            for matched in PAT.find_iter(line) {
                if found.len() == cap {
                    return (found, true);
                }
                found.push(RuleFinding {
                    line: number,
                    column: matched.start() as u32 + 1,
                    end_line: number,
                    end_column: matched.end() as u32 + 1,
                    span: offset + matched.start()..offset + matched.end(),
                    rule: "github-pat-shape",
                });
            }
        }
        offset += physical.len();
    }
    if let Some((start, _)) = key_start
        && let Some(changed_line) = key_changed
    {
        if found.len() == cap {
            return (found, true);
        }
        found.push(RuleFinding {
            line: changed_line,
            column: 1,
            end_line: last_line,
            end_column: last_column,
            span: start..text.len(),
            rule: "private-key-marker",
        });
    }
    found.sort_by_key(|f| (f.line, f.column, f.rule));
    (found, false)
}

pub(crate) fn redact_path_patterns(path: &str) -> String {
    PAT.replace_all(path, "[REDACTED]").into_owned()
}
