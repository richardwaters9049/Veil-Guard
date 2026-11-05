//! Versioned lexical candidate grammar. Values stay in the caller's source buffer.
//! Candidates contain spans and review metadata only; never derive Debug/Serialize.
use regex::Regex;
use std::collections::BTreeSet;
use std::ops::Range;
use std::sync::LazyLock;

pub(crate) const GRAMMAR: &str = "veilguard.candidates.v1";
static ASSIGNMENT: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"^\s*(?:"([A-Za-z_][A-Za-z0-9_.-]*)"|'([A-Za-z_][A-Za-z0-9_.-]*)'|([A-Za-z_][A-Za-z0-9_.-]*))\s*[:=]\s*"#)
        .expect("static assignment grammar")
});

pub(crate) struct Candidate {
    pub span: Range<usize>,
    pub line: u32,
    pub column: u32,
    pub end_column: u32,
    pub sensitive: bool,
    pub reason: &'static str,
}

pub(crate) struct Extraction {
    pub candidates: Vec<Candidate>,
    pub limit_hit: bool,
}

fn sensitive_key(key: &str) -> bool {
    !crate::features::keyword_spans(key).is_empty()
}

fn quoted_end(bytes: &[u8], start: usize) -> (usize, bool, bool) {
    let quote = bytes[start];
    let mut cursor = start + 1;
    let mut escaped = false;
    while cursor < bytes.len() {
        if bytes[cursor] == b'\\' {
            escaped = true;
            cursor = (cursor + 2).min(bytes.len());
        } else if bytes[cursor] == quote {
            return (cursor, escaped, true);
        } else {
            cursor += 1;
        }
    }
    (bytes.len(), escaped, false)
}

fn reason(value: &str, override_reason: Option<&'static str>) -> &'static str {
    if let Some(reason) = override_reason {
        reason
    } else if !value.bytes().all(|b| (0x20..=0x7e).contains(&b)) {
        "non_ascii_or_control_literal"
    } else if value.len() < 8 {
        "short_literal"
    } else if value.len() > 256 {
        "long_literal"
    } else {
        "model_not_available"
    }
}

#[allow(clippy::too_many_arguments)]
fn emit(
    result: &mut Extraction,
    text: &str,
    span: Range<usize>,
    offset: usize,
    line: u32,
    sensitive: bool,
    override_reason: Option<&'static str>,
    cap: usize,
) {
    let value = &text[span.clone()];
    if !sensitive && value.len() < 8 {
        return;
    }
    if result.candidates.len() == cap {
        result.limit_hit = true;
        return;
    }
    result.candidates.push(Candidate {
        column: (span.start - offset + 1) as u32,
        end_column: (span.end - offset + 1) as u32,
        line,
        sensitive,
        reason: reason(value, override_reason),
        span,
    });
}

/// Comments begin at a line boundary/whitespace, or immediately after a quote.
/// URL slashes inside an unquoted token are preserved.
fn comment_end(line: &str) -> usize {
    let bytes = line.as_bytes();
    let mut cursor = 0;
    while cursor < bytes.len() {
        if matches!(bytes[cursor], b'\'' | b'"' | b'\x60') {
            let (end, _, closed) = quoted_end(bytes, cursor);
            cursor = end + usize::from(closed);
            continue;
        }
        let boundary = cursor == 0
            || bytes[cursor - 1].is_ascii_whitespace()
            || matches!(bytes[cursor - 1], b'\'' | b'"' | b'\x60');
        if boundary && (bytes[cursor] == b'#' || bytes[cursor..].starts_with(b"//")) {
            return cursor;
        }
        cursor += 1;
    }
    line.len()
}

pub(crate) fn extract(text: &str, changed: &BTreeSet<u32>, cap: usize) -> Extraction {
    let mut result = Extraction {
        candidates: Vec::new(),
        limit_hit: false,
    };
    let mut offset = 0;
    for (index, physical) in text.split_inclusive('\n').enumerate() {
        let line_number = (index + 1) as u32;
        let line = physical.trim_end_matches('\n').trim_end_matches('\r');
        if !changed.contains(&line_number) {
            offset += physical.len();
            continue;
        }
        let line = &line[..comment_end(line)];
        let assignment = ASSIGNMENT
            .captures(line)
            .filter(|c| !line[c.get(0).expect("whole match").end()..].starts_with(['=', '>']));
        if let Some(assignment) = assignment {
            let key = assignment
                .get(1)
                .or(assignment.get(2))
                .or(assignment.get(3))
                .expect("key");
            let sensitive = sensitive_key(key.as_str());
            let start = assignment.get(0).expect("whole match").end();
            let rhs = line[start..].trim_end();
            let rhs = rhs.strip_suffix([',', ';']).unwrap_or(rhs).trim_end();
            let end = start + rhs.len();
            if rhs.starts_with(['\'', '"']) {
                let (close, escaped, closed) = quoted_end(line.as_bytes(), start);
                let triple = line.as_bytes()[start..].starts_with(&[line.as_bytes()[start]; 3]);
                let full_literal = closed && close + 1 == end;
                let override_reason = if triple {
                    Some("multiline_delimiter_unsupported")
                } else if !closed {
                    Some("unterminated_literal")
                } else if !full_literal {
                    Some("unsupported_expression")
                } else if escaped {
                    Some("escaped_literal")
                } else {
                    None
                };
                let span = if full_literal && !triple {
                    start + 1..close
                } else {
                    start..end
                };
                emit(
                    &mut result,
                    text,
                    offset + span.start..offset + span.end,
                    offset,
                    line_number,
                    sensitive,
                    override_reason,
                    cap,
                );
            } else {
                let bare = !rhs.is_empty()
                    && rhs
                        .bytes()
                        .all(|b| b.is_ascii_alphanumeric() || b"_./:@%-".contains(&b));
                if bare || sensitive || rhs.len() >= 8 {
                    emit(
                        &mut result,
                        text,
                        offset + start..offset + end,
                        offset,
                        line_number,
                        sensitive,
                        (!bare).then_some("unsupported_expression"),
                        cap,
                    );
                }
            }
        } else {
            let bytes = line.as_bytes();
            let mut cursor = 0;
            while cursor < bytes.len() {
                if !matches!(bytes[cursor], b'\'' | b'"' | b'\x60') {
                    cursor += 1;
                    continue;
                }
                let start = cursor;
                let (close, escaped, closed) = quoted_end(bytes, start);
                let triple = bytes[start..].starts_with(&[bytes[start]; 3]);
                let concatenated = line[..start].trim_end().ends_with('+')
                    || (closed && line[close + 1..].trim_start().starts_with('+'));
                let override_reason = if bytes[start] == b'\x60' || triple {
                    Some("multiline_or_template_unsupported")
                } else if !closed {
                    Some("unterminated_literal")
                } else if concatenated {
                    Some("unsupported_expression")
                } else if escaped {
                    Some("escaped_literal")
                } else {
                    None
                };
                let end = if triple { bytes.len() } else { close };
                emit(
                    &mut result,
                    text,
                    offset + start + 1..offset + end,
                    offset,
                    line_number,
                    false,
                    override_reason,
                    cap,
                );
                cursor = if triple {
                    bytes.len()
                } else {
                    close + usize::from(closed)
                };
                if result.limit_hit {
                    break;
                }
            }
        }
        if result.limit_hit {
            break;
        }
        offset += physical.len();
    }
    result
}
