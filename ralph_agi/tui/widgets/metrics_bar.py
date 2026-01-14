"""Metrics bar widget for displaying cost, time, and iteration stats."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import ClassVar

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static


@dataclass
class Metrics:
    """Current execution metrics."""

    iteration: int = 0
    max_iterations: int = 100
    cost: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    errors: int = 0
    velocity: float = 0.0  # points per sprint

    @property
    def total_tokens(self) -> int:
        """Get total tokens used."""
        return self.input_tokens + self.output_tokens

    @property
    def elapsed_time(self) -> timedelta:
        """Get elapsed time since start."""
        return datetime.now() - self.start_time

    @property
    def elapsed_str(self) -> str:
        """Get formatted elapsed time string."""
        elapsed = self.elapsed_time
        hours = int(elapsed.total_seconds() // 3600)
        minutes = int((elapsed.total_seconds() % 3600) // 60)
        seconds = int(elapsed.total_seconds() % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @property
    def iteration_str(self) -> str:
        """Get formatted iteration string."""
        return f"{self.iteration}/{self.max_iterations}"


class MetricItem(Static):
    """A single metric display item."""

    DEFAULT_CSS = """
    MetricItem {
        height: 1;
        padding: 0 1;
    }
    MetricItem .label {
        color: $text-muted;
    }
    MetricItem .value {
        color: $text;
        text-style: bold;
    }
    """

    def __init__(self, label: str, value: str, **kwargs) -> None:
        """Initialize a metric item.

        Args:
            label: Metric label.
            value: Metric value.
            **kwargs: Additional arguments for Static.
        """
        self.label = label
        self.value = value
        content = f"[dim]{label}:[/] [bold]{value}[/]"
        super().__init__(content, **kwargs)

    def update_value(self, value: str) -> None:
        """Update the metric value.

        Args:
            value: New value.
        """
        self.value = value
        self.update(f"[dim]{self.label}:[/] [bold]{value}[/]")


class MetricsBar(Vertical):
    """Panel displaying execution metrics."""

    DEFAULT_CSS = """
    MetricsBar {
        border: solid $primary;
        height: auto;
        min-height: 7;
        padding: 0;
    }
    MetricsBar > .metrics-title {
        dock: top;
        background: $primary;
        color: $text;
        padding: 0 1;
        text-style: bold;
    }
    MetricsBar > .metrics-content {
        padding: 0;
    }
    """

    TITLE: ClassVar[str] = "Metrics"

    def __init__(self, title: str = "Metrics", **kwargs) -> None:
        """Initialize the metrics bar.

        Args:
            title: Panel title.
            **kwargs: Additional arguments for Vertical.
        """
        super().__init__(**kwargs)
        self._title = title
        self._metrics = Metrics()

        # Metric items
        self._iteration_item: MetricItem | None = None
        self._cost_item: MetricItem | None = None
        self._time_item: MetricItem | None = None
        self._tokens_item: MetricItem | None = None
        self._velocity_item: MetricItem | None = None

    def compose(self) -> ComposeResult:
        """Compose the metrics layout."""
        yield Static(f" {self._title} ", classes="metrics-title")

        with Vertical(classes="metrics-content"):
            self._iteration_item = MetricItem("Iterations", self._metrics.iteration_str)
            yield self._iteration_item

            self._cost_item = MetricItem("Cost", f"${self._metrics.cost:.2f}")
            yield self._cost_item

            self._time_item = MetricItem("Time", self._metrics.elapsed_str)
            yield self._time_item

            self._tokens_item = MetricItem("Tokens", f"{self._metrics.total_tokens:,}")
            yield self._tokens_item

            self._velocity_item = MetricItem("Velocity", f"{self._metrics.velocity:.1f} pts/sprint")
            yield self._velocity_item

    def update_metrics(self, metrics: Metrics) -> None:
        """Update all metrics.

        Args:
            metrics: New metrics data.
        """
        self._metrics = metrics
        self._refresh_display()

    def update_iteration(self, iteration: int, max_iterations: int | None = None) -> None:
        """Update iteration count.

        Args:
            iteration: Current iteration.
            max_iterations: Optional new max iterations.
        """
        self._metrics.iteration = iteration
        if max_iterations is not None:
            self._metrics.max_iterations = max_iterations
        if self._iteration_item:
            self._iteration_item.update_value(self._metrics.iteration_str)

    def update_cost(self, cost: float) -> None:
        """Update cost.

        Args:
            cost: New cost value.
        """
        self._metrics.cost = cost
        if self._cost_item:
            self._cost_item.update_value(f"${cost:.2f}")

    def update_tokens(self, input_tokens: int, output_tokens: int) -> None:
        """Update token counts.

        Args:
            input_tokens: Input token count.
            output_tokens: Output token count.
        """
        self._metrics.input_tokens = input_tokens
        self._metrics.output_tokens = output_tokens
        if self._tokens_item:
            self._tokens_item.update_value(f"{self._metrics.total_tokens:,}")

    def add_cost(self, amount: float) -> None:
        """Add to the current cost.

        Args:
            amount: Amount to add.
        """
        self._metrics.cost += amount
        self.update_cost(self._metrics.cost)

    def add_tokens(self, input_tokens: int, output_tokens: int) -> None:
        """Add to token counts.

        Args:
            input_tokens: Input tokens to add.
            output_tokens: Output tokens to add.
        """
        self._metrics.input_tokens += input_tokens
        self._metrics.output_tokens += output_tokens
        if self._tokens_item:
            self._tokens_item.update_value(f"{self._metrics.total_tokens:,}")

    def _refresh_display(self) -> None:
        """Refresh all metric displays."""
        if self._iteration_item:
            self._iteration_item.update_value(self._metrics.iteration_str)
        if self._cost_item:
            self._cost_item.update_value(f"${self._metrics.cost:.2f}")
        if self._time_item:
            self._time_item.update_value(self._metrics.elapsed_str)
        if self._tokens_item:
            self._tokens_item.update_value(f"{self._metrics.total_tokens:,}")
        if self._velocity_item:
            self._velocity_item.update_value(f"{self._metrics.velocity:.1f} pts/sprint")

    def refresh_time(self) -> None:
        """Refresh the elapsed time display."""
        if self._time_item:
            self._time_item.update_value(self._metrics.elapsed_str)

    @property
    def metrics(self) -> Metrics:
        """Get current metrics."""
        return self._metrics
