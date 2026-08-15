from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.rga_agent import RgaAgent


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the lightweight RGA agent scaffold")
    parser.add_argument("task", nargs="?", default="Assist with RGA workflow", help="Natural-language task for the agent")
    args = parser.parse_args()

    agent = RgaAgent()
    result = agent.run(args.task)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
