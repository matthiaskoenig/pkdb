"""One vocabulary rule for every offline validation: file, checkout lock, endpoint cache, bundled."""

import json
import shutil

import pytest
from check_fixtures import study_checkout

from pkdb.cache import VocabularyCache, bundled_vocabulary, select_vocabulary
from pkdb.cli import main
from pkdb.curation import engine as module
from pkdb.domain.vocabulary import Vocabulary

ENDPOINT = "https://example.test"


@pytest.fixture
def setup(tmp_path, valid_files, sf_vocabulary, monkeypatch):
    """A checkout with a study and an empty lock, and a cache with a vocabulary that accepts the study."""
    monkeypatch.delenv("PKDB_ENDPOINT", raising=False)
    root, studies = study_checkout(tmp_path / "data", valid_files, "caffeine/A")
    Vocabulary(version="locked", measurements=()).save(root / "vocabulary.lock.json")
    cache = VocabularyCache(tmp_path / "cache")
    cache.store(ENDPOINT, sf_vocabulary)
    return root, studies["caffeine/A"], cache, tmp_path


def test_the_lock_of_the_checkout_wins_over_the_cache(setup):
    root, folder, cache, tmp_path = setup
    chosen = select_vocabulary(None, ENDPOINT, cache, folder)
    assert chosen.version == "locked"
    assert select_vocabulary(None, ENDPOINT, cache, root).version == "locked"
    explicit = tmp_path / "explicit.json"
    Vocabulary(version="explicit", measurements=()).save(explicit)
    assert select_vocabulary(explicit, ENDPOINT, cache, folder).version == "explicit"


def test_outside_a_checkout_the_cache_then_the_bundled_vocabulary_decide(
    setup, tmp_path
):
    _, _, cache, _ = setup
    elsewhere = tmp_path / "elsewhere" / "Study"
    elsewhere.mkdir(parents=True)
    assert select_vocabulary(None, ENDPOINT, cache, elsewhere).version == (
        "studyformat-test"
    )
    assert select_vocabulary(None, None, cache, elsewhere).version == (
        bundled_vocabulary().version
    )
    assert select_vocabulary(None, None, cache).version == bundled_vocabulary().version


def run_validate(folder, cache, capsys, *extra):
    code = main(
        [
            *("validate", str(folder), "--offline"),
            *("--endpoint", ENDPOINT, "--cache-dir", str(cache.directory)),
            *extra,
        ]
    )
    return code, json.loads(capsys.readouterr().out)


def test_validate_offline_uses_the_lock_before_the_cache(setup, capsys):
    root, folder, cache, _ = setup
    code, _ = run_validate(folder, cache, capsys)
    assert code == 1  # the empty lock does not know the species
    (root / "vocabulary.lock.json").unlink()
    code, _ = run_validate(folder, cache, capsys)
    assert code == 0  # the cached vocabulary of the endpoint


def test_validate_offline_outside_a_checkout_keeps_the_cache(setup, tmp_path, capsys):
    _, folder, cache, _ = setup
    copy = tmp_path / "scratch" / "A"
    copy.parent.mkdir()
    shutil.copytree(folder, copy)
    code, _ = run_validate(copy, cache, capsys)
    assert code == 0


def test_the_curation_app_uses_the_lock_of_the_checkout(setup, tmp_path_factory):
    root, folder, cache, _ = setup
    engine = module.CurationEngine(
        root, state_dir=tmp_path_factory.mktemp("state"), offline=True, start=False
    )
    try:
        engine.endpoint = ENDPOINT
        engine.cache = cache
        assert engine._local_vocabulary(folder).version == "locked"
        assert engine._local_vocabulary().version == "locked"
        (root / "vocabulary.lock.json").unlink()
        assert engine._local_vocabulary(folder).version == "studyformat-test"
    finally:
        engine.close()


def test_a_broken_lock_is_an_error_but_a_broken_cache_falls_back(
    setup, tmp_path_factory
):
    root, folder, cache, _ = setup
    engine = module.CurationEngine(
        root, state_dir=tmp_path_factory.mktemp("state"), offline=True, start=False
    )
    try:
        engine.endpoint = ENDPOINT
        engine.cache = cache
        (root / "vocabulary.lock.json").write_text("{", encoding="utf-8")
        with pytest.raises(ValueError, match="vocabulary.lock.json"):
            engine._local_vocabulary(folder)
        (root / "vocabulary.lock.json").unlink()
        for pointer in (cache.directory / "endpoints").iterdir():
            pointer.write_text("{", encoding="utf-8")
        version = engine._local_vocabulary(folder).version
        assert version == bundled_vocabulary().version
    finally:
        engine.close()
