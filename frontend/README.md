# Capture Spine Basic - Frontend

A modern React admin dashboard for managing SEC filing feeds, inspired by [Metronic Layout 16](https://keenthemes.com/metronic/starter-kits/vite/layout-16).

## Tech Stack

- **React 19** - Latest React with modern features
- **Vite 6** - Fast build tool and dev server
- **TypeScript 5.6** - Type-safe JavaScript
- **Tailwind CSS 3.4** - Utility-first CSS
- **React Router 7** - Client-side routing
- **TanStack Query 5** - Data fetching and caching
- **lucide-react** - Beautiful icons

## Features

- 🎨 **Metronic-style Design** - Dark sidebar, clean cards, professional color scheme
- 🌙 **Dark Mode** - Full dark mode support with system preference detection
- 📱 **Responsive** - Works on all screen sizes
- 📰 **Newsfeed Reader** - 3-panel layout for browsing SEC filings
- ⚙️ **Feed Management** - Configure and manage feed sources
- 🔔 **Notifications** - Real-time alerts and updates
- ⚡ **Settings** - Profile, appearance, and system configuration

## Development

```bash
# Install dependencies
npm install

# Start dev server (default: http://localhost:3000)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Type check
npm run typecheck

# Lint
npm run lint
```

## Project Structure

```
src/
├── api/                # API client and hooks
│   ├── index.ts       # Axios client and API functions
│   └── hooks.ts       # React Query hooks
├── components/         # Reusable components
│   └── layout/        # Layout components (Sidebar, Header)
├── layouts/           # Page layouts
│   └── AdminLayout.tsx
├── pages/             # Route pages
│   ├── DashboardPage.tsx
│   ├── NewsfeedPage.tsx
│   ├── FeedsPage.tsx
│   ├── SettingsPage.tsx
│   └── NotificationsPage.tsx
├── App.tsx            # Route definitions
├── main.tsx           # App entry point
└── index.css          # Global styles
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API base URL | `/api` |

## API Integration

The frontend uses React Query for data fetching. API hooks are in `src/api/hooks.ts`:

```tsx
import { useFeeds, useRecords, useHealth } from './api/hooks'

function MyComponent() {
  const { data: feeds, isLoading } = useFeeds()
  const { data: records } = useRecords({ feed_id: 'sec-latest' })
  const { data: health } = useHealth()
  // ...
}
```

## Docker Deployment

```bash
# Build and run with Docker Compose (from capture-spine-basic directory)
docker compose up -d

# View frontend logs
docker compose logs -f frontend

# Get frontend port
docker compose ps frontend
```

## Design System

### Colors

- **Primary**: `#3b82f6` (Blue)
- **Sidebar**: `#1E1E2D` (Dark purple-gray)
- **Success**: `#50cd89` (Green)
- **Warning**: `#ffc700` (Amber)
- **Danger**: `#f1416c` (Red)

### Components

Custom Tailwind components in `index.css`:

- `.card` - Elevated card with shadow
- `.btn`, `.btn-primary`, `.btn-secondary` - Buttons
- `.badge`, `.badge-*` - Status badges
- `.input` - Form inputs
- `.toggle` - Switch toggle

## License

MIT
