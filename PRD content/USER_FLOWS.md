# Taskflow User Flows (MVP) v0.1

## Navigation Assumption (for MVP)

- Landing page uses a **top navbar** (Sign up / Log in primary).
- App uses a **left sidebar**, defaulting to **Today** after login.

---

## Flow 0: First-time onboarding (Landing → Signup/Login → Survey → Today)

**Goal:** New user reaches a usable Today page in under 60 seconds.

**Steps:**

1. User lands on Landing page (/)
2. Clicks **Sign up** (primary CTA) or **Log in**
3. Enters email + password → submits
4. Sees a short onboarding survey (max 30 seconds, skippable):
   - **How much time do you have today?** (1–6 hours) (required)
   - **What are you focused on right now?** (optional: School / Fitness / Coding / Business / Content / Personal growth / Other)
   - **When do you work best?** (optional: Morning / Afternoon / Evening)
5. Redirect to **Today** page (/app/today)

**Success looks like:**

- User sees Today page with a clear primary action
- User understands what to do next (Add task / Add habit / Plan my day)
- AI “Plan my day” uses survey defaults if user skips

**Failure/edge cases:**

- Email already exists → show error + “Log in”
- Weak password → show rules
- User skips survey → set defaults:
  - available time = 2 hours
  - focus area = Personal growth
  - work time = Afternoon

---

## Flow 1: Tasks (Create → View → Complete)

**Goal:** User can create and finish tasks in one session.

**Steps:**

1. On Today page (or Tasks page from sidebar), user clicks **Add task**
2. Enters task title (required)
3. (Optional) Adds due date / priority (ONLY if it stays simple)
4. Task appears in Today list
5. User taps checkbox to **complete**
6. Completed task moves to Completed section (or toggled view)

**Success looks like:**

- Task saves instantly
- Completed state is obvious and satisfying

**Failure/edge cases:**

- Empty title → inline error
- Offline / API fail → “Couldn’t save, retry”
- Too many tasks → show “Top 3 priorities” hint

---

## Flow 2: Habits (Create → Mark done → Streak)

**Goal:** User creates a habit and marks it done today.

**Steps:**

1. On Today page (or Habits page from sidebar), user clicks **Add habit**
2. Enters habit name (required)
3. (Optional) Selects frequency (Daily default)
4. Habit appears in Today habits list
5. User taps **Done** for today
6. UI updates streak/progress

**Success looks like:**

- Completion is saved by date (not a single boolean)
- Streak/progress updates immediately

**Failure/edge cases:**

- Empty habit name → inline error
- Double-tap done → should not create duplicate completions
- If already completed today → show “Completed” state

---

## Flow 3: AI Plan My Day (Generate → Save → Use)

**Goal:** User generates a plan and follows it.

**Steps:**

1. On Today page, user clicks **Plan my day**
2. App asks/uses:
   - Available time today (if not set) (required)
   - Energy mode (optional: Low/Normal/High) (later if needed)
3. AI generates plan:
   - Top 3 priorities
   - 3–5 time blocks (Morning/Midday/Evening is fine)
   - Habit slots included
   - “If you’re behind…” fallback
4. User clicks **Accept plan** (Save)
5. Plan is saved for today and shown on Today page
6. User can:
   - Mark items done
   - Regenerate plan
   - Adjust by dragging/reordering (optional later)

**Success looks like:**

- Plan is readable, not overwhelming
- Plan is saved and re-openable the same day
- User can take action immediately

**Failure/edge cases:**

- No tasks/habits → AI prompts user to add at least 1–3 first
- Too many tasks → AI selects top priorities and defers the rest
- AI fails → show retry + fallback “manual plan” template

---

## Global UX Rules (MVP)

- Every screen must have a clear primary action.
- Empty states must guide the user (not a blank page).
- Mobile-friendly tap targets.
- No paragraphs of text required to understand any screen.
