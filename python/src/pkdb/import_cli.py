"""Import external datasets into reviewable, uploadable source study folders."""

import json
import sys
from pathlib import Path


def register(commands):
    command = commands.add_parser(
        "import", help="Import an external dataset as source-qualified studies"
    )
    providers = command.add_subparsers(dest="provider", required=True)
    osp = providers.add_parser(
        "osp", help="Import pinned OSP observed-data release v1.9"
    )
    osp.add_argument(
        "--workbook",
        type=Path,
        help="Already downloaded release workbook (checksum verified)",
    )
    osp.add_argument(
        "--output",
        type=Path,
        required=True,
        help="New directory for study folders, vocabulary, and report",
    )
    osp.add_argument(
        "--creator", required=True, help="PK-DB account attributed to this import"
    )
    osp.add_argument(
        "--offline",
        action="store_true",
        help="Require an existing workbook; never download",
    )


def run(args):
    import httpx2

    from pkdb.cache import cache_directory
    from pkdb.importers.osp.release import SHA256, URL
    from pkdb.importers.osp.workbook import import_workbook

    try:
        path = args.workbook
        if path is None:
            if args.offline:
                raise ValueError("Offline import requires --workbook")
            path = cache_directory() / "imports" / "osp" / SHA256 / "ObsDataPK_OSP.xlsx"
            if not path.exists():
                import hashlib
                from tempfile import NamedTemporaryFile

                with httpx2.Client(timeout=60, follow_redirects=True) as client:
                    response = client.get(URL)
                    response.raise_for_status()
                if hashlib.sha256(response.content).hexdigest() != SHA256:
                    raise ValueError(
                        "Downloaded workbook checksum does not match OSP v1.9"
                    )
                path.parent.mkdir(parents=True, exist_ok=True)
                with NamedTemporaryFile(dir=path.parent, delete=False) as handle:
                    handle.write(response.content)
                    temporary = Path(handle.name)
                temporary.replace(path)
        report = import_workbook(path, args.output, creator=args.creator)
        print(
            json.dumps(
                {
                    "ok": True,
                    "output": str(args.output),
                    **{
                        k: report[k]
                        for k in (
                            "release",
                            "study_count",
                            "source_rows",
                            "mapped_measurements",
                            "warning_counts",
                        )
                    },
                },
                indent=2,
            )
        )
        return 0
    except (ValueError, OSError, httpx2.HTTPError) as error:
        print(json.dumps({"ok": False, "error": str(error)}), file=sys.stderr)
        return 1
