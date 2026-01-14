"""Tests for cron expression parsing and validation."""

from datetime import datetime, timedelta

import pytest

from ralph_agi.scheduler.cron import (
    CronExpression,
    CronValidationError,
    PRESET_SCHEDULES,
    describe_cron,
    validate_cron,
)


class TestValidateCron:
    """Tests for cron expression validation."""

    def test_valid_standard_cron(self):
        """Standard 5-field cron expressions should be valid."""
        assert validate_cron("* * * * *")
        assert validate_cron("0 * * * *")
        assert validate_cron("0 0 * * *")
        assert validate_cron("0 0 1 * *")
        assert validate_cron("0 0 1 1 *")

    def test_valid_interval_expressions(self):
        """Interval expressions (*/n) should be valid."""
        assert validate_cron("*/5 * * * *")
        assert validate_cron("0 */2 * * *")
        assert validate_cron("0 */4 * * *")
        assert validate_cron("*/15 */6 * * *")

    def test_valid_range_expressions(self):
        """Range expressions (n-m) should be valid."""
        assert validate_cron("0 9 * * 1-5")  # Weekdays
        assert validate_cron("0 0 1-15 * *")  # First half of month
        assert validate_cron("0 8-17 * * *")  # Working hours

    def test_valid_list_expressions(self):
        """List expressions (n,m,o) should be valid."""
        assert validate_cron("0 9,12,18 * * *")  # 9am, noon, 6pm
        assert validate_cron("0 0 1,15 * *")  # 1st and 15th

    def test_invalid_expressions(self):
        """Invalid expressions should return False."""
        assert not validate_cron("")
        assert not validate_cron("invalid")
        assert not validate_cron("* * *")  # Too few fields
        assert not validate_cron("60 * * * *")  # Invalid minute
        assert not validate_cron("* 24 * * *")  # Invalid hour
        assert not validate_cron("* * 32 * *")  # Invalid day


class TestCronExpression:
    """Tests for CronExpression class."""

    def test_create_valid_expression(self):
        """Should create CronExpression for valid cron strings."""
        cron = CronExpression("0 */4 * * *", "Every 4 hours")
        assert cron.expression == "0 */4 * * *"
        assert cron.description == "Every 4 hours"

    def test_create_invalid_expression_raises(self):
        """Should raise CronValidationError for invalid expressions."""
        with pytest.raises(CronValidationError):
            CronExpression("invalid", "test")

    def test_next_run_returns_future_datetime(self):
        """next_run should return a datetime in the future."""
        cron = CronExpression("* * * * *", "Every minute")
        now = datetime.now()
        next_time = cron.next_run(now)
        assert next_time > now

    def test_previous_run_returns_past_datetime(self):
        """previous_run should return a datetime in the past."""
        cron = CronExpression("* * * * *", "Every minute")
        now = datetime.now()
        prev_time = cron.previous_run(now)
        assert prev_time < now

    def test_next_n_runs_returns_correct_count(self):
        """next_n_runs should return the requested number of datetimes."""
        cron = CronExpression("0 * * * *", "Every hour")
        runs = cron.next_n_runs(5)
        assert len(runs) == 5
        # Should be in ascending order
        for i in range(1, len(runs)):
            assert runs[i] > runs[i - 1]

    def test_time_until_next_returns_timedelta(self):
        """time_until_next should return a positive timedelta."""
        cron = CronExpression("* * * * *", "Every minute")
        delta = cron.time_until_next()
        assert isinstance(delta, timedelta)
        assert delta.total_seconds() >= 0

    def test_hourly_schedule(self):
        """Hourly schedule should fire at minute 0."""
        cron = CronExpression("0 * * * *", "Hourly")
        base = datetime(2026, 1, 1, 12, 30, 0)
        next_time = cron.next_run(base)
        assert next_time.minute == 0
        assert next_time.hour == 13  # Next hour

    def test_daily_schedule(self):
        """Daily schedule should fire at specified time."""
        cron = CronExpression("0 9 * * *", "Daily at 9am")
        base = datetime(2026, 1, 1, 10, 0, 0)  # After 9am
        next_time = cron.next_run(base)
        assert next_time.hour == 9
        assert next_time.day == 2  # Next day


class TestDescribeCron:
    """Tests for cron description generation."""

    def test_common_patterns(self):
        """Common patterns should have human-readable descriptions."""
        assert "minute" in describe_cron("* * * * *").lower()
        assert "hour" in describe_cron("0 * * * *").lower()
        assert "daily" in describe_cron("0 0 * * *").lower() or "midnight" in describe_cron("0 0 * * *").lower()

    def test_interval_descriptions(self):
        """Interval patterns should describe the interval."""
        desc = describe_cron("*/5 * * * *")
        assert "5" in desc

        desc = describe_cron("0 */4 * * *")
        assert "4" in desc

    def test_invalid_expression_returns_error_message(self):
        """Invalid expressions should return an error message."""
        desc = describe_cron("invalid")
        assert "invalid" in desc.lower()


class TestPresetSchedules:
    """Tests for preset schedule definitions."""

    def test_presets_are_valid(self):
        """All preset schedules should be valid CronExpressions."""
        for name, cron in PRESET_SCHEDULES.items():
            assert isinstance(cron, CronExpression)
            assert validate_cron(cron.expression)

    def test_expected_presets_exist(self):
        """Expected preset names should exist."""
        expected = ["hourly", "daily", "weekly", "every_4_hours"]
        for name in expected:
            assert name in PRESET_SCHEDULES

    def test_hourly_preset(self):
        """Hourly preset should fire every hour."""
        cron = PRESET_SCHEDULES["hourly"]
        base = datetime(2026, 1, 1, 12, 0, 0)
        runs = cron.next_n_runs(3, base)
        # Should be 1 hour apart
        for i in range(1, len(runs)):
            delta = runs[i] - runs[i - 1]
            assert delta == timedelta(hours=1)
