import json

import os
import sys

import requests
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient, RequestsClient
from django.core.exceptions import ObjectDoesNotExist

from pkdb_app.comments.models import Comment
from pkdb_app.data_management.setup_database import setup_database
from pkdb_app.data_management.upload_studies import upload_study_from_dir, read_reference_json, \
    upload_reference_json, upload_files

from pkdb_app.interventions.models import Substance
from pkdb_app.interventions.serializers import TimecourseSerializer
from pkdb_app.studies.models import Study
from pkdb_app.subjects.models import DataFile, Group
from pkdb_app.users.models import User

BASEPATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../")
)
sys.path.append(BASEPATH)


class AuthenticationAPITestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.api = reverse('user-list')
        self.password = "test"
    def test_api_token_auth(self):

        response = self.client.post("/api-token-auth/", data={"username": "admin", "password": self.password})
        assert json.loads(response.content) == {"non_field_errors":["Unable to log in with provided credentials."]} , json.loads(response.content)


    def test_create_superuser(self):
        User.objects.create_superuser(username="admin", password=self.password, email="")
        response = self.client.post("/api-token-auth/", data={"username": "admin", "password": self.password})

        assert response.status_code == 200, response.status_code
        assert "token" in json.loads(response.content) ,json.loads(response.content)


