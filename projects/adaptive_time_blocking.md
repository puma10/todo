# Adaptive Time Blocking System - PRD

## Overview
An intelligent time blocking system that integrates Google Calendar with priority [1] tasks, learns from completion patterns, and adapts scheduling based on task types, time-of-day preferences, and historical data.

## Goals
1. Automatically schedule priority [1] tasks into calendar
2. Learn optimal task durations over time
3. Adapt to personal productivity patterns (time-of-day preferences)
4. Differentiate between task types (dev learning vs architecting vs implementation)
5. Manage workout scheduling alongside tasks

## Core Features

### 1. Task Duration Estimation (Hybrid AI Approach)

**Priority Order:**
1. **Explicit duration** - Parse from task text ("1 hour", "30 min", "2h")
2. **Duration tags** - Extract from `[1h]` or `[30m]` tags
3. **AI estimation** - Use Google Gemini API with task context
4. **Section-based defaults** - Fallback to section defaults

**Task Type Classification:**
- **Dev Learning** (Reddit Bot, exploratory): High variance, unpredictable
- **Architecting** (Artsmart, complex design): Very high variance, requires deep focus
- **Dev Implementation** (Dev workflow, coding): Medium variance, more predictable
- **Quick Tasks** (Admin): Low variance, fast completion
- **Learning** (Learn section): Medium variance, focused time needed

### 2. Historical Learning Database

**Storage:** `task_history.json`

**Tracks:**
- Estimated vs actual completion times
- Task completion by time-of-day
- Average durations per task type
- Optimal scheduling times
- Completion rates

**Updates:**
- After each calendar event completion
- Compares scheduled vs actual duration
- Calculates weighted averages (70% historical, 30% new estimate)
- Identifies best time slots for each task type

### 3. Time-of-Day Pattern Learning

**Analyzes:**
- When tasks are completed most efficiently
- Energy patterns throughout the day
- Task type preferences (architecting → morning, etc.)
- Completion rate by hour

**Applies:**
- Schedules architecting tasks in morning (deep focus time)
- Schedules dev learning tasks when energy is high
- Adapts to personal patterns over time

### 4. Google Calendar Integration

**Features:**
- Fetch today's existing calendar events
- Find available time slots
- Create calendar events for [1] priority tasks
- Tag events with `[1]` prefix for tracking
- Respect existing meetings and commitments

**Scheduling Algorithm:**
- Prioritize optimal time slots based on task type
- Consider buffer time between meetings
- Respect work hours (configurable, default 9am-5pm)
- Handle overflow (if tasks don't fit, suggest tomorrow)

### 5. Workout Management

**Requirements:**
- Schedule workouts alongside tasks
- Learn optimal workout times
- Track workout completion
- Integrate with task scheduling (don't double-book)
- Support different workout types:
  - Strength training
  - Cardio
  - Recovery/stretching
  - Active rest

**Workout Scheduling:**
- Default workout duration: 60 minutes
- Preferred times: Configurable (e.g., morning 7-9am, evening 5-7pm)
- Frequency: Configurable (e.g., 3-4x per week)
- Auto-schedule: Option to automatically block workout time
- Manual override: Can manually schedule specific workouts

**Workout Tracking:**
- Mark workouts as completed
- Track actual duration vs scheduled
- Learn optimal workout times
- Adjust scheduling based on completion patterns

## Technical Implementation

### File Structure
```
time_block.py              # Main time blocking script
duration_estimator.py      # Hybrid duration estimation
calendar_integration.py     # Google Calendar API wrapper
task_history.json          # Learning database
workout_config.json        # Workout preferences
```

### Dependencies
- `google-generativeai` - AI estimation
- `google-api-python-client` - Calendar API
- `google-auth-httplib2` - Authentication
- `google-auth-oauthlib` - OAuth flow

### Configuration Files

**workout_config.json:**
```json
{
  "enabled": true,
  "default_duration": 60,
  "frequency_per_week": 4,
  "preferred_times": {
    "morning": {"start": "07:00", "end": "09:00"},
    "evening": {"start": "17:00", "end": "19:00"}
  },
  "workout_types": ["strength", "cardio", "recovery"],
  "auto_schedule": true
}
```

**task_type_config.json:**
```json
{
  "Reddit Bot": {
    "type": "dev_learning",
    "base_duration": 90,
    "variance": "high",
    "time_preference": "flexible"
  },
  "Artsmart": {
    "type": "architecting",
    "base_duration": 120,
    "variance": "very_high",
    "time_preference": "deep_focus"
  },
  "Dev workflow": {
    "type": "dev_implementation",
    "base_duration": 60,
    "variance": "medium",
    "time_preference": "flexible"
  }
}
```

## User Flow

### Initial Setup
1. Authenticate with Google Calendar (OAuth)
2. Configure workout preferences
3. Run initial AI estimation for all [1] tasks
4. Review and adjust estimates if needed

### Daily Workflow
1. Run `make focus` to see [1] priority tasks
2. Run `make block` to schedule tasks + workouts
3. System:
   - Fetches [1] tasks
   - Estimates durations (hybrid AI)
   - Checks calendar for available slots
   - Schedules tasks in optimal time slots
   - Schedules workouts based on preferences
   - Shows preview before creating events
4. User confirms → Events created in calendar
5. Throughout day: Complete tasks, mark workouts done
6. End of day: System learns from actual completion times

### Learning Loop
1. **Track**: Monitor calendar events marked complete
2. **Compare**: Scheduled duration vs actual duration
3. **Update**: Historical database with new data
4. **Improve**: Next day's estimates become more accurate

## Make Commands

```makefile
block:
    python3 time_block.py

block-auto:
    python3 time_block.py --auto

block-workouts:
    python3 time_block.py --include-workouts

learn:
    python3 update_learning_db.py  # Run at end of day
```

## Success Metrics

- **Estimation Accuracy**: % of tasks completed within ±20% of estimate
- **Scheduling Efficiency**: % of tasks scheduled in optimal time slots
- **Workout Consistency**: % of scheduled workouts actually completed
- **Time Utilization**: % of workday effectively blocked
- **Learning Rate**: Improvement in estimation accuracy over time

## Future Enhancements

- Integration with task completion tracking (sync_completed.py)
- Multi-day planning (schedule tasks across week)
- Energy level prediction based on sleep/activity data
- Conflict resolution (reschedule if conflicts arise)
- Mobile notifications for upcoming time blocks
- Weekly review reports (productivity insights)

## Open Questions

- Should workouts be mandatory blocks or flexible?
- How to handle tasks that span multiple days?
- Should system reschedule if tasks run over?
- Integration with other productivity tools?


