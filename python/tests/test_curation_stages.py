"""Every progress stage of a real upload is classified as before or after sending the study.

The local curation server treats an interrupted upload as an unknown outcome unless its stage
is one of `UNSENT_STAGES`. These tests record the stages that the preparation and the client
emit against a mock server, with whether the upload request had started, so that a new stage
can never be taken for one before sending by accident.
"""

import httpx2
import pytest

from pkdb.client import Client
from pkdb.curation.jobs import UNSENT_STAGES, maybe_sent
from pkdb.domain.validation import PROCESSING_VERSION
from pkdb.domain.vocabulary import vocabulary_hash
from pkdb.preparation import prepare

ENDPOINT = "https://example.test"


class Recorder:
    """The stages of the progress events, each with whether the upload request had started."""

    def __init__(self):
        self.sending = False
        self.stages: list[tuple[str, bool]] = []

    def progress(self, event):
        self.stages.append((event.stage, self.sending))

    def transport(self, sid):
        """A mock server that notes when the upload request reaches the transport."""
        recorder = self

        def handle(request):
            if request.method == "GET":
                assert request.url.path == "/api/v2/capabilities"
                return httpx2.Response(200, json=recorder.capabilities)
            assert request.method == "PUT"
            return httpx2.Response(
                201, json={"sid": sid, "created": True, "digest": "d", "counts": {}}
            )

        class Sending(httpx2.MockTransport):
            def handle_request(self, request):
                if request.method == "PUT":
                    # From here on the server may have the study: the body streams to it.
                    recorder.sending = True
                return super().handle_request(request)

        return Sending(handle)

    def client(self, vocabulary, sid):
        self.capabilities = {
            "schema_version": 1,
            "server_version": "0.10.2",
            "processing_version": PROCESSING_VERSION,
            "vocabulary_version": vocabulary.version,
            "vocabulary_hash": vocabulary_hash(vocabulary),
            "upload_report_versions": [1, 2],
            "upload_limits": {
                "max_rows": 1_000_000,
                "max_files": 256,
                "max_upload_bytes": 100_000_000,
                "max_attachment_bytes": 100_000_000,
            },
        }
        transport = httpx2.Client(transport=self.transport(sid))
        return Client(
            endpoint=ENDPOINT,
            api_key="secret",
            transport=transport,
            progress=self.progress,
        )

    def assert_classified(self):
        """Each stage before the request is unsent, and each stage from the request on is not."""
        assert self.stages
        for stage, sending in self.stages:
            assert maybe_sent({"action": "upload", "stage": stage}) is sending, stage


def test_the_stages_of_an_upload_as_the_curation_server_runs_it(
    valid_study, sf_vocabulary
):
    # As run_job: the job starts queued, prepares with its progress, then uploads.
    recorder = Recorder()
    recorder.stages.append(("queued", False))
    prepared = prepare(
        valid_study, vocabulary=sf_vocabulary, progress=recorder.progress
    )
    with recorder.client(sf_vocabulary, "caffeine/Example") as client:
        client.upload(prepared)
    recorder.assert_classified()
    stages = [stage for stage, _ in recorder.stages]
    assert {"read", "validate", "compatibility", "transfer"} <= set(stages)
    assert stages[-2:] == ["server_validation", "complete"]


def test_the_stages_of_an_upload_of_a_folder(valid_study, sf_vocabulary, tmp_path):
    from pkdb.cache import VocabularyCache

    cache = VocabularyCache(tmp_path / "cache")
    cache.store(ENDPOINT, sf_vocabulary)
    recorder = Recorder()
    with recorder.client(sf_vocabulary, "caffeine/Example") as client:
        client.cache = cache
        client.upload(valid_study)
    recorder.assert_classified()


def test_the_stages_of_preparing_a_format_1_folder(study_folder, vocabulary):
    recorder = Recorder()
    prepare(study_folder, vocabulary=vocabulary, progress=recorder.progress)
    recorder.assert_classified()
    assert "parse" in {stage for stage, _ in recorder.stages}


@pytest.mark.parametrize("stage", sorted(UNSENT_STAGES))
def test_an_unsent_stage_is_unsent_only_for_an_upload(stage):
    assert maybe_sent({"action": "upload", "stage": stage}) is False
    assert maybe_sent({"action": "validate", "stage": "transfer"}) is False


def test_an_upload_without_a_known_unsent_stage_may_have_been_sent():
    assert maybe_sent({"action": "upload"}) is True
    assert maybe_sent({"action": "upload", "stage": "a_later_stage"}) is True
