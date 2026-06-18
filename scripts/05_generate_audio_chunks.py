from __future__ import annotations

from common import parse_args


def main() -> None:
    _args = parse_args("Generate per-segment audio chunks with your configured local backend")
    print("This stage is intentionally left as a local-backend integration point.")
    print("Place generated files in the configured dub chunk directory as raw_<id>.wav.")


if __name__ == "__main__":
    main()
