#!/usr/bin/env python3
"""
Final validation that all §14 fixes are working
"""

import json
import sys
from pathlib import Path

import yaml


def validate_json_logging():
    """Validate §14.2 JSON logging"""
    sys.path.insert(0, str(Path(__file__).parent / "src"))
    from arxivbot.monitoring.structured_logger import get_logger

    logger = get_logger("validator")

    # Capture output
    import io

    buffer = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buffer

    # Generate log
    logger.info("Test message", source="arxiv", papers=100)

    # Restore stdout
    sys.stdout = old_stdout
    output = buffer.getvalue().strip()

    # Validate JSON
    try:
        log_entry = json.loads(output)
        required = ["msg", "ts", "level", "module", "extra"]
        missing = [f for f in required if f not in log_entry]
        if missing:
            print(f"❌ §14.2 FAILED: Missing fields {missing}")
            return False
        print("✅ §14.2 Structured JSON Logging: COMPLIANT")
        return True
    except json.JSONDecodeError:
        print(f"❌ §14.2 FAILED: Invalid JSON")
        return False


def validate_alert_expressions():
    """Validate §14.4 alert expressions"""
    alert_file = Path(__file__).parent / "infrastructure" / "alert.rules.yml"

    with open(alert_file) as f:
        config = yaml.safe_load(f)

    required = {
        "NoNewPapers": "increase(papers_saved_total[3d]) == 0",
        "DigestLate": "(time() - digest_sent_timestamp) > 32400",
        "LLMQuota90": "summary_tokens_total > (0.9 * 1000000)",
    }

    found = {}
    for group in config["groups"]:
        for rule in group["rules"]:
            name = rule["alert"]
            if name in required:
                found[name] = rule["expr"].strip()

    all_correct = True
    for alert, expected in required.items():
        actual = found.get(alert, "NOT FOUND")
        if expected in actual:
            print(f"✅ §14.4 Alert {alert}: COMPLIANT")
        else:
            print(f"❌ §14.4 Alert {alert}: FAILED")
            print(f"  Expected: {expected}")
            print(f"  Actual: {actual}")
            all_correct = False

    return all_correct


def validate_metrics_labels():
    """Validate §14.1 metric labels"""
    metrics_file = Path(__file__).parent / "src" / "arxivbot" / "monitoring" / "metrics.py"

    with open(metrics_file) as f:
        content = f.read()

    checks = [
        ("harvest_duration_seconds", "labelnames=['source']"),
        ("summary_tokens_total", "labelnames=['model']"),
        ("vector_query_seconds", "labelnames=['backend']"),
    ]

    all_correct = True
    for metric, expected in checks:
        if expected in content:
            print(f"✅ §14.1 Metric {metric}: COMPLIANT")
        else:
            print(f"❌ §14.1 Metric {metric}: FAILED")
            all_correct = False

    return all_correct


def validate_tracing_spans():
    """Validate §14.3 tracing spans"""
    tracing_file = Path(__file__).parent / "src" / "arxivbot" / "monitoring" / "tracing.py"

    if not tracing_file.exists():
        print("❌ §14.3 Tracing: File not found")
        return False

    with open(tracing_file) as f:
        content = f.read()

    required_spans = ["def harvest_span", "def score_span", "def download_span", "def llm_span"]

    all_found = True
    for span in required_spans:
        if span in content:
            span_name = span.replace("def ", "")
            print(f"✅ §14.3 Span {span_name}: IMPLEMENTED")
        else:
            print(f"❌ §14.3 Span {span}: NOT FOUND")
            all_found = False

    return all_found


def main():
    print("=" * 60)
    print("🔍 VALIDATING ALL §14 COMPLIANCE FIXES")
    print("=" * 60)
    print()

    results = {
        "§14.1 Metrics": validate_metrics_labels(),
        "§14.2 Logging": validate_json_logging(),
        "§14.3 Tracing": validate_tracing_spans(),
        "§14.4 Alerts": validate_alert_expressions(),
    }

    print()
    print("=" * 60)
    print("📊 FINAL RESULTS")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for section, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{section:15} {status}")

    compliance = (passed / total) * 100
    print("-" * 60)
    print(f"Overall: {passed}/{total} sections compliant ({compliance:.0f}%)")

    if compliance >= 85:
        print("\n🎉 TARGET COMPLIANCE ACHIEVED (≥85%)")
    else:
        print(f"\n⚠️ Below target compliance (<85%)")

    return compliance >= 85


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
