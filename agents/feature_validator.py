"""
Karate Feature Validator — basic syntax linting for generated .feature files.
"""
import json
import re
from typing import List


def validate_feature(content: str) -> List[str]:
    """
    Validate a generated Karate .feature file for basic syntax correctness.
    
    Returns a list of error messages. Empty list means the file is valid.
    """
    errors = []
    lines = content.strip().split("\n")

    if not lines:
        errors.append("Feature file is empty")
        return errors

    # Check for Feature: keyword
    has_feature = any(line.strip().startswith("Feature:") for line in lines)
    if not has_feature:
        errors.append("Missing 'Feature:' declaration")

    # Check for at least one Scenario: or Scenario Outline:
    has_scenario = any(
        line.strip().startswith("Scenario:") or line.strip().startswith("Scenario Outline:")
        for line in lines
    )
    if not has_scenario:
        errors.append("Missing 'Scenario:' or 'Scenario Outline:' declaration")

    # Check for Given url/path step
    has_given = any(
        re.match(r"\s*(Given |And |\* )(url|path)\s", line)
        for line in lines
    )
    if not has_given:
        errors.append("Missing 'Given url' or 'Given path' step")

    # Check for When method step
    has_when = any(
        re.match(r"\s*(When |And |\* )method\s", line)
        for line in lines
    )
    if not has_when:
        errors.append("Missing 'When method' step")

    # Check for Then status assertion
    has_then = any(
        re.match(r"\s*(Then |And |\* )status\s", line)
        for line in lines
    )
    if not has_then:
        errors.append("Missing 'Then status' assertion")

    # Validate JSON payloads in request steps
    for i, line in enumerate(lines):
        stripped = line.strip()
        if re.match(r"(And |Given |\* )request\s+\{", stripped):
            # Extract the JSON part
            json_start = stripped.index("{")
            json_str = stripped[json_start:]
            try:
                # Karate uses relaxed JSON (unquoted keys), so we can't
                # strictly validate with json.loads. Just check basic balance.
                _check_brace_balance(json_str)
            except ValueError as e:
                errors.append(f"Line {i+1}: Malformed request body — {e}")

    return errors


def _check_brace_balance(text: str) -> None:
    """Check that braces and brackets are balanced."""
    stack = []
    in_string = False
    escape = False
    for ch in text:
        if escape:
            escape = False
            continue
        if ch == '\\':
            escape = True
            continue
        if ch in ('"', "'") and not in_string:
            in_string = ch
            continue
        if in_string and ch == in_string:
            in_string = False
            continue
        if in_string:
            continue
        if ch in ('{', '[', '('):
            stack.append(ch)
        elif ch in ('}', ']', ')'):
            if not stack:
                raise ValueError(f"Unexpected closing '{ch}'")
            opening = stack.pop()
            expected = {'}': '{', ']': '[', ')': '('}
            if opening != expected[ch]:
                raise ValueError(f"Mismatched '{opening}' and '{ch}'")
    if stack:
        raise ValueError(f"Unclosed '{stack[-1]}'")
