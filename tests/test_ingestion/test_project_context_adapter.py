"""
Tests for the ProjectContextAdapter — auto-discovery of utility features
and config files from a Karate project directory.
"""
import os
import pytest
import tempfile
import shutil
from ingestion.project_context_adapter import ProjectContextAdapter


@pytest.fixture
def project_dir():
    """Create a temporary Karate project with utility features and configs."""
    base = tempfile.mkdtemp()

    # Create utility feature in utils/ directory
    utils_dir = os.path.join(base, "utils")
    os.makedirs(utils_dir)
    with open(os.path.join(utils_dir, "db-connection.feature"), "w") as f:
        f.write("""Feature: Database Connection Helper

  Background:
    * def dbUrl = __arg.dbUrl
    * def dbUser = __arg.dbUser
    * def dbPassword = __arg.dbPassword

  Scenario:
    * def props = new java.util.Properties()
    * eval props.setProperty('user', dbUser)
    * eval props.setProperty('password', dbPassword)
    * def result = java.sql.DriverManager.getConnection(dbUrl, props)
""")

    # Create utility in common/ directory (no Scenario keyword)
    common_dir = os.path.join(base, "common")
    os.makedirs(common_dir)
    with open(os.path.join(common_dir, "date-utils.feature"), "w") as f:
        f.write("""Feature: Date Formatting Utility

  Background:
    * def now = new java.util.Date()
    * def sdf = new java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss")
    * def result = sdf.format(now)
""")

    # Create a regular test feature (should NOT be classified as utility)
    test_dir = os.path.join(base, "orders")
    os.makedirs(test_dir)
    with open(os.path.join(test_dir, "create-order.feature"), "w") as f:
        f.write("""Feature: Create Order Tests

  Scenario: Create a standard order
    Given url baseUrl + '/orders'
    And request { "customerId": "cust-001" }
    When method post
    Then status 201
""")

    # Create a feature file with __arg but outside utility dirs
    with open(os.path.join(test_dir, "aws-auth.feature"), "w") as f:
        f.write("""Feature: AWS Auth Helper

  Background:
    * def region = __arg.region
    * def roleArn = __arg.roleArn
    * def result = karate.callSingle('classpath:aws/assume-role.feature', { region: region })
""")

    # Create project-specific utility (nested)
    orders_utils = os.path.join(test_dir, "helpers")
    os.makedirs(orders_utils)
    with open(os.path.join(orders_utils, "order-setup.feature"), "w") as f:
        f.write("""Feature: Order Test Setup

  Background:
    * def customerId = karate.get('customerId', 'cust-001')
    * url baseUrl + '/orders'
    * def result = { customerId: customerId }
""")

    # Create karate-config.js
    with open(os.path.join(base, "karate-config.js"), "w") as f:
        f.write("""function fn() {
  var env = karate.env;
  var config = {};
  config.baseUrl = 'http://localhost:8080';
  config.dbUrl = 'jdbc:postgresql://localhost:5434/orders_db';
  config.dbUser = 'testuser';
  config.dbPassword = 'testpass';

  if (env == 'staging') {
    config.baseUrl = 'https://staging.example.com';
    config.dbUrl = 'jdbc:postgresql://staging-db:5432/orders_db';
  }
  return config;
}
""")

    yield base
    shutil.rmtree(base)


