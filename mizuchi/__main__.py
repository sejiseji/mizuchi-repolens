"""CLI entrypoint for Mizuchi RepoLens."""

from __future__ import annotations

import argparse

from mizuchi.api.server import LOCAL_HOST, create_server
from mizuchi.runtime.state import RuntimeState


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Mizuchi RepoLens local API server.")
    parser.add_argument("--port", type=int, default=8765, help="Local API port.")
    parser.add_argument("--open-project", help="Project directory to open on startup.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    state = RuntimeState()
    if args.open_project:
        state.open_project(args.open_project)

    server = create_server(args.port, state)
    print(f"Mizuchi RepoLens API listening on http://{LOCAL_HOST}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
