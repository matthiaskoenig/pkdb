"""Small, typed public data interface using the shared scientific services."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from pkdb.schemas.data import DataPage, DataQuery, ScientificRecord
from pkdb.schemas.filters import FilterSpec
from pkdb.schemas.queries import Predicate, QuerySpec
from pkdb.schemas.responses import OutputResponse, StudyResponse
from pkdb_server.api.exports import download_response
from pkdb_server.services.statistics import StatisticsOverview

router = APIRouter(prefix="/api/v2", tags=["Data"])


class StudyParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    substance: str | None = Field(default=None, min_length=1, max_length=255)
    study_sid: str | None = Field(default=None, min_length=1, max_length=255)
    search: str | None = Field(default=None, max_length=500)
    sort: str = Field(default="sid", max_length=100)
    page: int = Field(default=1, ge=1, le=1000000)
    page_size: int = Field(default=100, ge=1, le=1000)


class MeasurementParameters(StudyParameters):
    measurement_type: str | None = Field(default=None, min_length=1, max_length=255)
    tissue: str | None = Field(default=None, min_length=1, max_length=255)


def search(request: Request, query: QuerySpec):
    actor = request.app.state.principal(request, required=False)
    try:
        return request.app.state.queries.search(query, actor)
    except ValueError as error:
        # Query-service messages describe allowlisted fields/operators, never SQL.
        raise HTTPException(400, str(error)) from None


def simple_query(parameters: StudyParameters, entity: str) -> QuerySpec:
    fields = (
        {"study_sid": "sid", "substance": "substance_name"}
        if entity == "studies"
        else {
            "study_sid": "study_sid",
            "substance": "substance",
            "measurement_type": "measurement_type",
            "tissue": "tissue",
        }
    )
    return QuerySpec.model_validate(
        {
            "entity": entity,
            "predicates": [
                Predicate(field=field, value=value)
                for name, field in fields.items()
                if (value := getattr(parameters, name)) is not None
            ],
            "search": parameters.search,
            "sort": parameters.sort,
            "page": parameters.page,
            "page_size": parameters.page_size,
        }
    )


@router.get("/studies", response_model=DataPage[StudyResponse])
def list_studies(request: Request, parameters: Annotated[StudyParameters, Query()]):
    """Find visible studies. Substance matches a vocabulary name in the study.

    Use POST /query with measurements.* predicates to require multiple criteria
    on the same measurement. Visibility is applied before counting and paging.
    """
    query = simple_query(parameters, "studies")
    return DataPage[StudyResponse].from_page(search(request, query), query)


@router.get("/measurements", response_model=DataPage[OutputResponse])
def list_measurements(
    request: Request, parameters: Annotated[MeasurementParameters, Query()]
):
    """Find measurements by study and vocabulary SIDs, including normalized rows.

    All filters apply to the same measurement. Use POST /query for ranges,
    calculated/normed selection and other advanced predicates.
    """
    query = simple_query(parameters, "outputs")
    return DataPage[OutputResponse].from_page(search(request, query), query)


@router.post("/query", response_model=DataPage[ScientificRecord])
def query_data(query: DataQuery, request: Request):
    """Query scientific entities with allowlisted predicates and ordering.

    `measurements` aliases `outputs`. For study queries, `measurements.*`
    predicates must match the same measurement; they do not independently match
    unrelated measurements in a study. Pagination uses page numbers.
    """
    return DataPage[ScientificRecord].from_page(search(request, query), query)


@router.post(
    "/exports",
    response_model=None,
    responses={
        200: {
            "description": "ZIP archive of CSV tables and attribution terms",
            "content": {
                "application/x-zip-compressed": {
                    "schema": {"type": "string", "format": "binary"}
                }
            },
        }
    },
)
def export_data(spec: FilterSpec, request: Request):
    """Download a dataset selected by typed per-entity criteria.

    Requires authentication with read scope. Current study permissions are
    reapplied when building the archive. Criteria use the canonical entity name
    `outputs` for measurements. With concise=true, matching rows and their
    dependencies are exported; false expands to the selected studies.
    """
    actor = request.app.state.principal(request, required=True)
    try:
        identifier = request.app.state.exports.create_filter(spec, actor)
        return download_response(request.app.state.exports, identifier, actor)
    except ValueError as error:
        raise HTTPException(400, str(error)) from None


@router.get("/statistics", response_model=StatisticsOverview)
def statistics(request: Request) -> StatisticsOverview:
    """Current coverage and annual metrics using the study date field."""
    actor = request.app.state.principal(request, required=False)
    return request.app.state.queries.statistics_overview(actor)
