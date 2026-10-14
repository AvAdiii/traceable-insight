"""One command, one school: `uv run python run_pipeline.py --school school_a`."""

import argparse
import sys

from ti import config, pipeline, score
from ti.llm import OllamaClient, OllamaUnavailable


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--school", default="school_a")
    ap.add_argument("--no-score", action="store_true", help="skip the ground-truth check")
    args = ap.parse_args()
    client = OllamaClient()
    try:
        client.check()
    except OllamaUnavailable as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    pipeline.run(args.school, client)
    print(f"store    {config.db_path(args.school)}")
    if not args.no_score:
        return 0 if score.report(args.school)["all_targets_met"] else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
