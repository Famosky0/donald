# Taskflow MVP Scope (v0.1)

## MVP Statement

Ship a working Taskflow app where a user can plan today using tasks + habits, and generate a simple AI day plan.

## In Scope (MUST ship)

### Auth

- [ ] Sign up (email + password) creates a user account
- [ ] Log in authenticates and creates a session
- [ ] Log out ends the session
- [ ] Protected routes: user cannot access /app without being logged in
- [ ] Basic validation + error messages (invalid email, weak password, wrong credentials)

### Tasks

- [ ] Create a task (title required)
- [ ] View task list (shows incomplete first; completed separated or toggle)
- [ ] Edit a task
- [ ] Complete/uncomplete a task
- [ ] Delete a task
- [ ] Optional (if simple): due date and priority

### Habits

- [ ] Create a habit (name required)
- [ ] Mark habit done for today
- [ ] Habit history stores completion by date
- [ ] Streak/progress is visible (even if simple: “3-day streak”)

### Habits (Data rule)

- Habit completion must be stored per-day (e.g., `habit_completions` table with `habit_id` + `date` + timestamps).
- Do NOT store habit completion as a single boolean on the habit, or streaks/history will break.

### Today Page (Core UX)

- [ ] Today page displays:
  - [ ] Today’s tasks
  - [ ] Today’s habits
  - [ ] Clear primary action (“Generate Plan” or “Start Now”)
- [ ] Empty states:
  - [ ] If no tasks: prompt to add tasks
  - [ ] If no habits: prompt to add habits

### AI Feature (LOCKED)

- [ ] Button: “Plan my day”
- [ ] Inputs used:
  - [ ] tasks + basic metadata
  - [ ] habits
  - [ ] available time (simple picker/slider)
- [ ] Output:
  - [ ] Top 3 priorities
  - [ ] 3–5 time blocks (morning/midday/evening is fine)
  - [ ] Habit slots included
  - [ ] A fallback plan (“If you’re behind…”)
- [ ] User can:
  - [ ] Accept plan (saves it for the day)
  - [ ] Regenerate plan

### AI Plan (Data rule)

- AI day plans must be saveable and retrievable (e.g., `day_plans` table keyed by `user_id` + `date`).
- If it can’t be saved and re-opened, it does not count as an MVP feature.

## Out of Scope (NOT in MVP)

- Teams/collaboration
- Calendar integrations
- Social/community
- Advanced analytics dashboards
- Multiple AI tools/features
- Notifications/reminders (unless super basic and fast)
- Payments/subscriptions
- Mobile app (native)

## Definition of Done (MVP is complete only when)

- [ ] New user can sign up and reach Today page in under 60 seconds
- [ ] User can create + complete at least 1 task and 1 habit
- [ ] AI “Plan my day” generates a plan and it can be saved + viewed later that same day
- [ ] No critical crashes in the core flow (auth → today → plan)
- [ ] App is deployed and usable by someone who is not you

## Nice-to-have (ONLY if MVP is already complete)

- [ ] Tags or lists
- [ ] Task priority + due dates (if not already included)
- [ ] Simple weekly review screen
