import pytest

from pkdb.repository import location, repository_root, study_folders, substances


def make(root, *locations):
    for value in locations:
        (root / "studies" / value).mkdir(parents=True)


def test_the_root_is_found_from_a_study_folder(tmp_path):
    make(tmp_path, "caffeine/Harder1988")
    assert repository_root(tmp_path / "studies" / "caffeine" / "Harder1988") == tmp_path
    with pytest.raises(ValueError, match="studies"):
        repository_root(tmp_path.parent)


def test_study_folders_in_natural_order_without_hidden_and_links(tmp_path):
    make(
        tmp_path,
        "caffeine/Study10",
        "caffeine/Study2",
        "acetaminophen/A1",
        "caffeine/.hidden",
    )
    (tmp_path / "studies" / "caffeine" / "link").symlink_to(
        tmp_path / "studies" / "caffeine" / "Study2"
    )
    assert [location(p) for p in study_folders(tmp_path)] == [
        "acetaminophen/A1",
        "caffeine/Study2",
        "caffeine/Study10",
    ]
    assert substances(tmp_path) == ["acetaminophen", "caffeine"]
