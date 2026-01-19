---
id: ralph-agi-001-002
title: Implement Cron/Scheduled Triggers for AFK Mode
type: feature
status: open
priority: 1
labels: [afk-mode, scheduler, autonomy, clawdbot-inspired]
created: 2026-01-10
epic: epic-01-core-loop
source: rnd/research/2026-01-10_clawdbot-patterns-analysis.md
---

# Implement Cron/Scheduled Triggers for AFK Mode

## Problem Statement

RALPH-AGI currently supports SIGINT handling for graceful pauses but has no mechanism to automatically resume or wake up. True AFK (Away From Keyboard) autonomy requires scheduled check-ins and external triggers.

## Proposed Solution

Implement a scheduler system inspired by Clawdbot's cron/webhook approach:

1. **Cron Support in config.yaml**

   ```yaml
   scheduler:
     enabled: true
     cron: "0 */4 * * *" # Every 4 hours
     wake_hooks:
       - check_progress
       - run_tests
       - commit_if_ready
   ```

2. **System Daemon Integration**
   - macOS: launchd plist
   - Linux: systemd service unit
   - Fallback: Python APScheduler

3. **Wake Hooks**
   - `on_scheduled_wake`: Resume from checkpoint
   - `on_external_trigger`: Webhook/API trigger
   - `on_idle_timeout`: Auto-sleep after N minutes of no progress

## Acceptance Criteria

- [ ] Cron expression parsing and validation
- [ ] Config.yaml scheduler section
- [ ] launchd/systemd service templates
- [ ] Wake hook execution framework
- [ ] Checkpoint resume on scheduled wake
- [ ] External webhook trigger endpoint (optional)
- [ ] Unit tests for scheduler logic
- [ ] Documentation for AFK setup

## Technical Notes

- Use `croniter` for cron parsing
- Consider `APScheduler` for cross-platform fallback
- Wake should load last checkpoint from progress.txt + Memvid
- Log wake/sleep events for debugging

## Dependencies

- Epic 01: Core Execution Loop (COMPLETE)
- Story 1.4: Checkpoint System

## Effort Estimate

Points: 5

## References

- [Clawdbot Patterns Analysis](../../rnd/research/2026-01-10_clawdbot-patterns-analysis.md)
- [Clawdbot GitHub](https://github.com/clawdbot/clawdbot)
