"""
Prompt templates for the Karate Feature Writer agent.
"""

SYSTEM_PROMPT = """You are a Karate Framework expert with deep knowledge of its DSL, assertions, and best practices.
You write clean, well-structured .feature files that follow Karate conventions.
You always include proper Background setup, use Karate's match assertions (not generic assert),
and add comments explaining which business rule each scenario tests.

You produce valid Karate DSL syntax that can be executed directly.

You also know how to use Karate's built-in JDBC support to verify database state after API calls.
When database schema context is available, you include JDBC verification steps to confirm
that the API operation correctly modified the database."""


def build_user_prompt(
    scenario_json: str,
    karate_reference: str,
    existing_test_patterns: str,
    dominant_data_pattern: str = "inline_examples",
    endpoint_tag: str = "",
    schema_context: str = ""
) -> str:
    data_pattern_directive = _get_data_pattern_directive(dominant_data_pattern)
    jdbc_directive = _get_jdbc_directive(schema_context)

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
{jdbc_directive}

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


def _get_jdbc_directive(schema_context: str) -> str:
    """Build JDBC verification directive when database schema is available."""
    if not schema_context or schema_context.strip() == "(no context available)" or schema_context.strip() == "":
        return ""

    return f"""
## JDBC Database Verification Directive
This project has database schema context available. After API calls that CREATE, UPDATE, or DELETE
resources, include JDBC verification steps to confirm the database was modified correctly.

### Database Schema
{schema_context}

### JDBC Step Syntax (Karate built-in)
Use Karate's built-in `karate.callSingle()` or direct Java interop to run SQL queries.
The database connection is configured in karate-config.js with these variables:
- `dbUrl` — JDBC connection string
- `dbUser` — database username
- `dbPassword` — database password
- `dbDriverClassName` — JDBC driver class

Use this pattern for JDBC verification:

```
# After a POST that creates a record:
* def DbUtils = Java.type('com.intuit.karate.core.ScenarioEngine')
* def config = {{ dbUrl: dbUrl, dbUser: dbUser, dbPassword: dbPassword, dbDriverClassName: dbDriverClassName }}
* def db = new com.intuit.karate.core.MockUtils()

# Simpler approach using karate.call with a helper:
* def query = "SELECT * FROM orders WHERE id = '" + response.id + "'"
* def dbResult = karate.callSingle('classpath:karate/helpers/db-query.feature', {{ query: query }})
* match dbResult.result[0].status == 'PENDING'
* match dbResult.result[0].total_amount == response.totalAmount
```

OR use the simpler inline Java JDBC approach:
```
# Verify database state after API call
* def jdbcUrl = dbUrl
* def props = new java.util.Properties()
* eval props.setProperty('user', dbUser)
* eval props.setProperty('password', dbPassword)
* def conn = java.sql.DriverManager.getConnection(jdbcUrl, props)
* def stmt = conn.prepareStatement("SELECT status, total_amount FROM orders WHERE id = ?")
* eval stmt.setObject(1, java.util.UUID.fromString(response.id))
* def rs = stmt.executeQuery()
* eval rs.next()
* match rs.getString('status') == 'PENDING'
* match rs.getBigDecimal('total_amount').doubleValue() == response.totalAmount
* eval rs.close()
* eval stmt.close()
* eval conn.close()
```

### Rules for JDBC Steps
1. ONLY add JDBC verification for mutating operations (POST, PUT, PATCH, DELETE) — NOT for GET requests
2. Place JDBC verification AFTER the API response assertions
3. Always close the connection in a finally-like pattern
4. Match database column names exactly as they appear in the schema (snake_case)
5. Use the schema above to determine the correct table and column names
6. For happy_path scenarios: verify the record was created/updated correctly
7. For error/validation scenarios: verify the record was NOT created (count == 0)
"""
