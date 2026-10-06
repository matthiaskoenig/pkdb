"""Fixtures for study format 2 tests."""

import gc
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

# A performance check measures a step for an input and for SCALE times the
# input, back to back, and the larger input may take at most SCALING_LIMIT
# times the CPU time. Linear work takes four times as long and quadratic work
# sixteen times, so the check catches a quadratic regression on a slow or busy
# machine alike, where an absolute budget fails or passes by chance.
SCALE = 4
SCALING_LIMIT = 6


def cpu_seconds(step):
    """The result of a step and the CPU seconds of this process it took.

    time.process_time hardly depends on the load of the machine, unlike the
    wall clock. Garbage of the preparation is collected first.
    """
    gc.collect()
    start = time.process_time()
    result = step()
    return result, time.process_time() - start


@pytest.fixture
def linear_cpu_time():
    """Check that a step takes CPU time linear in the size of its input.

    `prepare(size)` builds the input of that size and returns the step, which
    alone is measured, for `size` and SCALE times `size`. Returns the result of
    the larger step.
    """

    def check(prepare, size):
        _, small = cpu_seconds(prepare(size))
        result, large = cpu_seconds(prepare(SCALE * size))
        assert large <= SCALING_LIMIT * small, (
            f"{SCALE} times the input took {large / max(small, 1e-9):.1f} times "
            f"the CPU time ({small:.2f} s and {large:.2f} s)"
        )
        return result

    return check


@pytest.fixture
def cpu_time():
    """Measure a step in CPU seconds: `cpu_time(step)` returns its result and its time."""
    return cpu_seconds


@pytest.fixture
def libreoffice_resave(tmp_path_factory):
    """Re-save a workbook with headless LibreOffice Calc, as a curator's save would.

    Tests using it skip when `soffice` is missing, and fail instead when the
    environment variable PKDB_REQUIRE_LIBREOFFICE is 1, as on the Linux CI job.
    """
    soffice = shutil.which("soffice")
    if soffice is None:
        message = "LibreOffice (soffice) is not installed"
        if os.environ.get("PKDB_REQUIRE_LIBREOFFICE") == "1":
            pytest.fail(f"{message}, but PKDB_REQUIRE_LIBREOFFICE=1 requires it")
        pytest.skip(message)
    # A fresh profile, so that parallel runs and the user's profile do not interfere.
    work = tmp_path_factory.mktemp("libreoffice")
    profile = (work / "lo-profile").as_uri()

    def resave(path: Path) -> Path:
        output = tmp_path_factory.mktemp("resaved")
        completed = subprocess.run(
            [
                soffice,
                f"-env:UserInstallation={profile}",
                "--headless",
                "--calc",
                "--convert-to",
                "xlsx:Calc MS Excel 2007 XML",
                "--outdir",
                str(output),
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        saved = output / path.name
        if completed.returncode != 0 or not saved.is_file():
            output_text = f"{completed.stdout}{completed.stderr}".strip()
            pytest.fail(
                f"LibreOffice could not re-save {path.name} "
                f"(exit {completed.returncode}): {output_text}"
            )
        return saved

    return resave
