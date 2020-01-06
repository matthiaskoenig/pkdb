from django.http import Http404
from django_elasticsearch_dsl_drf.filter_backends import CompoundSearchFilterBackend, \
    FilteringFilterBackend, OrderingFilterBackend, IdsFilterBackend, MultiMatchSearchFilterBackend
from django_elasticsearch_dsl_drf.utils import DictionaryProxy
from django_elasticsearch_dsl_drf.viewsets import DocumentViewSet, BaseDocumentViewSet

from pkdb_app.outputs.documents import OutputDocument, TimecourseDocument, TimecourseInterventionDocument, \
    OutputInterventionDocument
from pkdb_app.outputs.models import TimecourseIntervention, OutputIntervention
from pkdb_app.subjects.models import GroupCharacteristica, IndividualCharacteristica
from pkdb_app.users.models import PUBLIC
from pkdb_app.users.permissions import IsAdminOrCreatorOrCurator, StudyPermission, user_group
from rest_framework.exceptions import ValidationError
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from elasticsearch import helpers
from pkdb_app.interventions.documents import InterventionDocument
from pkdb_app.pagination import CustomPagination
from pkdb_app.studies.documents import ReferenceDocument, StudyDocument
from pkdb_app.subjects.documents import GroupDocument, IndividualDocument, CharacteristicaDocument, \
    GroupCharacteristicaDocument, IndividualCharacteristicaDocument

from .models import Reference, Study
from .serializers import (
    ReferenceSerializer,
    StudySerializer,
    ReferenceElasticSerializer,
    StudyElasticSerializer)
from rest_framework import viewsets
import django_filters.rest_framework
from rest_framework import filters
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q as DQ

from elasticsearch_dsl.query import Q


class ReferencesViewSet(viewsets.ModelViewSet):
    """ ReferenceViewSet """
    queryset = Reference.objects.all()
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    serializer_class = ReferenceSerializer
    lookup_field = "sid"
    filter_backends = (
        django_filters.rest_framework.DjangoFilterBackend,
        filters.SearchFilter,
    )
    filter_fields = ("sid",)
    # filter_fields = ( 'pmid', 'doi','title', 'abstract', 'journal','date', 'authors')
    search_fields = filter_fields
    permission_classes = (IsAdminOrCreatorOrCurator,)