class UploadStudy(APITestCase):

    def setUp(self):
        self.client =  APIClient()
        self.password = "test"
        User.objects.create_superuser(username="admin", password=self.password, email="")
        response = self.client.post("/api-token-auth/", data={"username": "admin", "password": self.password})
        self.token = json.loads(response.content)["token"]
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token)
        self.header = {'Authorization': f'token {self.token}','Content-type': 'application/json'}
        self.api_url="/api/v1"


    def test_setup_database(self):
        setup_database(api_url=self.api_url, auth_headers=self.header, client=self.client)
        assert hasattr(Substance.objects.first(),"name")


    def test_upload_reference_json(self):
        study_name = "test_study"
        study_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), study_name)
        reference_path = os.path.join(study_dir, "reference.json")
        reference_pdf = os.path.join(study_dir, f"{study_name}.pdf")

        reference_dict = {"reference_path": reference_path, "pdf": reference_pdf}
        json_reference = read_reference_json(reference_dict)
        success = upload_reference_json(json_reference, api_url=self.api_url, auth_headers=self.header, client=self.client)
        assert success

    def test_upload_files(self):
        study_name = "test_study"
        study_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), study_name)
        upload_files(file_path=study_dir, api_url=self.api_url, auth_headers=self.header, client=self.client)
        assert hasattr(DataFile.objects.first(),"file"), DataFile.objects.first()

    def test_upload_study_from_dir(self):
        study_test_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)),"test_study")
        setup_database(api_url=self.api_url, auth_headers=self.header, client=self.client)
        upload_study_from_dir(study_dir=study_test_dir, auth_headers=self.header, api_url=self.api_url, client=self.client)
        assert  Study.objects.filter(name="test_study").count() == 1 ,Study.objects.filter(name="test_study")
        test_study = Study.objects.get(name="test_study")
        assert test_study.sid == '7589032'
        assert test_study.pkdb_version == 1
        assert test_study.creator.username == "mkoenig"
        assert test_study.name == "test_study"
        assert test_study.design is None
        assert test_study.reference.sid == '7589032'

        assert len(test_study.curators.all()) == 2
        for curator in test_study.curators.all():
            assert curator.username in ["mkoenig", "janekg"]

        assert len(test_study.substances.all()) == 1
        for substance in test_study.substances.all():
            assert substance.name in ["caffeine"]

        assert len(test_study.keywords.all()) == 0
        for keyword in test_study.keywords.all():
            assert keyword.name in []

        assert len(test_study.comments.all()) == 1
        for comment in test_study.comments.all():
            assert comment.user.username == "mkoenig"
            assert comment.text == "oral contraceptives"

        assert len(test_study.descriptions.all()) == 1
        for description in test_study.descriptions.all():
            assert description.text == ("The study was performed as an open group comparison " 
             "comprising five menstrual cycles")

        groupset = test_study.groupset

        assert len(groupset.descriptions.all()) == 4
        for description in groupset.descriptions.all():
            assert description.text in [
                ("Twenty healthy, young women, (ages 20-34 years), whose weight ranged from 51 to 75 kg, "
            "participated in the study. The women had not taken oral contraceptives at least 2 months prior " 
             "to their participation in the study"),
            "Excluded were smokers;",
                ("The subjects were randomly allocated to two groups A and B. Women of group A received the "
             "gestodene-containing formulation (0.075 mg gestodene + 0.03 mg EE2, Femovan, Schering, Berlin) "
              "and women of group B the levonorgestrel-containing formulation (0.125 mg levonorgestrel + 0.03 mg EE2, "
              "Minisiston, Jenapharm, Jena) once daily during a treatment cycle of 2l days, respectively"),
                ("All volunteers had been instructed to refrain for at least 36 h prior to and during the caffeine test "
            "from all methylxanthine-containing beverages and food. Intake of alcohol was also not allowed.")
            ]

        assert len(groupset.comments.all()) == 1
        for comment in groupset.comments.all():
            assert comment.user.username == "mkoenig"
            assert comment.text == ("Oral contraceptive treatment is encoded as patient characteristica "
            "(not as intervention). Post-treatment cycle (cycle V) is not significant different from pre-treatment "
            "cycles (cycle I-III), therefore handled as no oral contraceptive use.")

        groups = groupset.groups
        assert len(groups.all()) == 7
        group_all = get_or_assert(queryset=groups,name="all")
        assert group_all.count == 20
        groups_all_characteristica = group_all.characteristica
        def test_group_all_characteristica(characteristica):
            assert len(characteristica.all()) == 9
            get_or_assert(queryset=characteristica, category="species",choice="homo sapiens")
            get_or_assert(queryset=characteristica, category="abstinence",choice="alcohol")
            get_or_assert(queryset=characteristica, category="abstinence",choice="methylxanthine")
            get_or_assert(queryset=characteristica, category="abstinence",choice="caffeine")
            get_or_assert(queryset=characteristica, category="age",min=20,max=34,unit="yr")
            get_or_assert(queryset=characteristica, category="healthy",choice="Y")
            get_or_assert(queryset=characteristica, category="smoking",choice="N")
            get_or_assert(queryset=characteristica, category="weight",min=51,max=75,unit="kg")
            get_or_assert(queryset=characteristica, category="sex",choice="F")

        test_group_all_characteristica(groups_all_characteristica.filter(final=True))
        group_all_ex = group_all.ex
        assert group_all_ex.count == 20
        groups_all_ex_characteristica = group_all_ex.characteristica_ex
        test_group_all_characteristica(groups_all_ex_characteristica)

        group_A = get_or_assert(queryset=groups,name="A")
        assert group_A.parent == group_all
        group_A_oc = get_or_assert(queryset=groups,name="A_oc")
        assert group_A_oc.parent == group_A

        individualset = test_study.individualset

        assert len(individualset.descriptions.all()) == 0
        assert len(individualset.comments.all()) == 0

        individual_exs = individualset.individual_exs

        assert len(individual_exs.all()) == 2
        this_individual_ex = get_or_assert(queryset=individual_exs, name_map="col==subject", group_map="col==group",
                                            format="TSV")

        this_individual_ex2 = get_or_assert(queryset=individual_exs, name_map="col==subject",
                                            group_map="col==fake_group",
                                            format="TSV")

        assert "test_study_TabA.csv" in this_individual_ex.source.file.name

        individuals = individualset.individuals
        assert len(individuals.all()) == len(this_individual_ex.individuals.all()) +len(this_individual_ex2.individuals.all())
        assert set(individuals.all()) == set((this_individual_ex.individuals.all() | this_individual_ex2.individuals.all()))
        assert len(individuals.all()) == 60
        B_no_oc = get_or_assert(Group.objects, name="B_no_oc", ex__groupset__study=test_study)
        A_no_oc = get_or_assert(Group.objects, name="A_no_oc", ex__groupset__study=test_study)
        B_oc = get_or_assert(Group.objects, name="B_oc", ex__groupset__study=test_study)
        A_oc = get_or_assert(Group.objects, name="A_oc", ex__groupset__study=test_study)
        All_group = get_or_assert(Group.objects, name="all", ex__groupset__study=test_study)

        get_or_assert(queryset=individuals, name="1", group=B_no_oc,ex=this_individual_ex)
        get_or_assert(queryset=individuals, name="2", group=B_no_oc,ex=this_individual_ex)
        test_individual = get_or_assert(queryset=individuals, name="4", group=A_no_oc,ex=this_individual_ex)
        get_or_assert(queryset=individuals, name="5", group=A_no_oc,ex=this_individual_ex)
        get_or_assert(queryset=individuals, name="1_oc", group=B_oc,ex=this_individual_ex)
        get_or_assert(queryset=individuals, name="2_oc", group=B_oc,ex=this_individual_ex)
        get_or_assert(queryset=individuals, name="4_oc", group=A_oc,ex=this_individual_ex)
        get_or_assert(queryset=individuals, name="5_oc", group=A_oc,ex=this_individual_ex)



        individual_1C = get_or_assert(queryset=individuals, name="1C", group=All_group,ex=this_individual_ex2)
        individual_10M = get_or_assert(queryset=individuals, name="10M", group=All_group,ex=this_individual_ex2)

        assert set(individual_1C.characteristica.all()) > set(individual_1C.characteristica_final)
        assert set(individual_10M.characteristica.all()) > set(individual_10M.characteristica_final)
        not_norm_characteristca = get_or_assert(individual_10M.characteristica, final=False, category="weight")
        assert not_norm_characteristca.unit == "g"
        assert not_norm_characteristca.norm.first().unit == not_norm_characteristca.norm_unit



        interventionset = test_study.interventionset

        assert len(interventionset.descriptions.all()) == 3
        for description in interventionset.descriptions.all():
            assert description.text in [
                ("The drug (200 mg caffeine as uncoated tablet, Berlin Chemie, Germany) "
                 "was administered in the morning after an overnight fast, together with "
                 "200 ml herbal tea. On day 21 of the treatment cycle, caffeine was administered "
                 "30min after the intake of the oral contraceptive. All volunteers had been instructed "
                 "to refrain for at least 36 h prior to and during the caffeine test "
                 "from all methylxanthine-containing beverages and food."),
                ("The subjects were randomly allocated to two groups A and B. "
                 "Women of group A received the gestodene-containing formulation (0.075 mg gestodene + 0.03 mg EE2, "
                 "Femovan, Schering, Berlin) and women of group B the levonorgestrel-containing formulation "
                 "(0.125 mg levonorgestrel + 0.03 mg EE2, Minisiston, Jenapharm, Jena) once daily during a treatment "
                 "cycle of 2l days, respectively"),
                ("The study was performed as an open group comparison comprising five menstrual cycles: three control "
                 "cycles (cycles I-III), one treatment cycle (cycle IV) and one post-treatment cycle (cycle V). "
                 "The subjects were randomly allocated to two groups A and B. Women of group "
                 "A received the gestodene-containing formulation (0.075 mg gestodene + 0.03 mg EE2, "
                 "Femovan, Schering, Berlin) and women of group B the levonorgestrel-containing formulation "
                 "(0.125 mg levonorgestrel + 0.03 mg EE2, Minisiston, Jenapharm, Jena) once daily during a treatment "
                 "cycle of 2l days, respectively. The oral contraceptive was administered in the morning.")
            ]

        assert len(interventionset.comments.all()) == 1
        for comment in interventionset.comments.all():
            assert comment.user.username == "mkoenig"
            assert comment.text == ("Interventions DA, DB, DEE2 removed from outputs. "
                "The oral contraceptives are encoded via the group characteristica.")

        intervention_exs = interventionset.intervention_exs
        assert len(intervention_exs.all()) == 4
        gestodene = get_or_assert(Substance.objects, name="gestodene")

        da_intervention_ex = get_or_assert(queryset = intervention_exs,
                      name = "DA",
                      substance = gestodene,
                      route = "oral",
                      value= 0.075,
                      unit = "mg",
                      category = "dosing",
                      )

        assert len(da_intervention_ex.comments.all()) == 1

        mkoenig = get_or_assert(User.objects, username="mkoenig")
        comment = get_or_assert(Comment.objects, text="0.075 mg gestodene + 0.03 mg EE2", user=mkoenig)
        assert comment.intervention_ex == da_intervention_ex

        interventions = interventionset.interventions
        assert len(interventions.filter(final=True)) == 4
        da_intervention = get_or_assert(queryset=interventions,
                                        name="DA",
                                        substance=gestodene,
                                        route="oral",
                                        value=0.075,
                                        unit="mg",
                                        category="dosing",
                                        final=True
                                        )
        dcaf_intervention = get_or_assert(queryset=interventions,
                                        name="Dcaf",
                                        final=True
                                        )

        assert da_intervention.ex == da_intervention_ex

        outputset = test_study.outputset

        assert len(outputset.descriptions.all()) == 2
        for description in outputset.descriptions.all():
            assert description.text in [
                ("Blood samples were collected at the following time points: "
                 "immediately prior to caffeine intake (0 h) and 0.5, 1, 1.5, 2, 4, 6, 8, 10, 12 "
                 "and 24 h after administration."),
                ("The serum concentrations of caffeine, which were obtained after single oral administrations "
                 "on day 21 of the pretreatment, treatment and post-treatment cycles, were evaluated using a one "
                 "compartment model assuming complete bioavailability (TOPFIT 2.0, Goedecke, Schering, "
                 "Thomae GmbH, FRG). The elimination halflife (t~) of caffeine was determined by regression analysis "
                 "from the linear terminal part of the semilogarithrnic presentation of the caffeine "
                 "concentration-time curve. The volume of distribution (V~) was calculated according to: "
                 "Vc = D/C0 where D is the dose of caffeine administered and C0 is the serum concentration "
                 "obtained from extrapolation to time zero. Total clearance (CL) was calculated according to: "
                 "CL = ln 2 x Vc/thalf.")
            ]

        assert len(outputset.comments.all()) == 0

        output_exs = outputset.output_exs
        assert len(output_exs.all()) == 4

        caffeine = get_or_assert(Substance.objects, name="caffeine")

        output_exs_individual = get_or_assert(queryset=output_exs,
                      subset_map="intgroup==NO_OC || intgroup==A || intgroup==B",
                      format="TSV",
                      individual_map="col==subject",
                      interventions_map="Dcaf,DB || Dcaf || Dcaf",
                      substance=caffeine,
                      pktype="clearance",
                      value_map="col==cl",
                      tissue="plasma",
                      unit="ml/min"
                      )

        assert "test_study_Tab1.png" in output_exs_individual.figure.file.name
        assert "test_study_Tab1.csv" in output_exs_individual.source.file.name

        assert len(output_exs_individual.outputs.all()) == 200
        outputs_individual = get_or_assert(queryset=output_exs_individual.outputs,
                                              substance=caffeine,
                                              pktype="clearance",
                                              value=39.8,
                                              tissue="plasma",
                                              unit="ml/min"
                                              )

        outputs_individual_norm = get_or_assert(queryset=output_exs_individual.outputs,
                                                substance=caffeine,
                                                pktype="clearance",
                                                tissue="plasma",
                                                raw=outputs_individual,
                                                final=True
                                                )



        assert outputs_individual.individual == test_individual
        assert outputs_individual_norm.individual == test_individual
        assert outputs_individual.final == False

        assert len(outputs_individual.interventions.all()) == 2
        assert dcaf_intervention in outputs_individual.interventions.all()
        assert len(outputs_individual_norm.interventions.all()) == 2
        assert dcaf_intervention in outputs_individual_norm.interventions.all()


        assert outputs_individual_norm in outputset.outputs_final.all()
        assert outputs_individual.norm_unit == outputs_individual_norm.unit




        this_output_ex_group = get_or_assert(queryset=output_exs,
                                              subset_map="intgroup==NO_OC",
                                              format="TSV",
                                              group_map="col==group",
                                              substance=caffeine,
                                              pktype_map="clearance || cmax || tmax || thalf || vd",
                                              mean_map="col==cl || col==cmax || col==tmax || col==thalf || col==vd",
                                              sd_map="col==cl_sd || col==cmax_sd || col==tmax_sd || col==thalf_sd || col==vd_sd",
                                              tissue="plasma",
                                              unit_map= "ml/min || µg/ml || h || h || l"
                                              )



        assert "test_study_Tab2.png" in this_output_ex_group.figure.file.name
        assert "test_study_Tab2.csv" in this_output_ex_group.source.file.name
        assert len(this_output_ex_group.interventions.all()) == 1
        assert dcaf_intervention in this_output_ex_group.interventions.all()




        this_output_group = get_or_assert(queryset=this_output_ex_group.outputs,
                                           substance=caffeine,
                                           pktype="clearance",
                                           mean=87.6,
                                           tissue="plasma",
                                           unit="ml/min"
                                           )
        this_output_group_norm = get_or_assert(queryset=this_output_ex_group.outputs,
                                                  substance=caffeine,
                                                  pktype="clearance",
                                                  tissue="plasma",
                                                  raw=this_output_group,
                                                  final=True
                                                  )
        assert this_output_group_norm.raw == this_output_group


        assert this_output_group.ex == this_output_ex_group
        assert this_output_group.final == False

        assert len(this_output_group_norm.interventions.all()) == 1
        assert dcaf_intervention in this_output_group_norm.interventions.all()

        assert this_output_group_norm in outputset.outputs_final.all()
        assert this_output_group.norm_unit == this_output_group_norm.unit
        assert this_output_group.se is None
        assert this_output_group.cv is None
        assert this_output_group_norm.se is not None
        assert this_output_group_norm.cv is not None


        outputs = outputset.outputs
        outputs_final = outputset.outputs_final

        assert len(outputs.all()) == 300
        assert len(outputs_final.all()) == 150

        outputs_final.first()

        timecourses = outputset.timecourses
        timecourse_exs = outputset.timecourse_exs
        timecourses_final = outputset.timecourses_final


        assert len(timecourse_exs.all()) == 2
        assert len(timecourses.all()) == 18
        assert len(timecourses.filter(final=False)) == 9
        timecourse_notnorm = get_or_assert(timecourses.filter(final=False),individual=individual_1C,substance=caffeine)
        timecourse_norm = get_or_assert(timecourses.filter(final=True),individual=individual_1C,substance=caffeine)
        assert timecourse_norm.raw == timecourse_notnorm
        assert timecourse_notnorm.unit == "µg/ml"
        assert timecourse_norm.unit == "µg/ml"
        assert timecourse_norm in timecourses_final.all()

        timecourse_notnorm_group = get_or_assert(timecourses.filter(final=False),group=All_group,substance=caffeine)
        timecourse_norm_group = get_or_assert(timecourses.filter(final=True),group=All_group,substance=caffeine)


        assert timecourse_notnorm_group.se is None
        assert timecourse_notnorm_group.cv is None
        assert timecourse_norm_group.se is not None
        assert timecourse_norm_group.cv is not None

        assert timecourse_norm_group in timecourses_final.all()
        assert len(timecourses_final.all()) == 9







def get_or_assert(queryset, **kwargs):
    try:
        return queryset.get(**kwargs)

    except ObjectDoesNotExist:
        assert False , f"DoesNotExist with kwargs: {kwargs} "

