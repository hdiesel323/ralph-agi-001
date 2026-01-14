"""Cron expression parsing and validation for RALPH-AGI scheduler.

Uses croniter for robust cron expression handling with human-friendly descriptions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from croniter import croniter


class CronValidationError(Exception):
    """Raised when a cron expression is invalid."""

    pass


@dataclass
class CronExpression:
    """Parsed and validated cron expression.

    Attributes:
        expression: The raw cron expression string.
        description: Human-readable description of the schedule.
    """

    expression: str
    description: str

    def __post_init__(self):
        """Validate the expression on creation."""
        if not validate_cron(self.expression):
            raise CronValidationError(f"Invalid cron expression: {self.expression}")

    def next_run(self, base_time: Optional[datetime] = None) -> datetime:
        """Calculate the next scheduled run time.

        Args:
            base_time: Base time to calculate from. Default: now.

        Returns:
            datetime of next scheduled run.
        """
        base = base_time or datetime.now()
        cron = croniter(self.expression, base)
        return cron.get_next(datetime)

    def previous_run(self, base_time: Optional[datetime] = None) -> datetime:
        """Calculate the previous scheduled run time.

        Args:
            base_time: Base time to calculate from. Default: now.

        Returns:
            datetime of previous scheduled run.
        """
        base = base_time or datetime.now()
        cron = croniter(self.expression, base)
        return cron.get_prev(datetime)

    def next_n_runs(self, n: int, base_time: Optional[datetime] = None) -> list[datetime]:
        """Calculate the next N scheduled run times.

        Args:
            n: Number of upcoming runs to calculate.
            base_time: Base time to calculate from. Default: now.

        Returns:
            List of datetime objects for next N runs.
        """
        base = base_time or datetime.now()
        cron = croniter(self.expression, base)
        return [cron.get_next(datetime) for _ in range(n)]

    def time_until_next(self, base_time: Optional[datetime] = None) -> timedelta:
        """Calculate time until next scheduled run.

        Args:
            base_time: Base time to calculate from. Default: now.

        Returns:
            timedelta until next run.
        """
        base = base_time or datetime.now()
        next_time = self.next_run(base)
        return next_time - base


def validate_cron(expression: str) -> bool:
    """Validate a cron expression.

    Args:
        expression: Cron expression string (5 or 6 fields).

    Returns:
        True if valid, False otherwise.
    """
    try:
        croniter(expression)
        return True
    except (ValueError, KeyError):
        return False


def describe_cron(expression: str) -> str:
    """Generate a human-readable description of a cron expression.

    Args:
        expression: Valid cron expression.

    Returns:
        Human-readable description.
    """
    if not validate_cron(expression):
        return "Invalid cron expression"

    parts = expression.split()

    # Common patterns
    common_patterns = {
        "* * * * *": "Every minute",
        "*/5 * * * *": "Every 5 minutes",
        "*/15 * * * *": "Every 15 minutes",
        "*/30 * * * *": "Every 30 minutes",
        "0 * * * *": "Every hour",
        "0 */2 * * *": "Every 2 hours",
        "0 */4 * * *": "Every 4 hours",
        "0 */6 * * *": "Every 6 hours",
        "0 */12 * * *": "Every 12 hours",
        "0 0 * * *": "Daily at midnight",
        "0 9 * * *": "Daily at 9:00 AM",
        "0 9 * * 1-5": "Weekdays at 9:00 AM",
        "0 0 * * 0": "Weekly on Sunday at midnight",
        "0 0 1 * *": "Monthly on the 1st at midnight",
    }

    if expression in common_patterns:
        return common_patterns[expression]

    # Build description from parts
    minute, hour, day, month, weekday = parts[:5]

    desc_parts = []

    # Minute
    if minute == "*":
        desc_parts.append("every minute")
    elif minute.startswith("*/"):
        desc_parts.append(f"every {minute[2:]} minutes")
    elif minute == "0":
        pass  # Will be handled with hour
    else:
        desc_parts.append(f"at minute {minute}")

    # Hour
    if hour == "*":
        if minute != "*":
            desc_parts.append("every hour")
    elif hour.startswith("*/"):
        desc_parts.append(f"every {hour[2:]} hours")
    else:
        desc_parts.append(f"at {hour}:{minute.zfill(2) if minute != '*' else '00'}")

    # Day of month
    if day != "*":
        if day.startswith("*/"):
            desc_parts.append(f"every {day[2:]} days")
        else:
            desc_parts.append(f"on day {day}")

    # Weekday
    weekday_names = {
        "0": "Sunday",
        "1": "Monday",
        "2": "Tuesday",
        "3": "Wednesday",
        "4": "Thursday",
        "5": "Friday",
        "6": "Saturday",
        "7": "Sunday",
        "1-5": "weekdays",
        "0,6": "weekends",
    }
    if weekday != "*":
        if weekday in weekday_names:
            desc_parts.append(f"on {weekday_names[weekday]}")
        else:
            desc_parts.append(f"on weekday {weekday}")

    return " ".join(desc_parts) if desc_parts else "Custom schedule"


# Preset schedules for common AFK patterns
PRESET_SCHEDULES = {
    "hourly": CronExpression("0 * * * *", "Every hour"),
    "every_2_hours": CronExpression("0 */2 * * *", "Every 2 hours"),
    "every_4_hours": CronExpression("0 */4 * * *", "Every 4 hours"),
    "every_6_hours": CronExpression("0 */6 * * *", "Every 6 hours"),
    "twice_daily": CronExpression("0 9,21 * * *", "At 9:00 AM and 9:00 PM"),
    "daily": CronExpression("0 9 * * *", "Daily at 9:00 AM"),
    "weekdays": CronExpression("0 9 * * 1-5", "Weekdays at 9:00 AM"),
    "weekly": CronExpression("0 9 * * 1", "Weekly on Monday at 9:00 AM"),
}
