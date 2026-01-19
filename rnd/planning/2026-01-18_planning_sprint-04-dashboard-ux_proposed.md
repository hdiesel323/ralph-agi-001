# Sprint 04: Dashboard UX Improvements

**Duration:** 2026-01-18 to 2026-01-25
**Lead:** RALPH-AGI Team

---

## Goals

- Improve Dashboard usability with drag-and-drop, keyboard shortcuts, and better visual feedback
- Enhance mobile experience with swipe gestures and responsive improvements
- Add quality-of-life features like filter persistence, bulk actions, and empty states

## Tasks

### Phase 1: Core Interactions (P0 - High Impact)

| Task ID | Description | Estimated Effort | Status | Priority |
|:--------|:------------|:-----------------|:-------|:---------|
| T-01 | Implement drag-and-drop for Kanban board (react-dnd or dnd-kit) | 4 hours | Done | P0 |
| T-02 | Add filter state persistence (URL params + localStorage) | 2 hours | Done | P0 |
| T-03 | Add keyboard shortcuts help modal (? key trigger) | 2 hours | Done | P0 |

### Phase 2: Visual Feedback (P1 - Medium Impact)

| Task ID | Description | Estimated Effort | Status | Priority |
|:--------|:------------|:-----------------|:-------|:---------|
| T-04 | Add empty states for Kanban columns with helpful messages | 1 hour | Done | P1 |
| T-05 | Add overall progress bar in header | 1.5 hours | Done | P1 |
| T-06 | Improve dependency visualization (blocked badge, link indicators) | 2 hours | Done | P1 |

### Phase 3: Power User Features (P2)

| Task ID | Description | Estimated Effort | Status | Priority |
|:--------|:------------|:-----------------|:-------|:---------|
| T-07 | Add bulk actions (multi-select with checkboxes, batch operations) | 3 hours | Done | P2 |
| T-08 | Add sort options within columns (priority, date, duration) | 2 hours | Done | P2 |

### Phase 4: Mobile Enhancements (P2)

| Task ID | Description | Estimated Effort | Status | Priority |
|:--------|:------------|:-----------------|:-------|:---------|
| T-09 | Add mobile swipe gestures for status changes | 3 hours | Done | P2 |
| T-10 | Column tabs view for mobile (instead of horizontal scroll) | 2 hours | Done | P2 |

---

## Technical Approach

### T-01: Drag-and-Drop
- Use `@dnd-kit/core` and `@dnd-kit/sortable` (already have similar patterns in codebase)
- Update `KanbanColumn` to be droppable, `TaskCard` to be draggable
- Call `onStatusChange` when card dropped in different column

### T-02: Filter Persistence
- Use URL search params for shareable links: `?search=foo&priority=P1&showCompleted=false`
- Sync with `useSearchParams` or custom hook
- Fallback to localStorage for cross-session persistence

### T-03: Keyboard Shortcuts Help
- Create `KeyboardShortcutsDialog` component
- Register `?` in `useKeyboardShortcuts`
- Show all available shortcuts in a modal

### T-04: Empty States
- Add `EmptyColumnState` component with contextual messages
- "No tasks in backlog - create one with + Add Task"
- "All caught up!" for empty Done column

### T-05: Progress Bar
- Calculate from `queueStats`: `complete / total * 100`
- Add thin progress bar below header or in QuickActionsBar
- Color gradient based on completion %

### T-06: Dependency Visualization
- Add "Blocked" badge for tasks with unmet dependencies
- Tooltip showing which tasks are blocking
- Optional: dotted connector lines between dependent cards

---

## Acceptance Criteria

- [ ] Tasks can be dragged between Kanban columns to change status
- [ ] Filter state persists across page refreshes and is shareable via URL
- [ ] Pressing `?` opens keyboard shortcuts help modal
- [ ] Empty columns show helpful guidance messages
- [ ] Overall progress is visible at a glance
- [ ] Blocked tasks are visually distinct from ready tasks
- [ ] Multiple tasks can be selected and batch-operated
- [ ] Tasks within columns can be sorted by different criteria
- [ ] Mobile users can swipe cards to change status
- [ ] Mobile view has tab-based column navigation

## Dependencies

- May need to install `@dnd-kit/core` and `@dnd-kit/sortable` packages
- No backend changes required - all frontend improvements

## Risks

- Drag-and-drop may conflict with existing click handlers on TaskCard
- Mobile swipe gestures need careful touch event handling to avoid scroll conflicts

## Notes

- Consider adding undo/redo support in a future sprint
- Sound/notification features deferred to accessibility review
