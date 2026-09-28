#!/bin/sh
# Start Chiron. On the first start against an empty database this also builds the demo:
# the data dictionary, a real ETL of the bundled synthetic patients, and the demo
# accounts. Later starts check that in a second, and finish it if a start was cut short.
set -e
cd /app
python scripts/bootstrap_demo.py --resume

cd /app/vendor/is4r-chiron/test_project
python manage.py migrate --noinput -v 0
python manage.py collectstatic --noinput -v 0
exec gunicorn project.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-3}" \
  --timeout 180 \
  --access-logfile - \
  --forwarded-allow-ips '*'
