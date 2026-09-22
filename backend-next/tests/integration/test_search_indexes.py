from sqlalchemy import event, select, text

from pkdb.db.models.vocabulary import VocabularyNode, VocabularyTerm
from pkdb.db.textsearch import text_match
from pkdb.schemas.queries import QuerySpec
from pkdb.schemas.security import Principal
from pkdb.services.queries import QueryService


def test_text_search_indexes_exist_and_are_usable(session_factory):
    engine = session_factory.kw["bind"]
    with session_factory.begin() as session:
        indexes = dict(
            session.execute(
                text(
                    "SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = current_schema()"
                )
            ).all()
        )
        for name in (
            "ix_vocabulary_nodes_search",
            "ix_vocabulary_terms_search",
            "ix_studies_search",
            "ix_references_search",
        ):
            assert "USING gin" in indexes[name]
        session.execute(text("SET LOCAL enable_seqscan = off"))
        statement = select(VocabularyTerm.node_sid).where(
            text_match([VocabularyTerm.value], "unique phrase")
        )
        sql = str(statement.compile(engine, compile_kwargs={"literal_binds": True}))
        plan = session.execute(text("EXPLAIN (FORMAT JSON) " + sql)).scalar_one()
        assert "ix_vocabulary_terms_search" in str(plan)


def test_vocabulary_page_loading_has_fixed_query_count(session_factory):
    with session_factory.begin() as session:
        session.add_all(
            [
                VocabularyNode(sid=f"node-{n}", name=f"node {n}", kind="info_node")
                for n in range(100)
            ]
        )
    engine = session_factory.kw["bind"]
    queries = QueryService(session_factory)
    statements = []

    def capture(*args):
        statements.append(args[2])

    event.listen(engine, "before_cursor_execute", capture)
    try:
        queries.search(QuerySpec(entity="info_nodes", page_size=1), Principal())
        small = len(statements)
        statements.clear()
        page = queries.search(
            QuerySpec(entity="info_nodes", page_size=100), Principal()
        )
        assert page.count == 100
        assert len(statements) == small <= 5
    finally:
        event.remove(engine, "before_cursor_execute", capture)


def test_study_page_query_count_is_independent_of_page_length(
    ingestion_context, valid_bundle, session_factory
):
    from copy import deepcopy

    from sqlalchemy import event

    from pkdb.schemas.queries import QuerySpec
    from pkdb.services.queries import QueryService

    ingestion, principal = ingestion_context
    for number in range(6):
        bundle = deepcopy(valid_bundle)
        bundle.study["sid"] = f"PAGE{number}"
        bundle.study["name"] = f"Page {number}"
        bundle.reference["sid"] = f"PAGEREF{number}"
        bundle.study["reference"] = bundle.reference["sid"]
        ingestion.replace(bundle, principal)
    engine = session_factory.kw["bind"]
    statements = []

    def capture(*args):
        statements.append(args[2])

    service = QueryService(session_factory)
    event.listen(engine, "before_cursor_execute", capture)
    try:
        first = service.search(QuerySpec(entity="studies", page_size=1), principal)
        small = len(statements)
        statements.clear()
        full = service.search(QuerySpec(entity="studies", page_size=20), principal)
        large = len(statements)
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    assert len(first.items) == 1 and len(full.items) == 6
    assert small == large
    assert large <= 20
