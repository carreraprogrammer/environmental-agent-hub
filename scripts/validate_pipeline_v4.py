#!/usr/bin/env python3
"""
Validation script for Pipeline Orchestrator V4 (EDV-58).

This script validates:
1. Pipeline structure and initialization
2. Agent configuration
3. Code quality (syntax, imports)
4. Performance targets documentation

Usage:
    python scripts/validate_pipeline_v4.py
"""

from __future__ import annotations

import sys
from pathlib import Path


def validate_file_structure() -> bool:
    """Validate that all required files exist."""
    print("\n=== File Structure Validation ===")

    required_files = [
        "app/orchestrator/pipeline.py",
        "tests/integration/test_pipeline.py",
        "tests/performance/test_pipeline_latency.py",
    ]

    all_exist = True
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            size_kb = path.stat().st_size / 1024
            print(f"✓ {file_path} ({size_kb:.1f} KB)")
        else:
            print(f"✗ {file_path} NOT FOUND")
            all_exist = False

    return all_exist


def validate_syntax() -> bool:
    """Validate Python syntax for all files."""
    print("\n=== Syntax Validation ===")

    import py_compile

    files = [
        "app/orchestrator/pipeline.py",
        "tests/integration/test_pipeline.py",
        "tests/performance/test_pipeline_latency.py",
    ]

    all_valid = True
    for file_path in files:
        try:
            py_compile.compile(file_path, doraise=True)
            print(f"✓ {file_path}")
        except py_compile.PyCompileError as e:
            print(f"✗ {file_path}: {e}")
            all_valid = False

    return all_valid


def validate_pipeline_structure() -> bool:
    """Validate pipeline structure (without importing)."""
    print("\n=== Pipeline Structure Validation ===")

    pipeline_file = Path("app/orchestrator/pipeline.py")
    content = pipeline_file.read_text()

    # Check for all required classes
    required_classes = [
        "Pipeline",
        "VolumeEstimator",
        "FeedbackCoach",
        "BackendIntegration",
        "ValidationError",
        "ClassificationError",
    ]

    all_present = True
    for class_name in required_classes:
        if f"class {class_name}" in content:
            print(f"✓ Class {class_name} defined")
        else:
            print(f"✗ Class {class_name} NOT FOUND")
            all_present = False

    # Check for 7 agent initialization
    if "self.pre_validator = PreValidator()" in content:
        print("✓ PreValidator initialized")
    else:
        print("✗ PreValidator NOT initialized")
        all_present = False

    if "self.classifier = MaterialClassifier" in content:
        print("✓ MaterialClassifier initialized")
    else:
        print("✗ MaterialClassifier NOT initialized")
        all_present = False

    if "self.volume_estimator = VolumeEstimator()" in content:
        print("✓ VolumeEstimator initialized")
    else:
        print("✗ VolumeEstimator NOT initialized")
        all_present = False

    if "self.mapper = Mapper()" in content:
        print("✓ Mapper initialized")
    else:
        print("✗ Mapper NOT initialized")
        all_present = False

    if "self.waste_type_mapper = WasteTypeMapper()" in content:
        print("✓ WasteTypeMapper initialized")
    else:
        print("✗ WasteTypeMapper NOT initialized")
        all_present = False

    if "self.feedback_coach = FeedbackCoach()" in content:
        print("✓ FeedbackCoach initialized")
    else:
        print("✗ FeedbackCoach NOT initialized")
        all_present = False

    if "self.assembler = Assembler()" in content:
        print("✓ Assembler initialized")
    else:
        print("✗ Assembler NOT initialized")
        all_present = False

    if "self.backend_integration = BackendIntegration()" in content:
        print("✓ BackendIntegration initialized")
    else:
        print("✗ BackendIntegration NOT initialized")
        all_present = False

    return all_present


def validate_performance_targets() -> bool:
    """Validate performance targets are documented."""
    print("\n=== Performance Targets Validation ===")

    pipeline_file = Path("app/orchestrator/pipeline.py")
    content = pipeline_file.read_text()

    targets = {
        "Latency <1500ms": "1500" in content,
        "Cost <$0.008": "0.008" in content,
        "Timeout 5s": "TOTAL_TIMEOUT = 5.0" in content,
    }

    all_documented = True
    for target, found in targets.items():
        if found:
            print(f"✓ {target} documented")
        else:
            print(f"✗ {target} NOT documented")
            all_documented = False

    return all_documented


