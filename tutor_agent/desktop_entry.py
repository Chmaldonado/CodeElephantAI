from __future__ import annotations

import argparse

from tutor_agent.bootstrap import build_services
from tutor_agent.desktop_app import run_desktop_session


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch CodeElephant Tutor desktop app.")
    parser.add_argument("--user-id", default="learner", help="Stable learner id for long-term memory.")
    args = parser.parse_args()

    services = build_services()
    run_desktop_session(user_id=args.user_id, services=services)


if __name__ == "__main__":
    main()
