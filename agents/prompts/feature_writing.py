"""
Prompt templates for the Karate Feature Writer agent.
"""

SYSTEM_PROMPT = """You are a Karate Framework expert with deep knowledge of its DSL, assertions, and best practices.
You write clean, well-structured .feature files that follow Karate conventions.
You always include proper Background setup, use Karate's match assertions (not generic assert),
and add comments explaining which business rule each scenario tests.

You produce valid Karate DSL syntax that can be executed directly."""


def build_user_prompt(
    scenario_json: str,
    karate_reference: str,
    existing_test_patterns: str,
    dominant_data_pattern: str = "inline_examples",
    endpoint_tag: str = ""
) -> str:
    data_pattern_directive = _get_data_pattern_directive(dominant_data_pattern)

    return f"""Convert the following test scenario into a valid Karate .feature file.

## Scenario
{scenario_json}

## Karate Syntax Reference
{karate_reference}

## Existing Test Patterns (for style consistency)
{existing_test_patterns}

## Requirements
- Use proper Feature/Scenario/Given/When/Then structure
- Include a Background section for shared setup (base URL, auth headers)
- Use Karate's match assertions: `match`, `contains`, `==`, `#notnull`, `#present`
- Add comments explaining which business rule is being tested
- Tag scenarios with @category (e.g., @business_rule, @happy_path)
- Use JSON embedded in the feature file for request bodies
- Include proper status code assertions with `Then status <code>`
{data_pattern_directive}

## Output Format
Return ONLY the .feature file content. Do not wrap it in markdown code fences.
Start directly with `Feature:` and end with the last step of the last scenario."""


def _get_data_pattern_directive(pattern: str) -> str:
    if pattern == "csv_read":
        return """
## Data Pattern Directive
This project uses CSV files for test data. For data-driven scenarios:
- Use `Scenario Outline:` with placeholders like `<fieldName>`
- Reference CSV data with: `* def testData = read('testdata/<filename>.csv')`
- Also provide the CSV file content separately in your response, marked with:
  COMPANION_CSV_START:<filename>
  <csv content>
  COMPANION_CSV_END
"""
    elif pattern == "excel_read":
        return """
## Data Pattern Directive
This project uses Excel files for test data. For data-driven scenarios:
- Use `Scenario Outline:` with placeholders
- Reference data with: `* def testData = read('testdata/<filename>.xlsx')`
- Since we cannot generate binary Excel files, provide the data as CSV format and
  note it should be converted to Excel. Mark with:
  COMPANION_CSV_START:<filename>
  <csv content>
  COMPANION_CSV_END
"""
    else:
        return """
## Data Pattern Directive
For data-driven scenarios, use inline Examples tables:
```
Scenario Outline: <description>
  ...
  Examples:
    | field1 | field2 |
    | val1   | val2   |
```
"""