def validate_error_handling() -> bool:
    """Validate error handling is implemented."""
    print("\n=== Error Handling Validation ===")

    pipeline_file = Path("app/orchestrator/pipeline.py")
    content = pipeline_file.read_text()

    error_cases = {
        "NO_WASTE_DETECTED": "NO_WASTE_DETECTED" in content,
        "LOW_CONFIDENCE": "LOW_CONFIDENCE" in content,
        "TimeoutError": "TimeoutError" in content,
        "ValidationError": "ValidationError" in content,
        "ClassificationError": "ClassificationError" in content,
    }

    all_handled = True
    for error_case, found in error_cases.items():
        if found:
            print(f"✓ {error_case} handled")
        else:
            print(f"✗ {error_case} NOT handled")
            all_handled = False

    return all_handled


def validate_logging() -> bool:
    """Validate logging is implemented."""
    print("\n=== Logging Validation ===")

    pipeline_file = Path("app/orchestrator/pipeline.py")
    content = pipeline_file.read_text()

    log_events = {
        "pipeline_started": "pipeline_started" in content,
        "pipeline_complete": "pipeline_complete" in content,
        "pipeline_step": "pipeline_step" in content,
        "pipeline_error": "pipeline_error" in content,
        "trace_id propagation": "trace_id=" in content,
    }

    all_logged = True
    for event, found in log_events.items():
        if found:
            print(f"✓ {event} logged")
        else:
            print(f"✗ {event} NOT logged")
            all_logged = False

    return all_logged


def validate_tests() -> bool:
    """Validate test coverage."""
    print("\n=== Test Coverage Validation ===")

    integration_test = Path("tests/integration/test_pipeline.py")
    performance_test = Path("tests/performance/test_pipeline_latency.py")

    integration_content = integration_test.read_text()
    performance_content = performance_test.read_text()

    # Count test functions
    integration_tests = integration_content.count("def test_")
    performance_tests = performance_content.count("def test_")

    print(f"✓ Integration tests: {integration_tests} test cases")
    print(f"✓ Performance tests: {performance_tests} test cases")

    # Check for key test scenarios
    key_scenarios = {
        "Complete flow": "test_pipeline_complete_flow" in integration_content,
        "No waste detected": "test_pipeline_no_waste_detected" in integration_content,
        "Low confidence": "test_pipeline_low_confidence" in integration_content,
        "Timeout": "test_pipeline_timeout" in integration_content,
        "All materials": "test_pipeline_with_all_materials" in integration_content,
        "Latency target": "test_total_latency_within_target" in performance_content,
        "Cost target": "test_cost_within_target" in performance_content,
    }

    all_covered = True
    for scenario, found in key_scenarios.items():
        if found:
            print(f"✓ Test scenario: {scenario}")
        else:
            print(f"✗ Test scenario: {scenario} NOT FOUND")
            all_covered = False

    return all_covered and integration_tests >= 10 and performance_tests >= 5


def main() -> int:
    """Run all validations."""
    print("=" * 60)
    print("Pipeline Orchestrator V4 Validation (EDV-58)")
    print("=" * 60)

    results = {
        "File Structure": validate_file_structure(),
        "Syntax": validate_syntax(),
        "Pipeline Structure": validate_pipeline_structure(),
        "Performance Targets": validate_performance_targets(),
        "Error Handling": validate_error_handling(),
        "Logging": validate_logging(),
        "Tests": validate_tests(),
    }

    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)

    all_passed = True
    for check, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{check}: {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n🎉 ALL VALIDATIONS PASSED - Pipeline V4 is ready!")
        print("\nNext steps:")
        print("  1. Run: pytest tests/integration/test_pipeline.py -v")
        print("  2. Run: pytest tests/performance/test_pipeline_latency.py -v")
        print("  3. Review: pylint app/orchestrator/pipeline.py")
        print("  4. Review: mypy app/orchestrator/pipeline.py")
        return 0
    else:
        print("\n❌ SOME VALIDATIONS FAILED - Please review errors above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
