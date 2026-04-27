"""
Executor module to run Karate tests using Maven.
"""
import os
import subprocess
import logging
import time
import requests
from dataclasses import dataclass
from typing import Optional, List

from config.settings import get_settings
from executor.report_parser import parse_karate_reports, TestReport

logger = logging.getLogger("karate_ai.executor")

@dataclass
class ExecutionResult:
    exit_code: int
    stdout: str
    stderr: str
    report: TestReport
    success: bool


def start_mock_server(settings) -> Optional[subprocess.Popen]:
    """Start the WireMock standalone server."""
    if not settings.wiremock_auto_start:
        return None
        
    jar_path = settings.wiremock_jar_path
    if not os.path.exists(jar_path):
        logger.warning(f"WireMock JAR not found at {jar_path}. Proceeding without mock server.")
        return None
        
    logger.info(f"Starting WireMock on port {settings.wiremock_port}...")
    
    # We run wiremock from the karate_project/wiremock directory so it finds mappings/
    wiremock_dir = os.path.dirname(jar_path)
    
    cmd = [
        "java", "-jar", os.path.basename(jar_path),
        "--port", str(settings.wiremock_port)
    ]
    
    process = subprocess.Popen(
        cmd,
        cwd=wiremock_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Wait for it to be ready
    for _ in range(10):
        try:
            resp = requests.get(f"http://localhost:{settings.wiremock_port}/__admin/")
            if resp.status_code == 200:
                logger.info("WireMock started successfully.")
                return process
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(1)
        
    logger.warning("WireMock did not start in time. Execution may fail.")
    return process


def stop_mock_server(process: Optional[subprocess.Popen]):
    """Stop the WireMock server if we started it."""
    if process:
        logger.info("Stopping WireMock...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def run_tests(feature_path: Optional[str] = None, env: Optional[str] = None) -> ExecutionResult:
    """
    Run Karate tests via Maven subprocess.
    
    Args:
        feature_path: Path to a specific feature file or directory. 
                      If None, runs all generated features.
        env: Karate environment (dev, staging, etc.). Defaults to settings.
    """
    settings = get_settings()
    
    target_env = env or settings.karate_env
    
    # Default path if none specified
    if not feature_path:
        feature_path = "classpath:karate/generated"
        
    cmd = [
        "mvn", 
        "test", 
        f"-Dkarate.options={feature_path}", 
        f"-Dkarate.env={target_env}",
        "-Dkarate.config.dir=classpath:karate"
    ]
    
    env_vars = os.environ.copy()
    if settings.java_home:
        env_vars["JAVA_HOME"] = settings.java_home
        # Prepend to PATH so the correct 'java' is used
        env_vars["PATH"] = f"{settings.java_home}/bin:{env_vars.get('PATH', '')}"
        
    logger.info(f"Executing: {' '.join(cmd)}")
    logger.info(f"Working directory: {settings.karate_project_path}")
    logger.info(f"JAVA_HOME: {env_vars.get('JAVA_HOME')}")
    
    mock_process = start_mock_server(settings)
    
    try:
        # We run from the karate_project directory
        result = subprocess.run(
            cmd,
            cwd=settings.karate_project_path,
            env=env_vars,
            capture_output=True,
            text=True,
            timeout=settings.maven_execution_timeout
        )
        
        # Parse the reports
        report = parse_karate_reports(settings.karate_report_dir)
        
        # The build fails if any test fails, so exit_code != 0 is expected
        success = report.failed == 0 and report.total > 0 and result.returncode == 0
        
        return ExecutionResult(
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            report=report,
            success=success
        )
        
    except subprocess.TimeoutExpired as e:
        logger.error(f"Execution timed out after {settings.maven_execution_timeout} seconds")
        return ExecutionResult(
            exit_code=-1,
            stdout=e.stdout.decode('utf-8') if isinstance(e.stdout, bytes) else (e.stdout or ""),
            stderr=e.stderr.decode('utf-8') if isinstance(e.stderr, bytes) else (e.stderr or "Timeout expired"),
            report=TestReport(errors=1),
            success=False
        )
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        return ExecutionResult(
            exit_code=-1,
            stdout="",
            stderr=str(e),
            report=TestReport(errors=1),
            success=False
        )
    finally:
        stop_mock_server(mock_process)
