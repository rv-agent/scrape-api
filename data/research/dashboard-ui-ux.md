# Dashboard UI/UX Design

## Tech Stack
- Next.js 14 (App Router)
- Tailwind CSS + shadcn/ui components
- Recharts for analytics
- React Query for data fetching

## Key Pages
```
/dashboard              → Overview (usage stats, recent jobs, quick actions)
/dashboard/jobs         → Job list (filterable, sortable, paginated)
/dashboard/jobs/[id]    → Job detail (scraped data, timing, errors)
/dashboard/keys         → API key management (create, revoke, usage)
/dashboard/analytics    → Charts (requests over time, success rate, latency)
/dashboard/billing      → Plan info, usage limits, upgrade button
/dashboard/settings     → Webhooks, notifications, preferences
/dashboard/docs         → Embedded API docs
```

## Overview Cards
- Requests today / this month (vs limit)
- Success rate (%)
- Average response time
- Active jobs / queue depth

## Job List Table
- Columns: URL, Status, Created, Duration, Actions
- Filters: status (completed/failed/pending), date range
- Bulk actions: retry, delete, export
- Click row → job detail

## Analytics Charts
- Line chart: requests over time (7d, 30d, 90d)
- Pie chart: success vs failure vs timeout
- Bar chart: top domains scraped
- Heatmap: request volume by hour/day

## UX Patterns
- Skeleton loading states
- Optimistic updates
- Toast notifications for actions
- Keyboard shortcuts (j/k navigation, r refresh)
- Dark mode default (developer audience)

## Auth Flow
- API key → magic link login (email verification)
- Session via httpOnly cookie
- No password (API-first, key-based auth)

## Responsive
- Desktop-first (developer tools)
- Mobile: view-only, no complex forms
