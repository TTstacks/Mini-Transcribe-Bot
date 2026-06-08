import json

from rest_framework.exceptions import ValidationError


ALLOWED_SENTIMENTS = {"positive", "neutral", "negative"}
REQUIRED_REPORT_KEYS = {"summary", "topics", "sentiment", "action_items"}


def parse_and_validate_report(raw_report):
    if isinstance(raw_report, str):
        try:
            report = json.loads(raw_report)
        except json.JSONDecodeError as exc:
            raise ValidationError({"report": "LLM returned invalid JSON."}) from exc
    else:
        report = raw_report

    if not isinstance(report, dict):
        raise ValidationError({"report": "LLM report must be a JSON object."})

    missing_keys = REQUIRED_REPORT_KEYS - set(report)
    if missing_keys:
        raise ValidationError(
            {"report": f"LLM report is missing keys: {', '.join(sorted(missing_keys))}."}
        )

    if not isinstance(report["summary"], str) or not report["summary"].strip():
        raise ValidationError({"report": "Report summary must be a non-empty string."})

    if not isinstance(report["topics"], list) or not all(
        isinstance(topic, str) for topic in report["topics"]
    ):
        raise ValidationError({"report": "Report topics must be a list of strings."})

    if report["sentiment"] not in ALLOWED_SENTIMENTS:
        raise ValidationError(
            {"report": "Report sentiment must be positive, neutral, or negative."}
        )

    if not isinstance(report["action_items"], list) or not all(
        isinstance(item, str) for item in report["action_items"]
    ):
        raise ValidationError(
            {"report": "Report action_items must be a list of strings."}
        )

    return {
        "summary": report["summary"],
        "topics": report["topics"],
        "sentiment": report["sentiment"],
        "action_items": report["action_items"],
    }

