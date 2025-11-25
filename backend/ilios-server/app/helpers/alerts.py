"""Alerts related utilities"""

from app.models.alert import AlertSeverity

SEVERITIES_PRIORITY = [
    AlertSeverity.critical,
    AlertSeverity.warning,
    AlertSeverity.informational,
]


def get_max_severity(input_severities):
    """Return max severity name"""

    for prioritized_severity in SEVERITIES_PRIORITY:
        # Use Enum name for comparison because it is in DB
        if prioritized_severity.name in input_severities:
            return prioritized_severity.value


def populate_company_alerts_summary_section(company_alerts):
    """Populate alerts summary section with all possible severities and 0 total value if alert severity not
    received from DB"""
    alerts_summary = [alert._asdict() for alert in company_alerts]
    company_alerts_severities = [alert.severity for alert in company_alerts]
    for severity in AlertSeverity:
        if severity not in company_alerts_severities:
            alerts_summary.append(
                {
                    "severity": severity,
                    "total": 0,
                    "unaccomplished_tasks_count": 0,
                }
            )
    # Have summaries ordered by severity: critical, warning, informational.
    alerts_summary = sorted(
        alerts_summary, key=lambda severity_summary: SEVERITIES_PRIORITY.index(severity_summary["severity"])
    )
    return alerts_summary
