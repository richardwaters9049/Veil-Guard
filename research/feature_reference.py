"""Independent standard-library reference for veilguard.features.v1.

Only explicit, authored fixture tooling may print vectors. This module does not
read repositories, fit models, use filenames as features or perform inference.
"""
from collections import Counter
import math
import re

SCHEMA = "veilguard.features.v1"
NAMES = ("log_length", "shannon_entropy", "digit_ratio", "uppercase_ratio",
         "symbol_ratio", "keyword_proximity", "sensitive_assignment", "placeholder_similarity")
KEYWORDS = ("password", "passwd", "secret", "token", "credential", "apikey", "privatekey")
PLACEHOLDERS = ("changeme", "password", "example", "placeholder", "dummy", "test",
                "your_api_key_here", "replace_me", "not_a_real_secret")
WHITESPACE = "\t\n\v\f\r \x85\xa0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000"
ASSIGNMENT = re.compile(r"""^[\t-\r \x85\xa0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]*(?:"([A-Za-z_][A-Za-z0-9_.-]*)"|'([A-Za-z_][A-Za-z0-9_.-]*)'|([A-Za-z_][A-Za-z0-9_.-]*))[\t-\r \x85\xa0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]*[:=][\t-\r \x85\xa0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]*""")
QUOTED = re.compile(r""""(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\x60(?:\\.|[^\x60\\])*\x60""")


class FeatureError(ValueError):
    """Messages are fixed codes and never contain source or coordinates."""


def _span(line, start, end):
    if (not isinstance(start, int) or isinstance(start, bool)
            or not isinstance(end, int) or isinstance(end, bool)
            or len(line.encode("utf-8")) > 1_048_576 or "\n" in line or "\r" in line
            or start < 0 or start >= end or end > len(line.encode("utf-8"))):
        raise FeatureError("invalid_context")
    encoded = line.encode("utf-8")
    try:
        return encoded[start:end].decode("utf-8"), len(encoded[:start].decode("utf-8"))
    except UnicodeDecodeError:
        raise FeatureError("invalid_context") from None


def keyword_spans(line):
    tokens = []
    for word in re.finditer(r"[A-Za-z0-9]+", line):
        boundaries = [word.start()]
        boundaries.extend(i for i in range(word.start() + 1, word.end())
                          if "a" <= line[i - 1] <= "z" and "A" <= line[i] <= "Z")
        boundaries.append(word.end())
        tokens.extend(zip(boundaries, boundaries[1:]))
    matches = [(a, b) for a, b in tokens if line[a:b].lower() in KEYWORDS]
    matches.extend((a, d) for (a, b), (c, d) in zip(tokens, tokens[1:])
                   if (line[a:b] + line[c:d]).lower() in KEYWORDS)
    return [(len(line[:a].encode("utf-8")), len(line[:b].encode("utf-8")))
            for a, b in matches]


def keyword_proximity(line, start, end):
    _span(line, start, end)
    gaps = [start - b if b <= start else a - end
            for a, b in keyword_spans(line) if b <= start or a >= end]
    nearest = min(gaps, default=81)
    return 1.0 / (nearest + 1) if nearest <= 80 else 0.0


def _without_comment(line):
    cursor = 0
    while cursor < len(line):
        if line[cursor] in "'\"\x60":
            literal = QUOTED.match(line, cursor)
            if not literal:
                return line
            cursor = literal.end()
        elif (cursor == 0 or line[cursor - 1] in " \t\n\r\f" or line[cursor - 1] in "'\"\x60") and (
                line[cursor] == "#" or line.startswith("//", cursor)):
            return line[:cursor]
        else:
            cursor += 1
    return line