class TestProjectContextAdapter:
    def test_discovers_utility_in_utils_dir(self, project_dir):
        adapter = ProjectContextAdapter()
        utility_chunks, _ = adapter.ingest_separated(project_dir)
        names = [c.metadata["name"] for c in utility_chunks]
        assert "db-connection.feature" in names

    def test_discovers_utility_in_common_dir(self, project_dir):
        adapter = ProjectContextAdapter()
        utility_chunks, _ = adapter.ingest_separated(project_dir)
        names = [c.metadata["name"] for c in utility_chunks]
        assert "date-utils.feature" in names

    def test_ignores_regular_test_features(self, project_dir):
        adapter = ProjectContextAdapter()
        utility_chunks, _ = adapter.ingest_separated(project_dir)
        names = [c.metadata["name"] for c in utility_chunks]
        assert "create-order.feature" not in names

    def test_detects_arg_based_utility_outside_utility_dir(self, project_dir):
        adapter = ProjectContextAdapter()
        utility_chunks, _ = adapter.ingest_separated(project_dir)
        names = [c.metadata["name"] for c in utility_chunks]
        assert "aws-auth.feature" in names

    def test_discovers_config_files(self, project_dir):
        adapter = ProjectContextAdapter()
        _, config_chunks = adapter.ingest_separated(project_dir)
        names = [c.metadata["name"] for c in config_chunks]
        assert "karate-config.js" in names

    def test_config_extracts_variables(self, project_dir):
        adapter = ProjectContextAdapter()
        _, config_chunks = adapter.ingest_separated(project_dir)
        config_chunk = config_chunks[0]
        assert "baseUrl" in config_chunk.content
        assert "dbUrl" in config_chunk.content

    def test_utility_has_classpath(self, project_dir):
        adapter = ProjectContextAdapter()
        utility_chunks, _ = adapter.ingest_separated(project_dir)
        db_chunk = next(c for c in utility_chunks if c.metadata["name"] == "db-connection.feature")
        assert "classpath:" in db_chunk.metadata["classpath"]
        assert "utils/db-connection.feature" in db_chunk.metadata["classpath"]

    def test_utility_has_correct_origin_type(self, project_dir):
        adapter = ProjectContextAdapter()
        utility_chunks, config_chunks = adapter.ingest_separated(project_dir)
        for chunk in utility_chunks:
            assert chunk.origin_type == "utility"
        for chunk in config_chunks:
            assert chunk.origin_type == "config"

    def test_scope_tagging_global_vs_project(self, project_dir):
        adapter = ProjectContextAdapter()
        utility_chunks, _ = adapter.ingest_separated(project_dir)

        # utils/db-connection.feature → depth 2 → global
        db_chunk = next(c for c in utility_chunks if c.metadata["name"] == "db-connection.feature")
        assert db_chunk.metadata["scope"] == "global"

        # orders/helpers/order-setup.feature → depth 3 → project
        setup_chunk = next(c for c in utility_chunks if c.metadata["name"] == "order-setup.feature")
        assert setup_chunk.metadata["scope"] == "project"

    def test_extra_utility_dirs(self, project_dir):
        # Create a custom dir name with a feature that has a Scenario
        # (so content heuristics won't classify it as utility)
        custom_dir = os.path.join(project_dir, "custom_tools")
        os.makedirs(custom_dir)
        with open(os.path.join(custom_dir, "tool.feature"), "w") as f:
            f.write("Feature: Custom Tool\n\n  Scenario: run tool\n    * def result = 'hello'\n")

        # Without extra dirs — has Scenario so content heuristic won't trigger
        adapter1 = ProjectContextAdapter()
        chunks1, _ = adapter1.ingest_separated(project_dir)
        names1 = [c.metadata["name"] for c in chunks1]
        assert "tool.feature" not in names1

        # With extra dirs
        adapter2 = ProjectContextAdapter(extra_utility_dirs="custom_tools")
        chunks2, _ = adapter2.ingest_separated(project_dir)
        names2 = [c.metadata["name"] for c in chunks2]
        assert "tool.feature" in names2

    def test_empty_directory_returns_empty(self):
        empty_dir = tempfile.mkdtemp()
        try:
            adapter = ProjectContextAdapter()
            utility_chunks, config_chunks = adapter.ingest_separated(empty_dir)
            assert utility_chunks == []
            assert config_chunks == []
        finally:
            shutil.rmtree(empty_dir)

    def test_explicit_parameters_extracted(self, project_dir):
        adapter = ProjectContextAdapter()
        utility_chunks, _ = adapter.ingest_separated(project_dir)
        db_chunk = next(c for c in utility_chunks if c.metadata["name"] == "db-connection.feature")
        assert db_chunk.metadata["parameter_count"] >= 3
        assert "dbUrl" in db_chunk.content
        assert "explicit" in db_chunk.content

    def test_chunk_content_has_call_pattern(self, project_dir):
        adapter = ProjectContextAdapter()
        utility_chunks, _ = adapter.ingest_separated(project_dir)
        db_chunk = next(c for c in utility_chunks if c.metadata["name"] == "db-connection.feature")
        assert "Call Pattern:" in db_chunk.content
        assert "callonce read(" in db_chunk.content or "call read(" in db_chunk.content
