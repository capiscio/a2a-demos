#!/usr/bin/env python3
"""
Video recording helper — runs demos with clean output and timing.

Usage:
    python run_video.py enforcement-demo  # 5 min video
    python run_video.py demo-two      # 10 min video (manual policy switching)
    python run_video.py agents        # 15 min video (requires running agents)
"""
import subprocess
import sys
import os

DEMOS = {
    "enforcement-demo": {
        "cmd": [sys.executable, "enforcement-demo/run_demo.py"],
        "title": "Zero to Enforcement",
        "duration": "~5 minutes",
    },
    "demo-two": {
        "cmd": [sys.executable, "demo-two/run_demo.py"],
        "title": "Policy as Code",
        "duration": "~10 minutes",
    },
    "agents": {
        "cmd": [sys.executable, "scripts/demo_driver.py", "--chain"],
        "title": "Multi-Framework Agent Trust",
        "duration": "~15 minutes",
    },
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in DEMOS:
        print("Usage: python run_video.py [enforcement-demo|demo-two|agents]")
        for key, info in DEMOS.items():
            print(f"  {key:12s} — {info['title']} ({info['duration']})")
        sys.exit(1)

    demo = DEMOS[sys.argv[1]]
    print(f"\n{'═' * 60}")
    print(f"  🎬 Recording: {demo['title']}")
    print(f"  ⏱  Duration: {demo['duration']}")
    print(f"{'═' * 60}\n")

    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    result = subprocess.run(demo["cmd"])
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
