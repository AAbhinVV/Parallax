import argparse
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from parallax_backend.config import settings


def pg_dump_url(database_url: str) -> str:
    return urlunsplit(urlsplit(database_url.replace("postgresql+asyncpg://", "postgresql://")))


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a local PostgreSQL custom-format backup")
    parser.add_argument("--output-dir", type=Path, default=Path("backups"))
    parser.add_argument(
        "--docker",
        action="store_true",
        help="Run pg_dump inside the Compose PostgreSQL container",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output = args.output_dir / f"parallax-{timestamp}.dump"
    if args.docker:
        parsed = urlsplit(pg_dump_url(settings.database_url))
        database = parsed.path.lstrip("/")
        username = parsed.username or "parallax"
        with output.open("wb") as stream:
            subprocess.run(
                [
                    "docker",
                    "compose",
                    "exec",
                    "-T",
                    "postgres",
                    "pg_dump",
                    "--format=custom",
                    "--username",
                    username,
                    database,
                ],
                check=True,
                stdout=stream,
            )
    else:
        subprocess.run(
            [
                "pg_dump",
                "--format=custom",
                "--file",
                str(output),
                pg_dump_url(settings.database_url),
            ],
            check=True,
        )
    print(output.resolve())


if __name__ == "__main__":
    main()
