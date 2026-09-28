"""Print how many subjects a dataset has, counted by Chiron's own engine, for check.py.

Run inside the chiron container:  python /app/deploy/count_subjects.py synthea-10k
(Chiron's count API counts the user's open query instead, which changes as people work.)
"""

import sys

from chiron_mcp.bootstrap import ensure_django

ensure_django()

from chiron.query_engine import get_querytool  # noqa: E402
from chiron_mcp import identity  # noqa: E402

print(get_querytool(identity.resolve(sys.argv[1]).chironuser, []).get_cohort_count())
