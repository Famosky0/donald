# Taskflow DB Schema (MVP) v0.1

Database: MySQL 8+ (InnoDB, utf8mb4)

## Design rules

- All user-owned records include `user_id`.
- Store habit completion **by date** (do NOT store a single boolean on habits).
- AI plans must be **saveable + retrievable** (keyed by user + date).
- Use UTC timestamps.

---

## Table: users

Purpose: auth + identity

Columns:

- id (BIGINT PK, auto increment)
- email (VARCHAR(255), unique, not null)
- password_hash (VARCHAR(255), not null)
- display_name (VARCHAR(80), null)
- created_at (DATETIME, not null)
- updated_at (DATETIME, not null)

Indexes:

- UNIQUE(email)

---

## Table: user_settings

Purpose: onboarding survey defaults + preferences

Columns:

- id (BIGINT PK, auto increment)
- user_id (BIGINT FK -> users.id, unique, not null)
- available_minutes_default (INT, not null) # e.g. 120
- focus_area (VARCHAR(50), null) # "School", "Coding", etc
- best_work_time (VARCHAR(20), null) # "Morning"/"Afternoon"/"Evening"
- timezone (VARCHAR(64), null)
- created_at (DATETIME, not null)
- updated_at (DATETIME, not null)

Indexes:

- UNIQUE(user_id)

---

## Table: tasks

Purpose: task CRUD + “today view”

Columns:

- id (BIGINT PK, auto increment)
- user_id (BIGINT FK -> users.id, not null)
- title (VARCHAR(200), not null)
- notes (TEXT, null)
- status (ENUM('todo','done'), not null) # keep simple for MVP
- priority (TINYINT, null) # optional: 1-3
- due_date (DATE, null) # optional
- scheduled_for (DATE, null) # helps "Today" list
- estimated_minutes (INT, null) # optional
- completed_at (DATETIME, null)
- created_at (DATETIME, not null)
- updated_at (DATETIME, not null)

Indexes:

- INDEX(user_id, status)
- INDEX(user_id, scheduled_for)
- INDEX(user_id, due_date)

---

## Table: habits

Purpose: habit definitions

Columns:

- id (BIGINT PK, auto increment)
- user_id (BIGINT FK -> users.id, not null)
- name (VARCHAR(120), not null)
- frequency (ENUM('daily','weekly'), not null) # MVP: default 'daily'
- is_active (BOOLEAN, not null)
- created_at (DATETIME, not null)
- updated_at (DATETIME, not null)

Indexes:

- INDEX(user_id, is_active)

---

## Table: habit_completions

Purpose: habit tracking by date (streaks)

Columns:

- id (BIGINT PK, auto increment)
- habit_id (BIGINT FK -> habits.id, not null)
- user_id (BIGINT FK -> users.id, not null) # redundant but useful for queries
- completed_on (DATE, not null) # the day it was completed
- completed_at (DATETIME, not null)

Constraints:

- UNIQUE(habit_id, completed_on) # prevents double-tap duplicates

Indexes:

- INDEX(user_id, completed_on)
- INDEX(habit_id, completed_on)

---

## Table: day_plans

Purpose: saveable AI plan for a given date

Columns:

- id (BIGINT PK, auto increment)
- user_id (BIGINT FK -> users.id, not null)
- plan_date (DATE, not null)
- available_minutes (INT, not null)
- plan_json (JSON, not null) # blocks + priorities + fallback
- generated_at (DATETIME, not null)
- accepted_at (DATETIME, null) # set when user clicks "Save today's plan"

Constraints:

- UNIQUE(user_id, plan_date)

Indexes:

- INDEX(user_id, plan_date)

Plan JSON shape (example):
{
"top_priorities": ["Task A", "Task B", "Task C"],
"blocks": [
{"label":"Morning","minutes":90,"items":[{"type":"task","id":12},{"type":"habit","id":3}]},
{"label":"Midday","minutes":60,"items":[...]},
{"label":"Evening","minutes":30,"items":[...]}
],
"fallback": "If you're behind, do Task A + 1 habit."
}

---

## Later tables (NOT MVP)

- goals
- reminders
- journal_entries
- ai_memory
- notes
- integrations
