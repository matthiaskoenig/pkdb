"""The build hook refuses release builds without the curation app assets."""

import importlib
from pathlib import Path
from unittest.mock import Mock

import pytest

PROJECT = Path(__file__).parents[1]


@pytest.fixture
def hatch_build(monkeypatch):
    monkeypatch.syspath_prepend(str(PROJECT))
    monkeypatch.delenv("PKDB_BUILD_WITHOUT_CURATION_APP", raising=False)
    return importlib.import_module("hatch_build")


def _hook(hatch_build, root, target):
    # The arguments hatchling passes to a build hook.
    return hatch_build.CustomBuildHook(
        str(root), {}, Mock(), Mock(), str(root / "dist"), target
    )


def _built(root):
    index = root / "src" / "pkdb" / "curation" / "static" / "index.html"
    index.parent.mkdir(parents=True)
    index.write_text("<!doctype html>")


@pytest.mark.parametrize("target", ["wheel", "sdist"])
def test_release_builds_require_the_assets(hatch_build, tmp_path, target):
    with pytest.raises(RuntimeError, match="npm run build:curation"):
        _hook(hatch_build, tmp_path, target).initialize("standard", {})


@pytest.mark.parametrize("target", ["wheel", "sdist"])
def test_release_builds_pass_with_the_assets(hatch_build, tmp_path, target):
    _built(tmp_path)
    _hook(hatch_build, tmp_path, target).initialize("standard", {})


def test_editable_installs_skip_the_check_at_build_time(hatch_build, tmp_path):
    _hook(hatch_build, tmp_path, "wheel").initialize("editable", {})


def test_builds_without_the_app_can_opt_out(hatch_build, tmp_path, monkeypatch):
    monkeypatch.setenv("PKDB_BUILD_WITHOUT_CURATION_APP", "1")
    _hook(hatch_build, tmp_path, "wheel").initialize("standard", {})
