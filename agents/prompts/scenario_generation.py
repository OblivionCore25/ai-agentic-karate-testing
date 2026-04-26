"""
Prompt templates for the Scenario Generator agent.
"""

SYSTEM_PROMPT = """You are a senior QA engineer with deep backend knowledge and expertise in API testing.
You specialize in identifying test scenarios that go beyond simple contract testing — you analyze
source code to find business rules, validation logic, error handling paths, and edge cases that
would be missed by spec-only test generation.

You always produce structured JSON output following the exact schema requested."""


def build_user_prompt(
    endpoint_tag: str,
    spec_context: str,
    code_context: str,
    test_context: str,
    dominant_data_pattern: str = "inline_examples"
) -> str:
    data_pattern_instruction = ""
    if dominant_data_pattern == "csv_read":
        data_pattern_instruction = """
DATA PATTERN NOTE: This project uses CSV files for test data (via Karate's read() function).
When defining test_data, structure it as rows that could be placed in a CSV file.
Include a variety of valid and invalid data combinations."""
    elif dominant_data_pattern == "excel_read":
        data_pattern_instruction = """
DATA PATTERN NOTE: This project uses Excel files for test data (via Karate's read() function).
When defining test_data, structure it as rows that could be placed in an Excel spreadsheet.
Include a variety of valid and invalid data combinations."""

    return f"""You are generating test scenarios for the endpoint: {endpoint_tag}

## API Specification Context
{spec_context}

## Source Code Context (Business Logic)
{code_context}

## Existing Test Patterns
{test_context}
{data_pattern_instruction}

Generate a comprehensive list of test scenarios. For each scenario provide:
1. **name**: Descriptive, Gherkin-style scenario name
2. **category**: One of: happy_path, business_rule, validation, error_handling, boundary, security
3. **description**: What is being tested and why
4. **expected_outcome**: The expected result
5. **knowledge_sources**: Which spec/code/test chunks informed this scenario (be specific — cite method names, spec sections)
6. **confidence**: high, medium, or low — based on how well-grounded the scenario is in the provided context
7. **preconditions**: Any setup steps required (auth tokens, prerequisite data, etc.)
8. **test_data**: Key-value pairs for the test (request body fields, query params, expected values)

IMPORTANT: Go beyond contract testing. Use the source code context to identify:
- Business rule branches (if/else, switch statements)
- Validation logic (annotations like @NotNull, @Valid, custom validators)
- Error handling paths (try/catch, custom exceptions, error responses)
- Data transformation logic (mappers, converters, calculations)
- Boundary conditions (min/max values, empty collections, null fields)

Generate at least 5 scenarios covering multiple categories. Prioritize business_rule and
validation scenarios that would NOT be discoverable from the API spec alone.

Return your response as a JSON object with a "scenarios" key containing an array of scenario objects."""