def _occurrences(physical):
    line = _without_comment(physical)
    assignment = ASSIGNMENT.match(line)
    if assignment and line[assignment.end():].startswith(("=", ">")):
        assignment = None
    if assignment:
        key = next(group for group in assignment.groups() if group is not None)
        start = assignment.end()
        rhs = line[start:].rstrip(WHITESPACE)
        if rhs.endswith((",", ";")):
            rhs = rhs[:-1].rstrip(WHITESPACE)
        if rhs.startswith(("'''", '"""')):
            return []
        if rhs.startswith(("'", '"')):
            literal = QUOTED.fullmatch(rhs)
            if not literal or "\\" in rhs:
                return []
            start, end = start + 1, start + len(rhs) - 1
        elif re.fullmatch(r"[A-Za-z0-9_./:@%\-]+", rhs):
            end = start + len(rhs)
        else:
            return []
        return [(start, end, bool(keyword_spans(key)))]
    found = []
    cursor = 0
    while cursor < len(line):
        opening = re.search("['\"\x60]", line[cursor:])
        if not opening:
            break
        start = cursor + opening.start()
        if line.startswith(line[start] * 3, start):
            break
        literal = QUOTED.match(line, start)
        if not literal:
            break
        end = literal.end()
        if (line[start] != "\x60" and "\\" not in literal.group()
                and not line[:start].rstrip(WHITESPACE).endswith("+")
                and not line[end:].lstrip(WHITESPACE).startswith("+")):
            found.append((start + 1, end - 1, False))
        cursor = end
    return found


def _levenshtein(left, right):
    # Full table here; Rust independently uses a rolling row.
    table = [[0] * (len(right) + 1) for _ in range(len(left) + 1)]
    for i in range(len(left) + 1):
        table[i][0] = i
    for j in range(len(right) + 1):
        table[0][j] = j
    for i, a in enumerate(left, 1):
        for j, b in enumerate(right, 1):
            table[i][j] = min(table[i - 1][j] + 1, table[i][j - 1] + 1,
                              table[i - 1][j - 1] + (a != b))
    return table[-1][-1]


def from_line(line, start, end):
    value, char_start = _span(line, start, end)
    match = next((sensitive for a, b, sensitive in _occurrences(line)
                  if a == char_start and b == char_start + len(value)), None)
    if match is None or not 8 <= len(value) <= 256 or any(not " " <= c <= "~" for c in value):
        raise FeatureError("unsupported_literal")
    length = len(value)
    entropy = -sum((count / length) * math.log2(count / length)
                   for count in Counter(value).values())
    similarity = max(1 - _levenshtein(value.lower(), word) / max(length, len(word))
                     for word in PLACEHOLDERS)
    vector = [math.log1p(length), entropy,
              sum("0" <= c <= "9" for c in value) / length,
              sum("A" <= c <= "Z" for c in value) / length,
              sum(not c.isascii() or not c.isalnum() for c in value) / length,
              keyword_proximity(line, start, end), float(match), similarity]
    if (len(vector) != 8 or any(not math.isfinite(x) for x in vector)
            or not math.log(9) <= vector[0] <= math.log(257)
            or not 0 <= vector[1] <= math.log2(min(95, length)) + 1e-12
            or any(not 0 <= x <= 1 for x in vector[2:])):
        raise FeatureError("invalid_vector")
    return vector


def _eight(values):
    if len(values) != 8 or any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in values):
        raise FeatureError("invalid_vector")
    try:
        result = [float(v) for v in values]
    except OverflowError:
        raise FeatureError("invalid_vector") from None
    if any(not math.isfinite(v) for v in result):
        raise FeatureError("invalid_vector")
    return result


def standardise(values, means, scales):
    values, means, scales = map(_eight, (values, means, scales))
    if any(scale <= 0 for scale in scales):
        raise FeatureError("invalid_vector")
    try:
        return _eight([(v - mean) / scale for v, mean, scale in zip(values, means, scales)])
    except (OverflowError, ZeroDivisionError):
        raise FeatureError("invalid_vector") from None


def squared_distance_contributions(left, right):
    left, right = map(_eight, (left, right))
    try:
        result = _eight([(a - b) ** 2 for a, b in zip(left, right)])
        if not math.isfinite(sum(result)):
            raise FeatureError("invalid_vector")
        return result
    except OverflowError:
        raise FeatureError("invalid_vector") from None
