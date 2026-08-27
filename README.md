# EduAnimate — Flask + MySQL

EduAnimate is a web-based educational animation system for difficult Mathematics, Physics, Chemistry and Computer Science concepts.

## Technology stack

- HTML5 + CSS3 + JavaScript
- GSAP + SVG/CSS animations
- Python Flask backend
- MySQL 8.4 database
- GitHub Codespaces dev container

## What the system includes

- Student registration and login
- Bcrypt password hashing
- MySQL-backed users, subjects, topics, lessons, quiz questions, attempts, progress and login sessions
- 4 subjects and 5 fully seeded animated topics
- 25 quiz questions with immediate feedback
- Student dashboard and progress tracking
- Previous / next lesson navigation
- Desktop and mobile navigation
- Teacher/Admin performance dashboard

## Start in GitHub Codespaces

1. Open the repository on GitHub.
2. Click **Code** → **Codespaces** → **Create codespace on main**.
3. Wait for the container to finish building. The configuration automatically starts MySQL 8.4, creates the database tables, seeds the course data and starts Flask on port 5000.
4. If the browser does not open automatically, open the **Ports** tab and click the URL for port **5000**.
5. For your project defence, right-click port **5000** → **Port Visibility** → **Public**. GitHub may reset forwarded ports to Private when the codespace restarts, so confirm this before presenting.

## Make your account Admin

First register your normal account in the website. Then, in the Codespaces terminal, run:

```bash
flask --app app make-admin
```

Enter the registered email address. Log out and back in to refresh the role.

## Useful checks

```bash
curl http://127.0.0.1:5000/api/health
```

Expected response includes `"database":"MySQL"`.

To see the Flask log:

```bash
tail -f /tmp/eduanimate-flask.log
```

To connect directly to MySQL inside the database container:

```bash
docker compose -f .devcontainer/docker-compose.yml exec db mysql -ueduanimate -peduanimate_dev eduanimate
```

> The database credentials in the dev container are development-only credentials for this Codespaces demonstration environment. The MySQL port is not forwarded publicly.
