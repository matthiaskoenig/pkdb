"""Owned saved criteria and bounded exports with current permissions rechecked."""

import csv
import json
from datetime import UTC, datetime, timedelta
from importlib.resources import files
from tempfile import TemporaryFile
from threading import BoundedSemaphore
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy import delete, func, select

from pkdb.db.analysis import ENTITIES, statement
from pkdb.db.models.saved_queries import SavedQuery
from pkdb.db.selection import selection
from pkdb.schemas.analysis import ANALYSIS_MODELS
from pkdb.schemas.filters import FilterSpec
from pkdb.schemas.queries import QuerySpec
from pkdb.schemas.security import Principal
from pkdb.services.analysis import AnalysisService
from pkdb.services.authentication import revalidate_principal
from pkdb.services.authorization import AuthorizationDenied


class ExportBusy(RuntimeError):
    pass


class ExportLimit(ValueError):
    pass


class LimitedTextWriter:
    def __init__(self, target, maximum):
        self.target = target
        self.maximum = maximum
        self.size = 0

    def write(self, value):
        data = value.encode("utf-8")
        self.size += len(data)
        if self.size > self.maximum:
            raise ExportLimit("Export exceeds configured byte limit")
        self.target.write(data)
        return len(value)


class ExportService:
    def __init__(self, session_factory, queries, settings=None):
        self.session_factory = session_factory
        self.queries = queries
        self.analysis = AnalysisService(session_factory)
        self.max_bytes = settings.export_max_bytes if settings else 256 * 1024 * 1024
        self.max_rows = settings.export_max_rows if settings else 1_000_000
        self.slots = BoundedSemaphore(settings.export_concurrency if settings else 2)

    @staticmethod
    def current_principal(session, principal):
        if principal.user_id is None:
            return Principal()
        return revalidate_principal(principal, session)

    def create_filter(self, query: QuerySpec | FilterSpec, principal: Principal):
        if isinstance(query, QuerySpec) and query.entity not in ENTITIES:
            raise ValueError("Unsupported export entity")
        with self.session_factory.begin() as session:
            current = self.current_principal(session, principal)
            if isinstance(query, FilterSpec):
                selection(query, current)
            else:
                statement(query.entity, query, current)
            now = datetime.now(UTC)
            session.execute(delete(SavedQuery).where(SavedQuery.expires_at <= now))
            saved = SavedQuery(
                owner_id=current.user_id,
                criteria=query.model_dump(mode="json"),
                expires_at=now + timedelta(hours=24),
            )
            session.add(saved)
            session.flush()
            return saved.id

    def load_filter(self, identifier, principal, session):
        current = self.current_principal(session, principal)
        saved = session.get(SavedQuery, identifier)
        if saved is None or saved.expires_at <= datetime.now(UTC):
            raise LookupError("Saved filter expired or unavailable")
        if (
            saved.owner_id is not None
            and saved.owner_id != current.user_id
            and current.role != "admin"
        ):
            raise AuthorizationDenied("Saved filter belongs to another account")
        model = FilterSpec if "queries" in saved.criteria else QuerySpec
        return model.model_validate(saved.criteria), current

    def overview(self, identifier, principal):
        with self.session_factory() as session:
            session.connection(execution_options={"isolation_level": "REPEATABLE READ"})
            spec, current = self.load_filter(identifier, principal, session)
            if not isinstance(spec, FilterSpec):
                raise ValueError("Expected a multi-entity filter")
            selected = selection(spec, current)
            counts = select(
                *(
                    select(func.count())
                    .select_from(query.subquery())
                    .scalar_subquery()
                    .label(entity)
                    for entity, query in selected.items()
                    if entity != "subsets"
                )
            )
            return {
                "uuid": str(identifier),
                **dict(session.execute(counts).mappings().one()),
            }

    def write_csv(self, target, session, entity, query, principal):
        writer = csv.writer(
            LimitedTextWriter(target, self.max_bytes), lineterminator="\n"
        )
        columns = list(ANALYSIS_MODELS[entity].model_fields)
        count = 0
        for index, row in enumerate(
            self.analysis.iter_rows(session, entity, query, principal)
        ):
            if index >= self.max_rows:
                raise ExportLimit("Export exceeds configured row limit")
            if index == 0:
                writer.writerow(["", *columns])
            writer.writerow([index, *(row[column] for column in columns)])
            count += 1
        if count == 0:
            writer.writerow([""])

    def write_zip(self, target, session, spec, principal):
        from pkdb.db.models.vocabulary import VocabularyNode, VocabularyTerm
        from pkdb.db.scatter_export import rows as scatter_rows

        if not isinstance(spec, FilterSpec):
            raise ValueError("ZIP requires a multi-entity filter")
        total_bytes = 0
        total_rows = 0
        with ZipFile(target, "w", ZIP_DEFLATED) as archive:
            for entity in (
                "studies",
                "groups",
                "individuals",
                "interventions",
                "outputs",
                "timecourses",
                "scatters",
                "info_nodes",
            ):
                if entity == "scatters":
                    rows = scatter_rows(session, spec, principal)
                    columns = []
                elif entity == "info_nodes":
                    label = (
                        select(VocabularyTerm.value)
                        .where(
                            VocabularyTerm.node_sid == VocabularyNode.sid,
                            VocabularyTerm.kind == "label",
                        )
                        .order_by(VocabularyTerm.value)
                        .limit(1)
                        .scalar_subquery()
                    )
                    nodes = session.execute(
                        select(VocabularyNode, label)
                        .order_by(VocabularyNode.sid)
                        .execution_options(yield_per=500)
                    )
                    rows = (
                        {
                            "sid": node.sid,
                            "label": json.loads(label) if label else node.name,
                            "ntype": "measurement_type"
                            if node.kind == "measurement"
                            else node.kind,
                        }
                        for node, label in nodes
                    )
                    columns = ["sid", "label", "ntype"]
                else:
                    rows = self.analysis.iter_rows(
                        session,
                        entity,
                        QuerySpec.model_validate({"entity": ENTITIES[entity]}),
                        principal,
                        filter_spec=spec,
                    )
                    columns = list(ANALYSIS_MODELS[entity].model_fields)
                with archive.open(entity + ".csv", "w") as member:
                    output = LimitedTextWriter(member, self.max_bytes - total_bytes)
                    writer = csv.writer(output, lineterminator="\n")
                    count = 0
                    for index, row in enumerate(rows):
                        total_rows += 1
                        if total_rows > self.max_rows:
                            raise ExportLimit("Export exceeds configured row limit")
                        if index == 0:
                            columns = columns or list(row)
                            writer.writerow(["", *columns])
                        writer.writerow([index, *(row[column] for column in columns)])
                        count += 1
                    if count == 0:
                        writer.writerow([""])
                    total_bytes += output.size
            for name in ("README.md", "TERMS_OF_USE.md"):
                data = files("pkdb").joinpath("assets", "download", name).read_bytes()
                total_bytes += len(data)
                if total_bytes > self.max_bytes:
                    raise ExportLimit("Export exceeds configured byte limit")
                archive.writestr(name, data)
        if target.tell() > self.max_bytes:
            raise ExportLimit("Export exceeds configured byte limit")

    def stream_export(self, filter_id, format: str, principal: Principal):
        if format not in {"csv", "zip"}:
            raise ValueError("Unsupported export format")
        if not self.slots.acquire(blocking=False):
            raise ExportBusy("Export capacity reached")
        try:
            with TemporaryFile(mode="w+b") as artifact:
                # Build under one repeatable-read snapshot in one worker. Only the
                # resulting file is streamed, so a Session never crosses workers.
                with self.session_factory() as session:
                    session.connection(
                        execution_options={"isolation_level": "REPEATABLE READ"}
                    )
                    query, current = self.load_filter(filter_id, principal, session)
                    if format == "zip":
                        self.write_zip(artifact, session, query, current)
                    elif isinstance(query, QuerySpec):
                        self.write_csv(artifact, session, query.entity, query, current)
                    else:
                        raise ValueError("CSV requires a single-entity filter")
                artifact.seek(0)
                while chunk := artifact.read(64 * 1024):
                    yield chunk
        finally:
            self.slots.release()
