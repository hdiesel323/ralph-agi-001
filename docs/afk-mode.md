# AFK Mode: Scheduled Autonomous Operation

AFK (Away From Keyboard) mode allows RALPH-AGI to run autonomously on a schedule, checking in periodically to make progress on tasks even when you're not actively monitoring.

## Quick Start

### 1. Configure the Scheduler

Add a `scheduler` section to your `config.yaml`:

```yaml
scheduler:
  enabled: true
  cron: "0 */4 * * *" # Every 4 hours
  prd_path: "PRD.json"
  wake_hooks:
    - resume_checkpoint
    - check_progress
```

### 2. Start the Daemon

```bash
# Start in background (APScheduler mode)
ralph-agi daemon start

# Or run in foreground for debugging
ralph-agi daemon start --foreground
```

### 3. Check Status

```bash
ralph-agi daemon status
```

### 4. Stop When Done

```bash
ralph-agi daemon stop
```

## Configuration Reference

### Full Configuration Example

```yaml
scheduler:
  # Enable/disable scheduling
  enabled: true

  # Cron expression for wake schedule
  # Format: minute hour day month weekday
  cron: "0 */4 * * *" # Every 4 hours

  # Auto-sleep after N minutes of no progress
  idle_timeout: 30

  # Hooks to run on each scheduled wake
  wake_hooks:
    - resume_checkpoint # Load last checkpoint
    - check_progress # Check task completion
    - run_tests # Run test suite
    - commit_if_ready # Auto-commit if tests pass
    - send_status # Log status notification

  # Daemon configuration
  daemon_mode: apscheduler # apscheduler, launchd, or systemd
  pid_file: ".ralph.pid"
  log_file: ".ralph-daemon.log"

  # Task configuration
  prd_path: "PRD.json"
  config_path: "config.yaml"

  # Failure handling
  max_consecutive_failures: 3
  notify_on_completion: false
  notify_on_failure: true
```

### Cron Expression Examples

| Expression     | Description            |
| -------------- | ---------------------- |
| `* * * * *`    | Every minute           |
| `*/15 * * * *` | Every 15 minutes       |
| `0 * * * *`    | Every hour             |
| `0 */2 * * *`  | Every 2 hours          |
| `0 */4 * * *`  | Every 4 hours          |
| `0 9 * * *`    | Daily at 9:00 AM       |
| `0 9 * * 1-5`  | Weekdays at 9:00 AM    |
| `0 9,18 * * *` | At 9:00 AM and 6:00 PM |
| `0 0 * * 0`    | Weekly on Sunday       |

## Daemon Modes

### APScheduler (Default)

Cross-platform Python-based scheduler. Works on any OS.

```bash
ralph-agi daemon start  # Uses APScheduler by default
```

### launchd (macOS)

Native macOS service for better system integration.

```bash
# Install the service
ralph-agi daemon install --mode launchd

# Enable it
launchctl load ~/Library/LaunchAgents/com.ralph-agi.scheduler.plist

# Disable it
launchctl unload ~/Library/LaunchAgents/com.ralph-agi.scheduler.plist
```

### systemd (Linux)

Native Linux service for server deployments.

```bash
# Install the service
ralph-agi daemon install --mode systemd

# Enable it
systemctl --user daemon-reload
systemctl --user enable --now ralph-agi-scheduler.timer

# Disable it
systemctl --user disable --now ralph-agi-scheduler.timer

# Check status
systemctl --user status ralph-agi-scheduler.timer
journalctl --user -u ralph-agi-scheduler
```

## Wake Hooks

Wake hooks run at each scheduled wake before the main loop executes.

### Built-in Hooks

| Hook                | Description                           |
| ------------------- | ------------------------------------- |
| `resume_checkpoint` | Load last checkpoint for continuation |
| `check_progress`    | Check task completion status in PRD   |
| `run_tests`         | Run pytest suite                      |
| `commit_if_ready`   | Auto-commit if there are changes      |
| `send_status`       | Log a status notification             |

### Hook Execution Order

Hooks execute in the order specified in `wake_hooks`. If a critical hook fails, the main loop may not run.

### Custom Hooks

You can register custom hooks programmatically:

```python
from ralph_agi.scheduler.hooks import WakeHookExecutor, HookExecutionResult, HookResult

executor = WakeHookExecutor(prd_path="PRD.json")

def my_custom_hook():
    # Do something useful
    return HookExecutionResult(
        hook="my_custom_hook",
        result=HookResult.SUCCESS,
        message="Custom hook completed",
        duration_ms=0,
    )

executor.register_hook("my_custom_hook", my_custom_hook)
```

## Monitoring

### Log Files

The daemon logs to the configured `log_file` (default: `.ralph-daemon.log`):

```bash
tail -f .ralph-daemon.log
```

### Status Check

```bash
ralph-agi daemon status
```

Output includes:

- Running/stopped status
- Process ID (if running)
- Next scheduled run time
- Time until next run

## Best Practices

### 1. Start Small

Begin with a longer interval (every 4-6 hours) and decrease as you gain confidence:

```yaml
scheduler:
  cron: "0 */6 * * *" # Every 6 hours initially
```

### 2. Use Checkpoints

Ensure checkpointing is enabled so RALPH can resume from where it left off:

```yaml
checkpoint_path: ".ralph-checkpoint.json"
checkpoint_interval: 1 # Save after every iteration
```

### 3. Enable Test Hooks

Run tests on each wake to catch regressions early:

```yaml
wake_hooks:
  - resume_checkpoint
  - check_progress
  - run_tests # Catch issues early
```

### 4. Monitor Failures

Check logs regularly, especially when starting:

```bash
# Watch for errors
grep -i "error\|fail" .ralph-daemon.log
```

### 5. Set Reasonable Timeouts

Configure idle timeout to avoid wasting resources:

```yaml
scheduler:
  idle_timeout: 30 # Sleep after 30 minutes of no progress
```

## Troubleshooting

### Daemon Won't Start

1. Check if already running:

   ```bash
   ralph-agi daemon status
   ```

2. Check for stale PID file:

   ```bash
   rm .ralph.pid
   ralph-agi daemon start
   ```

3. Check config syntax:
   ```bash
   python -c "import yaml; yaml.safe_load(open('config.yaml'))"
   ```

### Daemon Stops Unexpectedly

1. Check the log file for errors:

   ```bash
   tail -100 .ralph-daemon.log
   ```

2. Verify cron expression is valid:
   ```python
   from ralph_agi.scheduler.cron import validate_cron
   print(validate_cron("0 */4 * * *"))  # Should print True
   ```

### Tasks Not Running

1. Ensure `prd_path` is set in config
2. Check that PRD file exists
3. Verify hooks aren't failing (check logs)

### System Service Not Working

**macOS (launchd):**

```bash
launchctl list | grep ralph
launchctl error com.ralph-agi.scheduler
```

**Linux (systemd):**

```bash
systemctl --user status ralph-agi-scheduler.timer
journalctl --user -u ralph-agi-scheduler -n 50
```

## Security Considerations

1. **PID File Location**: Keep `.ralph.pid` in your project directory
2. **Log Permissions**: Daemon logs may contain sensitive info - restrict access
3. **Git Hooks**: Be cautious with `commit_if_ready` - review changes before pushing
4. **System Services**: User-level services (launchd LaunchAgents, systemd --user) are recommended over system-level
