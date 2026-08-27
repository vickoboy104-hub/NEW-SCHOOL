#!/usr/bin/env bash
set -e
cd /workspaces/eduanimate
python scripts/init_db.py
PYTHONPATH=/workspaces/eduanimate python scripts/expand_courses.py
pkill -f "flask --app app run" 2>/dev/null || true
nohup flask --app app run --host=0.0.0.0 --port=5000 > /tmp/eduanimate-flask.log 2>&1 &
echo "EduAnimate started on port 5000 with 20 animated lessons"
