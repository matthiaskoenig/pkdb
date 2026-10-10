"""Fixtures for study format 2 tests."""

import gc
import math
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

# A performance check measures a step for an input and for SCALE times the
# input, and the larger input may take at most SCALING_LIMIT times the CPU
# time. Linear work takes four times as long and quadratic work sixteen times,
# so the check catches a quadratic regression on a slow or busy machine alike,
# where an absolute budget fails or passes by chance. Each size is measured up
# to REPEATS times and its least CPU time counts, since a busy machine only
# ever adds time. Repeats cost nothing while the first ones pass.
SCALE = 4
SCALING_LIMIT = 6
REPEATS = 6


def cpu_seconds(step):
    """The result of a step and the CPU seconds of this thread it took.

    time.thread_time hardly depends on the load of the machine, unlike the wall
    clock, and unlike time.process_time it leaves out the other threads of the
    process, such as servers or watchers of other tests. Garbage of the
    preparation is collected first, and the collector is paused during the
    step: a collection pass walks the whole live heap, which a larger input
    makes larger, and it runs at moments that depend on earlier allocations.
    """
    gc.collect()
    gc.disable()
    try:
        start = time.thread_time()
        result = step()
        return result, time.thread_time() - start
    finally:
        gc.enable()


@pytest.fixture
def linear_cpu_time():
    """Check that a step takes CPU time linear in the size of its input.

    `prepare(size)` returns the step for an input of that size, which alone is
    measured; it is called for every measurement, so a step that changes its
    input gets a fresh one each time. Steps of `size` and of SCALE times `size`
    alternate, so that both meet the same load of the machine, up to REPEATS
    times each, until the least CPU time of the larger steps is within
    SCALING_LIMIT times the least of the smaller ones. Returns the result of
    the last larger step.
    """

    def check(prepare, size):
        small = large = math.inf
        for _ in range(REPEATS):
            small = min(small, cpu_seconds(prepare(size))[1])
            result, seconds = cpu_seconds(prepare(SCALE * size))
            large = min(large, seconds)
            if large <= SCALING_LIMIT * small:
                break
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
