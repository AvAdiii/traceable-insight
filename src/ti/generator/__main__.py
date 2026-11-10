"""`uv run python -m ti.generator [seed]` writes data/demo/*.xlsx and ground_truth.json."""
import sys

from ti import config
from ti.generator import generate

t = generate(config.DEMO_DIR, int(sys.argv[1]) if len(sys.argv) > 1 else config.SEED)
print(f"{t['children']} children, files: {list(t['files'])}, planted issues: {len(t['planted'])}")