class StudyViewSet(viewsets.ModelViewSet):
    """ StudyViewSet """
    queryset = Study.objects.all()
    serializer_class = StudySerializer
    filter_backends = (
        django_filters.rest_framework.DjangoFilterBackend,
        filters.SearchFilter,
    )
    filter_fields = ("sid",)
    search_fields = filter_fields
    lookup_field = "sid"
    permission_classes = (StudyPermission,)

    def get_queryset(self):
        queryset = super().get_queryset()
        group = user_group(self.request.user)
        if group in ["admin", "reviewer"]:
            return queryset

        elif group == "basic":

            return queryset.filter(DQ(access=PUBLIC) |
                                   DQ(creator=self.request.user) |
                                   DQ(collaborators=self.request.user) |
                                   DQ(curators=self.request.user)).distinct()

        elif group == "anonymous":
            return queryset.filter(access=PUBLIC)

    @staticmethod
    def group_validation(request):
        if "groupset" in request.data and request.data["groupset"]:
            groupset = request.data["groupset"]
            if "groups" in groupset:
                groups = groupset.get("groups", [])
                if not isinstance(groups, list):
                    raise ValidationError(
                        {"groups": f"groups must be a list and not a {type(groups)}", "detail": groups})

                parents_name = set()
                groups_name = set()

                for group in groups:
                    parent_name = group.get("parent")
                    if parent_name:
                        parents_name.add(parent_name)
                    group_name = group.get("name")
                    if group_name:
                        groups_name.add(group_name)
                    if group_name == "all" and parent_name is not None:
                        raise ValidationError({"groups": "parent is not allowed for group all"})

                    elif group_name != "all" and parent_name is None:
                        raise ValidationError(
                            {
                                "groups": f"'parent' field missing on group '{group_name}'. "
                                          f"For all groups the parent group must be specified via "
                                          f"the 'parent' field (with exception of the <all> group)."
                             })

                if "all" not in groups_name:
                    raise ValidationError(
                        {
                            "group":
                             "A group with the name `all` is missing (studies without such a group cannot be uploaded). "
                             "The `all` group is the group of all subjects which was studied and defines common "
                             "characteristica for all groups and individuals. Species information are requirement "
                             "on the all group. Create the `all` group or rename group to `all`. "
                         }
                    )

                # validate if groups are missing
                missing_groups = parents_name - groups_name
                if missing_groups:
                    msg = {
                        "groups": f"The groups <{missing_groups}> have been used but not defined."
                    }
                    raise ValidationError(msg)

    def partial_update(self, request, *args, **kwargs):
        self.group_validation(request)
        return super().partial_update(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        self.group_validation(request)
        return super().update(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        self.group_validation(request)
        return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):

        # if get object does not find  an object it stops here

        instance = self.get_object()

        related_elastic = related_elastic_dict(instance)
        delete_elastic_study(related_elastic)
        return super().destroy(request, *args, **kwargs)


###############################################################################################
# Elastic ViewSets
###############################################################################################

@csrf_exempt
def update_index_study(request):
    if request.method == 'POST':
        data = JSONParser().parse(request)
        try:
            study = Study.objects.get(sid=data["sid"])
        except ObjectDoesNotExist:
            return JsonResponse({"success": "False", "reason": "Instance not in database"})

        related_elastic = related_elastic_dict(study)
        for doc, instances in related_elastic.items():
            try:
                action = data.get('action', 'index')
                doc().update(thing=instances, action=action)
            except helpers.BulkIndexError:
                raise helpers.BulkIndexError

        return JsonResponse({"success": "True"})


def delete_elastic_study(related_elastic):
    for doc, instances in related_elastic.items():
        try:
            doc().update(thing=instances, action="delete")
        except helpers.BulkIndexError:
            return False, "BulkIndexError"



def related_elastic_dict(study):
    """ Dictionary of elastic documents for given study.

    :param study:
    :return:
    """
    interventions = study.interventions.all()
    groups = study.groups.all()
    individuals = study.individuals.all()
    outputs = study.outputs.all()
    timecourses = study.timecourses.all()
    docs_dict = {
        StudyDocument: study,
        GroupDocument: groups,
        IndividualDocument: individuals,
        CharacteristicaDocument: study.characteristica,
        GroupCharacteristicaDocument: GroupCharacteristica.objects.filter(group__in=groups),
        IndividualCharacteristicaDocument: IndividualCharacteristica.objects.filter(individual__in=individuals),
        TimecourseInterventionDocument: TimecourseIntervention.objects.filter(timecourse__in=timecourses),
        OutputInterventionDocument: OutputIntervention.objects.filter(output__in=outputs),
        InterventionDocument: interventions,
        OutputDocument: study.outputs,
        TimecourseDocument: study.timecourses,

    }
    if study.reference:
        docs_dict[ReferenceDocument] = study.reference
    return docs_dict


class ElasticStudyViewSet(BaseDocumentViewSet):
    document_uid_field = "sid__raw"
    lookup_field = "sid"
    document = StudyDocument
    pagination_class = CustomPagination
    serializer_class = StudyElasticSerializer
    filter_backends = [FilteringFilterBackend, IdsFilterBackend, OrderingFilterBackend, MultiMatchSearchFilterBackend]
    permission_classes = (StudyPermission,)
    search_fields = (
        'sid',
        'pk_version',
        'creator.first_name',
        'creator.last_name',
        'creator.user',

        'curators.first_name',
        'curators.last_name',
        'curators.user',

        'name',
        'reference',
        'substances',
        'files',
    )
    multi_match_search_fields = {field: {"boost": 1} for field in search_fields}
    multi_match_options = {
        'operator': 'and'
    }

    filter_fields = {
        'sid': 'sid.raw',
        'name': 'name.raw',
        'licence': 'licence.raw',
        'access': 'access.raw',
        'substances': 'substances.raw',
    }
    ordering_fields = {
        'sid': 'sid',
    }


    def get_queryset(self):
        search = self.search
        group = user_group(self.request.user)

        if group in ["admin", "reviewer"]:
            return search.query()

        elif group == "basic":

            qs = search.query(
                Q('match', access__raw=PUBLIC) |
                Q('match', creator__username__raw=self.request.user.username) |
                Q('match', curators__username__raw=self.request.user.username) |
                Q('match', collaborators__username__raw=self.request.user.username)

            )

            return qs

        elif group == "anonymous":

            qs = search.query(
                'match',
                **{"access__raw": PUBLIC}
            )

            return qs


class ElasticReferenceViewSet(BaseDocumentViewSet):
    """Read/query/search references. """
    document_uid_field = "sid__raw"
    lookup_field = "sid"
    document = ReferenceDocument
    pagination_class = CustomPagination
    permission_classes = (IsAdminOrCreatorOrCurator,)
    serializer_class = ReferenceElasticSerializer
    filter_backends = [FilteringFilterBackend, IdsFilterBackend, OrderingFilterBackend, MultiMatchSearchFilterBackend]
    search_fields = ('sid', 'study_name', 'study_pk', 'pmid', 'title', 'abstract', 'name', 'journal')
    multi_match_search_fields = {field: {"boost": 1} for field in search_fields}
    multi_match_options = {
        'operator': 'and'
    }
    filter_fields = {'name': 'name.raw', }
    ordering_fields = {
        'sid': 'sid',
        "pk": 'pk',
        "study_name": "study_name",
        "study_pk": "study_pk",
        "pmid": "pmid",
        "name": "name",
        "doi": "doi",
        "title": "title.raw",
        "abstract": "abstract.raw",
        "journal": "journal.raw",
        "date": "date",
        "pdf": "pdf",
        "authors": "authors.last_name",
    }
