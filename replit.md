# GroundTube

A full-featured video-sharing web platform inspired by YouTube, built with Python/Flask. Users can register, upload MP4/WEBM/MP3/WAV files, watch videos with an HTML5 player, like/dislike/comment, subscribe to channels, and search by title, tag, or category. A master admin panel provides manual moderation with no automated bans or tracking.

## Run & Operate

- `cd artifacts/groundtube && python3 app.py` — run GroundTube on port 8000 (managed via the "GroundTube" workflow)
- `pnpm --filter @workspace/api-server run dev` — run the legacy API server (port 5000, unused)
- `pnpm run typecheck` — typecheck TypeScript packages

## Stack

- Backend: Python 3.11, Flask 3, Flask-SQLAlchemy, Flask-Login
- Database: SQLite (`artifacts/groundtube/groundtube.db`)
- Frontend: HTML5, CSS3, Vanilla JavaScript (no frameworks)
- File Storage: `artifacts/groundtube/static/uploads/` (local filesystem)
- Auth: Session/cookie only — no IP tracking, no device fingerprinting

## Where things live

- `artifacts/groundtube/app.py` — entire Flask app: models, routes, helpers
- `artifacts/groundtube/static/css/style.css` — dark YouTube-aesthetic theme
- `artifacts/groundtube/static/js/main.js` — like/dislike AJAX, comments, upload UX
- `artifacts/groundtube/templates/` — Jinja2 templates (base, index, watch, upload, channel, admin…)
- `artifacts/groundtube/static/uploads/` — video/, audio/, thumbnails/, avatars/
- `artifacts/groundtube/groundtube.db` — SQLite database (auto-created on first run)

## Admin Access

Register an account with the **username `admin`** — it is automatically promoted to Master Admin role and gains access to `/admin`.

## Architecture decisions

- Single-file Flask app (`app.py`) — all models and routes in one file for simplicity; no blueprints needed at this scale.
- SQLite database — sufficient for a self-hosted platform; swap `SQLALCHEMY_DATABASE_URI` for PostgreSQL with no code changes.
- No IP/fingerprint tracking anywhere — account isolation is enforced at the model level; creating a new account has no link to previous ones.
- All moderation is manual — no automated ban logic exists in the codebase.
- `PORT` env var respected at startup — `int(os.environ.get('PORT', 8000))`.

## Product

- **Home feed** — paginated grid of latest uploads
- **Trending** — most-viewed in the last 7 days
- **Categories** — Gaming, Music, Sports, Education, Technology, Entertainment, News, Travel, Comedy, Art, Science, Automotive, Food, Fashion, Other
- **Search** — full-text search across title, description, and tags
- **Watch page** — HTML5 video/audio player, like/dislike, comments with replies, subscribe button, related videos sidebar
- **Upload** — drag-and-drop or browse; supports MP4, WEBM, MP3, WAV + optional custom thumbnail
- **Channel page** — video grid + About tab, subscriber count, subscribe button
- **Settings** — edit bio/avatar, change password
- **Admin panel** — `/admin` — stats overview, user management (suspend/delete), video removal, comment moderation, report queue

## User preferences

_Populate as you build._

## Gotchas

- Flask dev server — for production use, run behind gunicorn + nginx.
- Upload folder is local — files are not replicated across deployments; use object storage for production.
- The `admin` username is hardcoded as the admin trigger — first registration with that name gets admin role.
