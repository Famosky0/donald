# Taskflow Backlog (v0.1)

## MVP Backlog (MUST ship — no exceptions)

### 0) Foundations

- [ ] Repo structure (/apps, /docs, /db) + environment setup
- [ ] Database connected (MySQL) + migrations
- [ ] Basic UI layout:
  - Landing page (top navbar)
  - App shell (sidebar) + protected routes

### 1) Authentication

- [ ] Signup (email + password)
- [ ] Login
- [ ] Logout
- [ ] Password hashing (bcrypt/argon2)
- [ ] Session/JWT handling
- [ ] Basic validation + error messages

### 2) Onboarding Survey (Surgical)

- [ ] Collect available time (1–6h) (required)
- [ ] Optional focus area + best work time
- [ ] Skippable with defaults saved

### 3) Tasks (CRUD)

- [ ] Create task (title required)
- [ ] List tasks (Today + Tasks page)
- [ ] Edit task
- [ ] Complete/uncomplete task
- [ ] Delete task
- [ ] (Optional if simple) Priority and due date

### 4) Habits (Core loop)

- [ ] Create habit (name required)
- [ ] Mark habit done for today
- [ ] Store completion by date (habit_completions)
- [ ] Show streak/progress (simple streak count is enough)

### 5) Today Page (Core UX)

- [ ] Today shows:
  - Tasks for today
  - Habits for today
  - Primary CTA: "Plan my day"
- [ ] Empty states:
  - No tasks → prompt add tasks
  - No habits → prompt add habit
- [ ] Mobile-friendly responsiveness (basic)

### 6) AI Feature (LOCKED): Plan my day

- [ ] Generate plan using tasks + habits + available time
- [ ] Output includes:
  - Top 3 priorities
  - 3–5 time blocks (Morning/Midday/Evening acceptable)
  - Habit slots included
  - “If you’re behind…” fallback plan
- [ ] Save plan (day_plans table keyed by user + date)
- [ ] View saved plan later the same day
- [ ] Regenerate plan

### 7) Quality + Security (MVP level)

- [ ] Input validation (server-side)
- [ ] Error handling + loading states + empty states
- [ ] SQL injection protection (parameterized queries/ORM)
- [ ] Rate limiting on auth endpoints (basic)
- [ ] Basic test coverage: auth + tasks + habits + plan save/load
- [ ] Deploy MVP (so a real user can use it)

---

## Later (DO NOT TOUCH until MVP ships)

### UI/UX upgrades

- Dark/Light mode
- Global search bar
- Advanced UI polish + animations
- Notifications/reminders (push/email/SMS)

### Productivity expansion

- Goals page (short/long term)
- Calendar view (weekly/monthly)
- Notes / journaling section
- Focus mode / Pomodoro timer
- Progress dashboard (charts, achievements)

### AI expansion

- AI assistant chat page
- Habit recommendations
- Weekly summaries + improvements
- Journal analysis
- Routine generator

### Account features

- Email verification
- Password reset / account recovery

### Advanced productivity logic

- Task categories/tags/lists
- Daily resets + recurring tasks
- Calendar syncing

### Social / Gamification / Integrations

- Friends / sharing / leaderboards
- XP, levels, badges, rewards
- Google Calendar sync
- Mobile app notifications
- Apple Health / Google Fit integrations
