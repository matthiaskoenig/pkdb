"""Definition of symptoms, diseases and health status.

Disease definitions should be based on the disease-ontology DOID.
Secondary resource is the NCIT.
"""

from pymetadata.core.miriam import BQB

from ..node import Choice, DType, InfoNode, MeasurementType
from ..units import NO_UNIT

DISEASE_NODES: list[InfoNode] = [
    MeasurementType(
        sid="health-status",
        name="health status",
        description="Health status. The state of a subject's mental or physical condition.",
        parents=["measurement"],
        dtype=DType.ABSTRACT,
        annotations=[
            (BQB.IS, "NCIT:C16669"),
            (BQB.IS, "https://bioregistry.io/OPMI:0000281"),
            (BQB.IS, "hp/HP:0032319"),
        ],
    ),
    MeasurementType(
        sid="healthy",
        description="Individual or subjects are described as healthy. If "
        "subjects are not healthy the disease or impairment "
        "should be described by a combination of 'disease', "
        "'disease severity' and 'disease duration'. "
        "If abnormal blood biochemistry "
        "is reported code the respective biochemistry.",
        parents=["health status"],
        dtype=DType.BOOLEAN,
        annotations=[
            (BQB.IS, "NCIT:C115935"),
        ],
    ),
    # --- Symptoms -------------------------------------------------------------------------------
    MeasurementType(
        sid="symptom",
        name="symptom",
        description="Symptom of a disease. A symptom is a perceived change in function, "
        "sensation, loss, disturbance or appearance reported by a patient indicative "
        "of a disease. Symptom of individual or subjects is encoded by 'choice' "
        "field. Symptom duration of individual or subjects (duration should be "
        "provided via the min/mean numerical fields in combination with unit).",
        dtype=DType.NUMERIC_CATEGORICAL,
        units=["year", NO_UNIT],
        annotations=[
            ## (BQB.IS, "symp/SYMP:0000462"),
        ],
        synonyms=[],
        parents=["health status"],
    ),
    Choice(
        sid="oedem",
        description="An accumulation of an excessive amount of watery fluid in cells or intercellular tissues.",
        parents=["symptom"],
        annotations=[
            ## (BQB.IS, "symp/SYMP:0000538"),
            (BQB.IS, "efo/0009373"),
        ],
        synonyms=["edema", "oedema"],
    ),
    Choice(
        sid="liver-oedem",
        name="liver oedem",
        description="Liver oedem",
        parents=["oedem"],
        annotations=[
            # (BQB.IS_VERSION_OF, "symp/SYMP:0000538"),
            (BQB.IS_VERSION_OF, "efo/0009373"),
        ],
    ),
    Choice(
        sid="ascites",
        description="Ascites. An abdominal symptom consisting of an abnormal accumulation of "
        "serous fluid in the spaces between tissues and organs in the cavity of the "
        "abdomen. The accumulation of fluid in the peritoneal cavity, which may be "
        "serous, hemorrhagic, or the result of tumor metastasis to the peritoneum.",
        parents=["symptom"],
        annotations=[
            ## (BQB.IS, "symp/SYMP:0000526"),
        ],
    ),
    Choice(
        sid="jaundice",
        description="A skin and integumentary tissue symptom that is characterized by a yellowish "
        "pigmentation of the skin, tissues, and certain body fluids is caused by the "
        "deposition of bile pigments that follows interference with normal production "
        "and discharge of bile (as in certain liver diseases) or excessive breakdown "
        "of red blood cells (as after internal hemorrhage or in various hemolytic "
        "states).",
        parents=["symptom"],
        annotations=[
            ## (BQB.IS, "symp/SYMP:0000539"),
        ],
    ),
    Choice(
        sid="stasis",
        description="Stasis. Cessation of movement of a body fluid or liquid.",
        parents=["symptom"],
        annotations=[],
    ),
    Choice(
        sid="biliary-stasis",
        name="biliary stasis",
        description="Biliary stasis. Cessation of the flow of bile due to bile duct "
        "blockage or overproduction.",
        parents=["stasis"],
        annotations=[],
        synonyms=["intrahepatic billiary stasis"],
    ),
    Choice(
        sid="liver-stasis",
        name="liver stasis",
        description="Liver stasis. Cessation of the hepatic blood flow",
        parents=["stasis"],
        annotations=[],
        synonyms=[],
    ),
    Choice(
        sid="shock",
        name="shock",
        description="Shock. Shock is the state of insufficient blood flow to the "
        "tissues of the body as a result of problems with the circulatory "
        "system. A life-threatening condition that requires immediate "
        "medical intervention. It is characterized by reduced blood flow "
        "that may result in damage of multiple organs. Types of shock "
        "include cardiogenic, hemorrhagic, septic, anaphylactic, "
        "and traumatic shock.",
        parents=["symptom"],
        annotations=[
            ## (BQB.IS, "symp/SYMP:0000450"),
        ],
        synonyms=[],
    ),
    Choice(
        sid="macroalbuminuria",
        name="macroalbuminuria",
        description="An abnormal albumin excretion rate of more than 300 mg/g urine creatinine.",
        parents=["symptom"],
        synonyms=[],
        annotations=[(BQB.IS, "https://bioregistry.io/SCDO:10002014")],
    ),
    # --- Diseases -------------------------------------------------------------------------------
    MeasurementType(
        sid="disease",
        description="A disease is a disposition (i) to undergo pathological processes "
        "that (ii) exists in an organism because of one or more disorders in that organism. "
        "Disease of individual or subjects with disease encoded by 'choice' "
        "field. Disease duration of individual "
        "or subjects (duration should be provided via the min/mean numerical "
        "fields in combination with unit). To encode the family history for "
        "disease use 'family history disease'.",
        parents=["health status"],
        dtype=DType.NUMERIC_CATEGORICAL,
        units=["year", NO_UNIT],
        annotations=[
            (BQB.IS, "doid/DOID:4"),
            (BQB.IS_VERSION_OF, "NCIT:C2991"),
            (BQB.IS, "efo/0000408"),
        ],
    ),
    Choice(
        sid="genetic-disease",
        name="genetic disease",
        description="A disease that has_material_basis_in genetic variations in the human genome. "
        "Genetic diseases are diseases in which inherited genes predispose to "
        "increased risk.",
        annotations=[
            (BQB.IS, "doid/DOID:630"),
            (BQB.IS, "NCIT:C3101"),
        ],
        synonyms=["genetic disorder"],
        parents=["disease"],
    ),
    # --- disease of metabolism
    Choice(
        sid="disease-of-metabolism",
        name="disease of metabolism",
        description="A disease that involves errors in metabolic processes of building or "
        "degradation of molecules.",
        annotations=[
            (BQB.IS, "doid/DOID:0014667"),
            (BQB.IS, "NCIT:C3235"),
        ],
        synonyms=["metabolic disorder"],
        parents=["disease"],
    ),
    Choice(
        sid="hypercholesterolemia",
        description="A laboratory test result indicating an increased amount of"
        "cholesterol in the blood; Abnormally high level of cholesterol"
        "in the blood. See also 'FH', 'homozygote FH' and 'heterozygote FH'",
        parents=["disease-of-metabolism"],
        annotations=[
            (BQB.IS, "NCIT:C37967"),
            (BQB.IS, "efo/0003124"),
        ],
    ),
    Choice(
        sid="mixed-hypercholesterolemia",
        name="mixed hypercholesterolemia",
        description="A type of hypercholesterolemia with elevated LDL-C and triglyceride plasma levels.",
        parents=["hypercholesterolemia"],
        annotations=[],
        synonyms=["combined hypercholesterolemia"],
    ),
    Choice(
        sid="familial-hypercholesterolemia",
        name="FH",
        label="familial hypercholesterolemia (FH)",
        description="A familial hyperlipidemia characterized by very high levels of "
        "low-density lipoprotein (LDL) and early cardiovascular disease.",
        parents=["hypercholesterolemia"],
        annotations=[(BQB.IS, "doid/DOID:13810"), (BQB.IS, "efo/0004911")],
    ),
    Choice(
        sid="homozygous-familial-hypercholesterolemia",
        name="homozygous FH",
        label="homozygous familial hypercholesterolemia (FH)",
        description=" A familial hypercholesterolemia that is characterized by very "
        "high levels of low-density lipoprotein (LDL) cholesterol "
        "(usually above 400 mg/dl) and increased risk of premature "
        "atherosclerotic cardiovascular disease, and has_material_basis_in "
        "autosomal recessive homozygous mutation in the low density "
        "lipoprotein receptor adaptor protein 1 gene (LDLRAP1) "
        "on chromosome 1p36. "
        "See also 'heterozygous FH'.",
        parents=["familial hypercholesterolemia"],
        synonyms=["autosomal recessive hypercholesterolemia"],
        annotations=[
            (BQB.IS, "doid/DOID:0090105"),
        ],
    ),
    Choice(
        sid="heterozygous-familial-hypercholesterolemia",
        name="heterozygous FH",
        label="heterozygous familial hypercholesterolemia (FH)",
        description="An autosomal dominant condition caused by mutation(s) in the "
        "APOB gene, encoding apolipoprotein B-100. It is characterized by "
        "hypercholesterolemia and abnormal low-density lipoproteins. "
        "See also 'homozygous FH'.",
        parents=["familial hypercholesterolemia"],
        synonyms=["autosomal dominant hypercholesterolemia"],
        annotations=[
            (BQB.IS, "NCIT:C176014"),
        ],
    ),
    # --- disease of cellular proliferation
    Choice(
        sid="disease-of-cellular-proliferation",
        name="disease of cellular proliferation",
        description="A disease that is characterized by abnormally rapid cell division.",
        parents=["disease"],
        annotations=[
            (BQB.IS, "doid/DOID:14566"),
        ],
    ),
    Choice(
        sid="cancer",
        description="A disease of cellular proliferation that is malignant and primary, "
        "characterized by uncontrolled cellular proliferation, local cell invasion "
        "and metastasis.",
        parents=["disease-of-cellular-proliferation"],
        annotations=[
            (BQB.IS, "doid/DOID:162"),
            (BQB.IS_VERSION_OF, "NCIT:C9305"),
            (BQB.IS, "efo/0000311"),
        ],
    ),
    Choice(
        sid="hematologic-cancer",
        label="hematologic cancer",
        description="An organ system cancer located in the hematological system that is "
        "characterized by uncontrolled cellular proliferation in blood, bone marrow "
        "and lymph nodes.",
        parents=["cancer"],
        annotations=[
            (BQB.IS, "doid/DOID:2531"),
        ],
        synonyms=["blood cancer", "hematologic malignancy"],
    ),
    Choice(
        sid="leukaemia",
        label="leukemia",
        description="A cancer that affects the blood or bone marrow characterized by an abnormal "
        "proliferation of blood cells.",
        parents=["cancer"],
        annotations=[
            (BQB.IS, "doid/DOID:1240"),
            (BQB.IS, "NCIT:C3161"),
            (BQB.IS, "omit/0009028"),
        ],
        synonyms=["leukemia", "leukaemia"],
    ),
    Choice(
        sid="myeloid leukemia",
        name="myeloid leukemia",
        description="A leukemia that is located_in myeloid tissue.",
        parents=["leukaemia"],
        annotations=[
            (BQB.IS, "doid/DOID:8692"),
        ],
    ),
    Choice(
        sid="chronic-myelogenous-leukemia",
        name="chronic myelogenous leukemia, BCR-ABL1 positive",
        description="A chronic myeloid leukemia that is characterized by an abnormally high number "
        "of neutrophils and the expression of the BCR-ABL1 fusion gene. A chronic "
        "myeloproliferative neoplasm characterized by the expression of the BCR-ABL1 "
        "fusion gene. It presents with neutrophilic leukocytosis. It can appear "
        "at any age, but it mostly affects middle aged and older individuals.",
        parents=["myeloid leukemia"],
        annotations=[
            (BQB.IS, "doid/DOID:0081088"),
        ],
    ),
    # --- hematopoietic system disease ---
    Choice(
        sid="hematopoietic-system-disease",
        name="hematopoietic system disease",
        description="A disease of anatomical entity that has_material_basis_in hematopoietic "
        "cells.",
        parents=["disease"],
        annotations=[
            (BQB.IS, "doid/DOID:74"),
        ],
    ),
    Choice(
        sid="sickle-cell-disease",
        name="sickle cell disease",
        description="A blood disorder characterized by the appearance of sickle-shaped red blood "
        "cells and anemia.",
        parents=["hematopoietic-system-disease"],
        annotations=[(BQB.IS, "doid/DOID:0081445"), (BQB.IS, "NCIT:C34383")],
    ),
    # --- endocrine system disease ---
    Choice(
        sid="endocrine-system-disease",
        name="endocrine system disease",
        description="A disease of anatomical entity that is located_in endocrine glands "
        "which secretes a type of hormone directly into the bloodstream to "
        "regulate the body.",
        parents=["disease"],
        annotations=[(BQB.IS, "doid/DOID:28")],
    ),
    Choice(
        sid="pancreatic-disease",
        name="pancreatic disease",
        description="Pancreatic disease. A non-neoplastic or neoplastic disorder "
        "that affects the pancreas. Representative examples of "
        "non-neoplastic disorders include pancreatitis and "
        "pancreatic insufficiency. Representative examples of "
        "neoplastic disorders include cystadenomas, carcinomas, "
        "lymphomas, and neuroendocrine neoplasms.",
        parents=["endocrine-system-disease"],
        annotations=[
            (BQB.IS, "doid/DOID:26"),
            (BQB.IS, "efo/0009605"),
        ],
        synonyms=["pancreas disease"],
    ),
    Choice(
        sid="pancreatitis",
        name="pancreatitis",
        description="A pancreas disease that is characterized by inflammation of the pancreas.",
        parents=["pancreatic-disease"],
        annotations=[
            (BQB.IS, "doid/DOID:4989"),
            (BQB.IS, "NCIT:C3306"),
        ],
    ),
    Choice(
        sid="chronic-pancreatitis",
        name="chronic pancreatitis",
        description="Long-standing inflammation of the pancreas.",
        parents=["pancreatitis"],
        annotations=[(BQB.IS, "efo/0000342"), (BQB.IS, "NCIT:C84637")],
    ),
    Choice(
        sid="gilbert-syndrome",
        name="Gilbert syndrome",
        description="A bilirubin metabolic disorder that involves elevated levels of unconjugated "
        "bilirubin as bilirubin is not being conjugated as a result of reduced "
        "glucuronyltransferase activity. An autosomal recessive inherited disorder "
        "characterized by unconjugated hyperbilirubinemia, resulting in harmless "
        "intermittent jaundice.",
        parents=["genetic-disease", "disease-of-metabolism"],
        annotations=[
            (BQB.IS, "doid/DOID:2739"),
            (BQB.IS, "NCIT:C84729"),
        ],
    ),
    Choice(
        sid="thyroid-disease",
        name="thyroid gland disease",
        description="Thyroid disease. A disease involving the thyroid gland. A "
        "non-neoplastic or neoplastic disorder that affects the thyroid "
        "gland. Representative examples include hyperthyroidism, "
        "hypothyroidism, thyroiditis, follicular adenoma, and carcinoma.",
        parents=["endocrine system disease"],
        annotations=[
            (BQB.IS, "doid/DOID:50"),
            (BQB.IS, "NCIT:C26893"),
            (BQB.IS, "efo/1000627"),
        ],
        synonyms=["Thyroiditis", "thyroid gland disorders"],
    ),
    Choice(
        sid="hyperthyroidism",
        description="Overactivity of the thyroid gland resulting in overproduction of "
        "thyroid hormone and increased metabolic rate. Causes include "
        "diffuse hyperplasia of the thyroid gland (Graves disease), "
        "single nodule in the thyroid gland, and thyroiditis. The symptoms "
        "are related to the increased metabolic rate and include weight "
        "loss, fatigue, heat intolerance, excessive sweating, diarrhea, "
        "tachycardia, insomnia, muscle weakness, and tremor.",
        parents=["thyroid-disease"],
        annotations=[
            (BQB.IS, "doid/DOID:7998"),
            (BQB.IS, "NCIT:C3123"),
        ],
    ),
    Choice(
        sid="hypothyroidism",
        description="A thyroid gland disease which involves an underproduction of thyroid hormone. "
        "Abnormally low levels of thyroid hormone.",
        parents=["thyroid-disease"],
        annotations=[
            (BQB.IS, "doid/DOID:1459"),
            (BQB.IS, "NCIT:C26800"),
        ],
    ),
    # --- gastrointestinal system disease ---
    Choice(
        sid="gastrointestinal-system-disease",
        name="gastrointestinal system disease",
        description="A disease of anatomical entity that is located_in the gastrointestinal tract.",
        parents=["disease"],
        annotations=[
            (BQB.IS, "doid/DOID:77"),
        ],
        synonyms=[],
    ),
    Choice(
        sid="duodenal-ulcer",
        name="duodenal ulcer",
        description="An ulcer in the duodenal wall.",
        parents=["gastrointestinal-system-disease"],
        annotations=[
            (BQB.IS, "doid/DOID:1724"),
            (BQB.IS, "NCIT:C26755"),
        ],
        synonyms=["ulceration"],
    ),
    Choice(
        sid="hepatobiliary-disease",
        name="hepatobiliary disease",
        description="A gastrointestinal system disease that is located_in the liver and/or biliary "
        "tract. A non-neoplastic or neoplastic disorder that affects the liver, "
        "bile ducts, and gallbladder. Representative examples of non-neoplastic "
        "disorders include hepatitis, cirrhosis, cholangitis, and cholecystitis. "
        "Representative examples of neoplastic disorders include hepatocellular "
        "adenoma, hepatocellular carcinoma, and cholangiocarcinoma.",
        parents=["gastrointestinal-system-disease"],
        annotations=[
            (BQB.IS, "doid/DOID:3118"),
            (BQB.IS, "NCIT:C3959"),
        ],
        synonyms=["hepatobiliary disorder"],
    ),
    Choice(
        sid="liver-disease",
        name="liver disease",
        description="A disease involving the liver. "
        "A non-neoplastic or neoplastic disorder that affects the "
        "liver parenchyma and/or intrahepatic bile ducts. Representative "
        "examples of non-neoplastic disorders include hepatitis, cirrhosis, "
        "cholangitis, and polycystic liver disease. Representative examples of "
        "neoplastic disorders include hepatocellular adenoma, "
        "hepatocellular carcinoma, intrahepatic cholangiocarcinoma, "
        "lymphoma, and angiosarcoma.",
        parents=["hepatobiliary-disease"],
        annotations=[
            (BQB.IS, "doid/DOID:409"),
            (BQB.IS, "NCIT:C3196"),  # Liver and Intrahepatic Bile Duct Disorder
            (BQB.IS, "efo/0001421"),
        ],
    ),
    Choice(
        sid="liver-disease-qualitative",
        name="liver disease (qualitative)",
        description="Liver disease qualitative.",
        parents=["liver disease"],
        dtype=DType.ABSTRACT,
        annotations=[
            (BQB.IS_VERSION_OF, "doid/DOID:409"),
            (BQB.IS_VERSION_OF, "NCIT:C3196"),
            (BQB.IS_VERSION_OF, "efo/0001421"),
        ],
    ),
    Choice(
        sid="liver-disease-minimal",
        name="liver disease (minimal)",
        description="Minimal liver disease",
        parents=["liver-disease-qualitative"],
        annotations=[
            (BQB.IS_VERSION_OF, "doid/DOID:409"),
            (BQB.IS_VERSION_OF, "NCIT:C3196"),
            (BQB.IS_VERSION_OF, "efo/0001421"),
        ],
    ),
    Choice(
        sid="liver-disease-mild",
        name="liver disease (mild)",
        description="Mild liver disease",
        parents=["liver-disease-qualitative"],
        annotations=[
            (BQB.IS_VERSION_OF, "doid/DOID:409"),
            (BQB.IS_VERSION_OF, "NCIT:C3196"),
            (BQB.IS_VERSION_OF, "efo/0001421"),
        ],
    ),
    Choice(
        sid="liver-disease-moderate",
        name="liver disease (moderate)",
        description="Moderate liver disease",
        parents=["liver-disease-qualitative"],
        annotations=[
            (BQB.IS_VERSION_OF, "doid/DOID:409"),
            (BQB.IS_VERSION_OF, "NCIT:C3196"),
            (BQB.IS_VERSION_OF, "efo/0001421"),
        ],
    ),
    Choice(
        sid="liver-disease-severe",
        name="liver disease (severe)",
        description="Severe or end-stage liver disease",
        parents=["liver-disease-qualitative"],
        annotations=[
            (BQB.IS_VERSION_OF, "doid/DOID:409"),
            (BQB.IS_VERSION_OF, "NCIT:C3196"),
            (BQB.IS_VERSION_OF, "efo/0001421"),
        ],
    ),
    Choice(
        sid="hemochromatosis",
        name="hemochromatosis",
        description="A metal metabolism disorder characterized by the accumulation of iron in "
        "various organs of the body. Accumulation of iron in internal organs. "
        "Disorder due to the deposition of hemosiderin in the parenchymal cells, "
        "causing tissue damage and dysfunction of the liver, pancreas, heart, "
        "and pituitary.",
        parents=["genetic-disease", "disease-of-metabolism"],
        annotations=[
            (BQB.IS, "doid/DOID:2352"),
            (BQB.IS, "NCIT:C82892"),
            (BQB.IS, "efo/1000642"),
        ],
        synonyms=["HC"],
    ),
    Choice(
        sid="liver-damage",
        name="liver damage",
        description="Damage of the liver, e.g., necrosis due to acetaminophen overdose.",
        parents=["liver disease"],
        annotations=[],
    ),
    Choice(
        sid="subacute hepatic necrosis",
        name="subacute hepatic necrosis",
        description="Subacute hepatic necrosis.",
        parents=["liver-damage"],
        annotations=[],
        synonyms=["SHN"],
    ),
    Choice(
        sid="alcoholic-liver-disease",
        name="alcoholic liver disease",
        description="Alcoholic liver disease. A disorder caused by damage to the "
        "liver parenchyma due to alcohol consumption. It may present with "
        "an acute onset or follow a chronic course, leading to cirrhosis.",
        parents=["liver disease"],
        annotations=[
            (BQB.IS, "NCIT:C34783"),
            (BQB.IS, "efo/0008573"),
        ],
        synonyms=["alcohol liver disease", "ALD"],
    ),
    Choice(
        sid="hepatocellular-carcinoma",
        name="hepatocellular carcinoma",
        label="hepatocellular carcinoma (HCC)",
        description="Hepatocellular carcinoma. A malignant tumor that arises from hepatocytes.",
        parents=["liver disease", "cancer"],
        annotations=[(BQB.IS, "doid/DOID:684"), (BQB.IS, "NCIT:C3099")],
        synonyms=["HCC"],
    ),
    Choice(
        sid="liver-cirrhosis",
        name="liver cirrhosis",
        description="Liver disease in which the normal microcirculation, the gross "
        "vascular anatomy, and the hepatic architecture have been variably "
        "destroyed and altered with fibrous septa surrounding regenerated "
        "or regenerating parenchymal nodules.",
        parents=["liver disease"],
        annotations=[(BQB.IS, "doid/DOID:5082"), (BQB.IS, "NCIT:C2951")],
    ),
    Choice(
        sid="decompensated-liver-cirrhosis",
        name="decompensated liver cirrhosis",
        description="Decompensated liver cirrhosis",
        parents=["liver cirrhosis"],
        annotations=[],
    ),
    Choice(
        sid="alcoholic-liver-cirrhosis",
        name="alcoholic liver cirrhosis",
        description="alcoholic liver cirrhosis",
        parents=["liver cirrhosis", "alcoholic liver disease"],
        annotations=[(BQB.IS, "doid/DOID:14018")],
    ),
    Choice(
        sid="postnecrotic-liver-cirrhosis",
        name="postnecrotic liver cirrhosis",
        description="Postnecrotic liver cirrhosis",
        parents=["liver cirrhosis"],
        annotations=[],
    ),
    Choice(
        sid="cryptogenic-liver-cirrhosis",
        name="cryptogenic liver cirrhosis",
        description="Liver cirrhosis in which no causative agent can be identified.",
        parents=["liver cirrhosis"],
        annotations=[(BQB.IS_VERSION_OF, "NCIT:C84411")],
    ),
    Choice(
        sid="non-cirrhotic-liver-disease",
        name="non-cirrhotic liver disease",
        description="non-cirrhotic liver disease",
        parents=["liver disease"],
    ),
    Choice(
        sid="hepatitis",
        description="Hepatitis. Inflammation of the liver; usually from a viral "
        "infection, but sometimes from toxic agents.",
        parents=["liver disease"],
        annotations=[
            (BQB.IS, "doid/DOID:2237"),
            (BQB.IS, "NCIT:C3095"),
            (BQB.IS, "hp/HP:0012115"),
        ],
    ),
    Choice(
        sid="alcoholic-hepatitis",
        name="alcoholic-hepatitis",
        description="Alcoholic hepatitis.",
        parents=["hepatitis"],
        annotations=[
            (BQB.IS, "doid/DOID:12351"),
        ],
    ),
    Choice(
        sid="drug-induced-hepatitis",
        name="drug-induced hepatitis",
        description="Drug-induced hepatitis.",
        parents=["hepatitis"],
        annotations=[
            (BQB.IS, "doid/DOID:2044"),
        ],
    ),
    Choice(
        sid="viral-hepatitis",
        name="viral hepatitis",
        description="A hepatitis that involves viral infection causing inflammation of "
        "the liver.",
        parents=["hepatitis"],
        annotations=[
            (BQB.IS, "doid/DOID:1844"),
        ],
    ),
    Choice(
        sid="hepatitis-a",
        name="hepatitis A",
        description="A hepatitis that involves viral infection by Hepatitis A virus causing "
        "inflammation of the liver.",
        parents=["viral-hepatitis"],
        annotations=[
            (BQB.IS, "doid/DOID:12549"),
            (BQB.IS, "NCIT:C3096"),
        ],
        synonyms=["HBV"],
    ),
    Choice(
        sid="hepatitis-b",
        name="hepatitis B",
        description="A hepatitis that involves viral infection by Hepatitis B virus causing "
        "inflammation of the liver.",
        parents=["viral-hepatitis"],
        annotations=[
            (BQB.IS, "doid/DOID:2043"),
        ],
        synonyms=["HBV"],
    ),
    Choice(
        sid="hcv",
        name="hcv",
        label="Hepatitis C virus (HCV)",
        description="Hepatitis C virus (HCV) infection. A viral infectious disease that results_in "
        "inflammation located_in liver, has_material_basis_in Hepatitis C virus, "
        "which is transmitted_by blood from an infected person enters the body of an "
        "uninfected person. The infection has_symptom fever, has_symptom fatigue, "
        "has_symptom loss of appetite, has_symptom nausea, has_symptom vomiting, "
        "has_symptom abdominal pain, has_symptom clay-colored bowel movements, "
        "has_symptom joint pain, and has_symptom jaundice.",
        parents=["viral hepatitis"],
        annotations=[
            (BQB.IS_VERSION_OF, "doid/DOID:1883"),
            (BQB.IS_VERSION_OF, "NCIT:C14312"),
        ],
        synonyms=["hepatitis C"],
    ),
    Choice(
        sid="chronic-hepatitis",
        name="chronic hepatitis",
        description="An active inflammatory process affecting the liver for more than "
        "six months. Causes include viral infections, autoimmune "
        "disorders, drugs, and metabolic disorders.",
        parents=["hepatitis"],
        annotations=[
            (BQB.IS, "NCIT:C82978"),
            (BQB.IS, "efo/0008496"),
        ],
    ),
    Choice(
        sid="toxic-hepatitis",
        name="toxic hepatitis",
        description="Toxic hepatitis.",
        parents=["hepatitis"],
        annotations=[(BQB.IS, "SNOMEDCT:197352008")],
    ),
    Choice(
        sid="biliary-liver-disease",
        name="biliary liver disease",
        description="A non-neoplastic or neoplastic disorder that affects the intrahepatic "
        "or extrahepatic bile ducts or the gallbladder. Representative "
        "examples of non-neoplastic disorders include cholangitis and "
        "cholecystitis. Representative examples of neoplastic disorders "
        "include extrahepatic bile duct adenoma, intrahepatic and "
        "extrahepatic cholangiocarcinoma, and gallbladder carcinoma.",
        parents=["hepatobiliary-disease"],
        annotations=[
            (BQB.IS_VERSION_OF, "doid/DOID:9741"),
            (BQB.IS_VERSION_OF, "NCIT:C2899"),
        ],
        synonyms=["biliary tract disease"],
    ),
    Choice(
        sid="biliary-obstruction",
        name="biliary obstruction",
        description="Blockage in the biliary tract that carries bile from the liver "
        "to the gallbladder and small intestine. Causes include gallstones, "
        "biliary tract strictures and inflammation, pancreatitis, cirrhosis, "
        "lymph node enlargement, and bile duct and pancreas neoplasms.",
        parents=["biliary-liver-disease"],
        annotations=[
            (BQB.IS, "NCIT:C60698"),
        ],
    ),
    Choice(
        sid="pbc",
        name="pbc",
        label="PBC",
        description="Primary biliary cholangitis or primary biliary cirrhosis (PBC) "
        "(autoimune disease of the liver). A liver cirrhosis characterized by chronic and slow "
        "progressive destruction of intrahepatic bile ducts.",
        parents=["biliary liver disease", "liver cirrhosis"],
        annotations=[
            (BQB.IS, "doid/DOID:12236"),
            (BQB.IS_VERSION_OF, "NCIT:C26718"),
        ],
    ),
    Choice(
        sid="biliary-calculus",
        name="biliary calculus",
        description="The presence of one or more stones in the bile duct. "
        "They are composed either of cholesterol or, less commonly, "
        "calcium salts and bilirubin.",
        parents=["biliary-liver-disease"],
        annotations=[
            (BQB.IS, "SNOMEDCT:266474003"),
            (BQB.IS, "NCIT:C35773"),
            (BQB.IS, "NCIT:C122822"),
        ],
        synonyms=["Calculus in biliary tract", "Bile Duct Stone", "Cholelithiasis"],
    ),
    Choice(
        sid="fatty-liver-disease",
        name="fatty liver disease",
        description="Fatty liver disease. A reversible condition wherein large vacuoles "
        "of triglyceride fat accumulate in liver cells via the process "
        "of steatosis. ",
        parents=["non-cirrhotic liver disease"],
        annotations=[(BQB.IS, "doid/DOID:9452"), (BQB.IS, "mondo/0004790")],
        synonyms=["steatotic liver disease"],
    ),
    Choice(
        sid="nafld",
        name="nafld",
        label="non-alcoholic fatty liver disease (NAFLD)",
        description="Non-alcoholic fatty liver disease (NAFLD). "
        "A term referring to fatty replacement of the hepatic parenchyma "
        "which is not related to alcohol use.",
        parents=["fatty-liver-disease"],
        annotations=[
            (BQB.IS, "doid/DOID:0080208"),
            (BQB.IS, "NCIT:C84444"),
            (BQB.IS, "efo/0003095"),
        ],
    ),
    Choice(
        sid="nash",
        name="nash",
        label="NASH",
        description="Non-alcoholic steato-hepatitis (NASH). Fatty replacement and "
        "damage to the hepatocytes not related to alcohol use. "
        "It may lead to cirrhosis and liver failure.",
        parents=["nafld"],
        annotations=[
            (BQB.IS, "doid/DOID:0080547"),
            (BQB.IS, "efo/1001249"),
            (BQB.IS, "NCIT:C84445"),
        ],
    ),
    Choice(
        sid="mafld",
        name="mafld",
        label="metabolic dysfunction-associated steatotic liver disease (MAFLD)",
        description="A steatotic liver disease characterized by at least one of five specified "
        "cardiometabolic risk factors and no other discernible cause with normal to "
        "no alcohol use. The five cardiometabolic risk factors are: (1) higher than "
        "normal body mass index or waist circumference; (2) higher than normal serum "
        "glucose or glycated hemoglobin level, or type 2 diabetes; (3) higher than "
        "normal blood pressure or hypertensive treatment; (4) higher than normal "
        "plasma triglycerides or lipid lowering treatment; and (5) lower than "
        "normal plasma high-density lipoprotein cholesterol.",
        parents=["fatty-liver-disease"],
        annotations=[
            (BQB.IS, "doid/DOID:0080208"),
        ],
    ),
    Choice(
        sid="mash",
        name="mash",
        label="metabolic dysfunction-associated steatohepatitis (MASH)",
        description="A metabolic dysfunction-associated steatotic liver disease characterized by "
        "the presence of inflammation with hepatocyte injury such as ballooning, with "
        "or without fibrosis.",
        parents=["mafld"],
        annotations=[
            (BQB.IS, "doid/DOID:0080547"),
        ],
    ),
    Choice(
        sid="miscellaneous-liver-disease",
        name="miscellaneous liver disease",
        description="Liver disease not clearly characterized in any other "
        "liver disease.",
        parents=["liver disease"],
    ),
    Choice(
        sid="liver-fibrosis",
        name="liver fibrosis",
        description="A liver disease that is characterized by progressive detrimental connective "
        "tissue deposition of the liver parenchyma leading to deterioration of "
        "liver function.",
        parents=["liver disease"],
        annotations=[
            (BQB.IS, "hp/HP:0001395"),
            (BQB.IS_VERSION_OF, "NCIT:C3044"),  # fibrosis
            (BQB.IS_VERSION_OF, "efo/0006890"),  # fibrosis
        ],
        synonyms=["hepatic fibrosis"],
    ),
    Choice(
        sid="liver-fibrosis-f1",
        name="liver fibrosis (F1)",
        description="Fibrosis of the liver (F1 stage).",
        parents=["liver fibrosis"],
    ),
    Choice(
        sid="liver-fibrosis-f2",
        name="liver fibrosis (F2)",
        description="Fibrosis of the liver (F4 stage).",
        parents=["liver fibrosis"],
    ),
    Choice(
        sid="liver-fibrosis-f3",
        name="liver fibrosis (F3)",
        description="Fibrosis of the liver (F4 stage).",
        parents=["liver fibrosis"],
    ),
    Choice(
        sid="liver-fibrosis-f4",
        name="liver fibrosis (F4)",
        description="Fibrosis of the liver (F4 stage).",
        parents=["liver fibrosis"],
    ),
    Choice(
        sid="renal-disease",
        name="renal disease",
        description="Renal disease or kidney disorder. "
        "A neoplastic or non-neoplastic condition affecting the kidney. "
        "Representative examples of non-neoplastic conditions include "
        "glomerulonephritis and nephrotic syndrome. Representative examples of "
        "neoplastic conditions include benign processes "
        "(e.g., renal lipoma and renal fibroma) and malignant processes "
        "(e.g., renal cell carcinoma and renal lymphoma).",
        parents=["disease"],
        synonyms=["kidney disease"],
        annotations=[
            (BQB.IS, "doid/DOID:557"),
            (BQB.IS, "NCIT:C3149"),
            (BQB.IS, "efo/0003086"),
        ],
    ),
    Choice(
        sid="renal-disease-mild",
        name="renal disease (mild)",
        description="Mild renal disease.",
        parents=["renal-disease"],
    ),
    Choice(
        sid="renal-disease-moderate",
        name="renal disease (moderate)",
        description="moderate renal disease (not requiring dialysis)",
        parents=["renal-disease"],
    ),
    Choice(
        sid="renal-disease-severe",
        name="renal disease (severe)",
        description="moderate renal disease (severe)",
        parents=["renal-disease"],
    ),
    Choice(
        sid="renal-disease-end-stage",
        name="renal disease (end-stage)",
        description="severe or end-stage renal disease (requiring dialysis)",
        synonyms=["chronic renal failure"],
        parents=["renal-disease"],
    ),
    Choice(
        sid="renal-hypoplasia",
        name="renal hypoplasia",
        description="Absence or underdevelopment of the kidney. A kidney disease that is "
        "characterized by abnormally small kidneys with normal morphology and reduced "
        "number of nephrons.",
        parents=["renal-disease"],
        synonyms=[],
        annotations=[(BQB.IS, "doid/DOID:0080204"), (BQB.IS, "efo/0008678")],
    ),
    Choice(
        sid="renal carcinoma",
        name="renal carcinoma",
        description="A carcinoma arising from the epithelium of the renal parenchyma "
        "or the renal pelvis. The majority are renal cell carcinomas. "
        "Kidney carcinomas usually affect middle aged and elderly adults. "
        "Hematuria, abdominal pain, and a palpable mass are common "
        "symptoms.",
        parents=["renal-disease"],
        annotations=[
            (BQB.IS, "DOID:4451"),
            (BQB.IS, "NCIT:C9384"),
        ],
        synonyms=["kidney carcinoma"],
    ),
    Choice(
        sid="pyelonephritis",
        description="Pyelonephritis. An inflammatory process affecting "
        "the kidney. The cause is most often bacterial, but may "
        "also be fungal in nature. Signs and symptoms may "
        "include fever, chills, flank pain, painful and frequent "
        "urination, cloudy or bloody urine, and confusion.",
        parents=["renal-disease"],
        annotations=[
            (BQB.IS, "doid/DOID:11400"),
            (BQB.IS, "NCIT:C34965"),
            (BQB.IS, "efo/1001141"),
        ],
    ),
    Choice(
        sid="chronic-pyelonephritis",
        name="chronic pyelonephritis",
        description="Chronic pyelonephritis. Persistent pyelonephritis.",
        parents=["pyelonephritis"],
        annotations=[
            (BQB.IS, "doid/DOID:1076"),
            (BQB.IS, "NCIT:C123216"),
        ],
    ),
    Choice(
        sid="nephrosclerosis",
        description="Hardening of the kidney due to infiltration by fibrous connective "
        "tissue (fibrosis), usually caused by renovascular diseases or "
        "chronic hypertension. Nephrosclerosis leads to renal ischemia.",
        parents=["renal disease"],
        annotations=[
            (BQB.IS, "doid/DOID:11664"),
            (BQB.IS, "efo/1000041"),
        ],
    ),
    Choice(
        sid="arterionephrosclerosis",
        description="Scarring and atrophy of the renal cortex that occurs in hypertensive patients and in old age.",
        parents=["nephrosclerosis"],
        annotations=[(BQB.IS, "NCIT:C97144")],
    ),
    Choice(
        sid="cystic-kidney-disease",
        name="cystic kidney disease",
        description="Cystic kidney disease. A congenital or acquired kidney disorder "
        "characterized by the presence of renal cysts.",
        parents=["renal disease"],
        annotations=[
            (BQB.IS, "doid/DOID:2975"),
            (BQB.IS, "efo/0008615"),
        ],
        synonyms=["cystic degeneration of the kidney", "cystic kidneys"],
    ),
    Choice(
        sid="polycystic-kidney-disease",
        name="polycystic kidney disease",
        description="A usually autosomal dominant and less frequently autosomal "
        "recessive genetic disorder characterized by the presence of "
        "numerous cysts in the kidneys leading to end-stage renal failure.",
        synonyms=["PKD"],
        parents=["cystic kidney disease"],
        annotations=[
            (BQB.IS, "doid/DOID:0080322"),
            (BQB.IS, "NCIT:C75464"),
        ],
    ),
    Choice(
        sid="anephric",
        description="Loss of kidneys mostly surgically.",
        parents=["renal disease (end-stage)"],
    ),
    Choice(
        sid="glomerulosclerosis",
        description="A hardening of the kidney glomerulus caused "
        "by scarring of the blood vessels.",
        parents=["renal disease"],
        annotations=[
            (BQB.IS, "doid/DOID:0050851"),
            (BQB.IS, "NCIT:C120888"),
        ],
    ),
    Choice(
        sid="glomerulonephritis",
        description="Glomerulonephritis. A renal disorder characterized by "
        "damage in the glomeruli. It may be acute or chronic, "
        "focal or diffuse, and it may lead to renal failure. "
        "Causes include autoimmune disorders, infections, "
        "diabetes, and malignancies.",
        parents=["renal-disease"],
        annotations=[
            (BQB.IS, "doid/DOID:2921"),
            (BQB.IS, "NCIT:C26784"),
        ],
    ),
    Choice(
        sid="chronic-glomerulonephritis",
        name="chronic glomerulonephritis",
        description="Chronic glomerulonephritis. A chronic, persistent "
        "inflammation of the glomeruli, which is slowly progressive, "
        "leading to impaired kidney function.",
        parents=["glomerulonephritis"],
        annotations=[
            (BQB.IS, "NCIT:C35173"),
        ],
        synonyms=["chronic glomerulonephritis"],
    ),
    Choice(
        sid="acute-glomerulonephritis",
        name="acute glomerulonephritis",
        description="Acute glomerulonephritis.",
        parents=["glomerulonephritis"],
        annotations=[(BQB.IS_VERSION_OF, "NCIT:C26784")],
    ),
    Choice(
        sid="focal-glomerulonephritis",
        name="focal glomerulonephritis",
        description="Focal glomerulonephritis.",
        parents=["glomerulonephritis"],
        annotations=[(BQB.IS_VERSION_OF, "NCIT:C26784")],
    ),
    Choice(
        sid="diffuse-glomerulonephritis",
        name="diffuse glomerulonephritis",
        description="Diffuse glomerulonephritis.",
        parents=["glomerulonephritis"],
        annotations=[(BQB.IS_VERSION_OF, "NCIT:C26784")],
    ),
    # --- cardiovascular system disease ---
    Choice(
        sid="cardiovascular_disease",
        name="cardiovascular system disease",
        description="A disease involving the cardiovascular system. A disease of anatomical entity which occurs in "
        "the blood, heart, blood vessels or the lymphatic system that passes nutrients (such as amino "
        "acids and electrolytes), gases, hormones, blood cells or lymph to and from cells in the body to "
        "help fight diseases and help stabilize body temperature and pH to maintain homeostasis.",
        parents=["disease"],
        annotations=[
            (BQB.IS, "doid/DOID:1287"),
            (BQB.IS, "NCIT:C2931"),
            (BQB.IS, "efo/0000319"),
        ],
        synonyms=[],
    ),
    Choice(
        sid="heart-disease",
        name="heart disease",
        description="Pathological conditions involving the HEART including its structural "
        "and functional abnormalities. A cardiovascular system disease that involves the heart.",
        parents=["cardiovascular_disease"],
        annotations=[
            (BQB.IS, "doid/DOID:114"),
            (BQB.IS, "efo/0003777"),
        ],
    ),
    Choice(
        sid="heart-failure",
        name="heart failure",
        description="Heart failure. Inability of the heart to pump blood at an adequate rate to meet tissue "
        "metabolic requirements. Clinical symptoms of heart failure include: unusual dyspnea on light "
        "exertion, recurrent dyspnea occurring in the supine position, fluid retention or rales, "
        "jugular venous distension, pulmonary edema on physical exam.",
        parents=["heart-disease"],
        annotations=[
            (BQB.IS, "NCIT:C50577"),
            (BQB.IS, "efo/0003144"),
        ],
    ),
    Choice(
        sid="congestive-heart-failure",
        name="congestive heart failure",
        description="Congestive heart failure. Failure of the heart to pump a "
        "sufficient amount of blood to meet the needs of the body tissues, "
        "resulting in tissue congestion and edema. Signs and symptoms "
        "include shortness of breath, pitting edema, enlarged tender "
        "liver, engorged neck veins, and pulmonary rales.",
        parents=["heart-failure"],
        annotations=[
            (BQB.IS, "doid/DOID:6000"),
            (BQB.IS, "efo/0000373"),
            (BQB.IS, "NCIT:C3080"),
        ],
    ),
    Choice(
        sid="cardiac-arrhythmia",
        name="cardiac arrhythmia",
        description="Cardiac arrythmia. Any disturbances of the normal rhythmic "
        "beating of the heart or myocardial contraction. Cardiac arrhythmias "
        "can be classified by the abnormalities in HEART RATE, disorders of "
        "electrical impulse generation, or impulse conduction.",
        parents=["heart disease"],
        annotations=[
            (BQB.IS, "omit/0002531"),
            (BQB.IS, "efo/0004269"),
        ],
        synonyms=["arrythmia"],
    ),
    Choice(
        sid="ischemic-heart-disease",
        name="ischemic heart disease",
        description="A disorder of cardiac function caused by insufficient blood flow "
        "to the muscle tissue of the heart. The decreased blood flow may "
        "be due to narrowing of the coronary arteries,"
        "to obstruction by a thrombus, or less commonly, to diffuse narrowing of arterioles and "
        "other small vessels within the heart. Severe interruption of the blood "
        "supply to the myocardial tissue may result in necrosis of cardiac muscle "
        "(myocardial infarction).",
        parents=["heart disease"],
        annotations=[
            (BQB.IS, "NCIT:C50625"),
        ],
    ),
    Choice(
        sid="myocardial-infarction",
        name="myocardial infarction",
        description="Gross necrosis of the myocardium, as a result of interruption of the "
        "blood supply to the area, as in coronary thrombosis.",
        parents=["cardiovascular-disease"],
        annotations=[
            (BQB.IS, "doid/DOID:5844"),
            (BQB.IS, "NCIT:C27996"),
        ],
    ),
    Choice(
        sid="premature-ventricular-contraction",
        name="premature ventricular contraction",
        description="Extra beats beginning in the ventricles, that can disrupt the regular heart rhythm.",
        parents=["heart-disease"],
        synonyms=["VPB", "PVC"],
        annotations=[
            (BQB.IS, "NCIT:C54936"),
        ],
    ),
    Choice(
        sid="ventricular-fibrillation",
        name="ventricular fibrillation",
        description="A disorder characterized by an electrocardiographic finding of a "
        "rapid grossly irregular ventricular rhythm with marked variability "
        "in QRS cycle length, morphology, and amplitude. "
        "The rate is typically greater than 300 bpm.",
        parents=["heart-disease"],
        synonyms=[],
        annotations=[
            (BQB.IS, "NCIT:C50799"),
            (BQB.IS, "omit/0015525"),
            (BQB.IS, "efo/0004287"),
        ],
    ),
    Choice(
        sid="primary-ventricular-fibrillation",
        name="primary ventricular fibrillation",
        description="PVF is defined as ventricular fibrillation not preceded by heart "
        "failure or shock, in contrast to secondary ventricular "
        "fibrillation, which is. Ventricular fibrillation is characterized "
        "by an electrocardiographic finding of a rapid grossly irregular ventricular rhythm.",
        parents=["ventricular fibrillation"],
        synonyms=["PVF"],
        annotations=[
            (BQB.IS_VERSION_OF, "NCIT:C50799"),
            (BQB.IS_VERSION_OF, "omit/0015525"),
            (BQB.IS_VERSION_OF, "efo/0004287"),
        ],
    ),
    Choice(
        sid="coronary-atherosclerosis",
        name="coronary atherosclerosis",
        description="Atherosclerosis of the coronary vasculature. Reduction of the "
        "diameter of the coronary arteries as the result of an "
        "accumulation of atheromatous plaques within the walls of the "
        "coronary arteries, which increases the risk of myocardial "
        "ischemia.",
        parents=["heart disease"],
        synonyms=[],
        annotations=[
            (BQB.IS_VERSION_OF, "NCIT:C35505"),
        ],
    ),
    # --- infectious disease ---
    Choice(
        sid="infectious-disorder",
        name="infectious disorder",
        description="A disorder resulting from the presence and activity of a microbial, "
        "viral, fungal, or parasitic agent. It can be transmitted by direct or "
        "indirect contact.",
        parents=["disease"],
        annotations=[
            (BQB.IS, "NCIT:C26726"),
        ],
    ),
    Choice(
        sid="malaria",
        description="Malaria or plasmodium falciparum infection. "
        "A protozoan infection caused by the genus Plasmodium. There are four "
        "species of Plasmodium that can infect humans: Plasmodium falciparum, "
        "vivax, ovale, and malariae. It is transmitted to humans by infected "
        "mosquitoes. Signs and symptoms include paroxysmal high fever, "
        "sweating, chills, and anemia.",
        parents=["infectious disorder"],
        annotations=[
            (BQB.IS, "NCIT:C34797"),
            (BQB.IS, "efo/0001068"),
            (BQB.IS, "doid/DOID:12365"),
        ],
    ),
    Choice(
        sid="central-nervous-system-disease",
        name="central nervous system disease",
        description="A nervous system disease that affects either the spinal cord (myelopathy) or brain "
        "(encephalopathy) of the central nervous system.",
        parents=["disease"],
        annotations=[(BQB.IS, "doid/DOID:331")],
    ),
    Choice(
        sid="brain-disease",
        name="brain disease",
        description="A central nervous system disease that is located_in the brain.",
        parents=["central-nervous-system-disease"],
        annotations=[(BQB.IS, "doid/DOID:936")],
    ),
    Choice(
        sid="epilepsy",
        description="Epilepsy is a disorder characterized by recurrent episodes of "
        "paroxysmal brain dysfunction due to a sudden, disorderly, and "
        "excessive neuronal discharge. Epilepsy classification systems are "
        "generally based upon: (1) clinical features of the seizure episodes "
        "(e.g., motor seizure), (2) etiology (e.g., post-traumatic), "
        "(3) anatomic site of seizure origin (e.g., frontal lobe seizure), "
        "(4) tendency to spread to other structures in the brain, and "
        "(5) temporal patterns (e.g., nocturnal epilepsy).",
        parents=["brain-disease"],
        annotations=[
            (BQB.IS, "doid/DOID:1826"),
            (BQB.IS, "efo/0000474"),
        ],
    ),
    Choice(
        sid="parkinsonism",
        name="Parkinsonism",
        description="A movement disorder that is characterized by disturbances of balance, gait "
        "and posture. Neurologic anomaly resulting from degeneration of "
        "dopamine-generating cells in the substantia nigra, a region of "
        "the midbrain, characterized clinically by shaking, rigidity, "
        "slowness of movement and difficulty with walking and gait.",
        parents=["brain-disease"],
        annotations=[
            (BQB.IS, "doid/DOID:0080855"),
            (BQB.IS, "hp/HP:0001300"),
            (BQB.IS, "SNOMEDCT:32798002"),
        ],
    ),
    Choice(
        sid="migraine",
        description="A common, severe type of vascular headache often associated with "
        "increased sympathetic activity, resulting in nausea, vomiting, "
        "and light sensitivity. A class of disabling primary headache disorders, "
        "characterized by recurrent unilateral pulsatile headaches. "
        "The two major subtypes are common migraine (without aura) and "
        "classic migraine (with aura or neurological symptoms).",
        parents=["brain-disease"],
        annotations=[
            (BQB.IS, "doid/DOID:6364"),
            (BQB.IS, "efo/0003821"),
            (BQB.IS, "NCIT:C89715"),
        ],
    ),
    Choice(
        sid="stroke",
        name="stroke",
        description="A group of pathological conditions characterized by sudden, non-convulsive "
        "loss of neurological function due to brain ischemia or intracranial "
        "hemorrhages."
        "A disorder characterized by a decrease or absence of blood supply to the "
        "brain caused by obstruction (thrombosis or embolism) of an artery resulting "
        "in neurological damage.",
        parents=["brain-disease"],
        annotations=[
            (BQB.IS, "doid/DOID:3454"),
            (BQB.IS, "NCIT:C143862"),
            (BQB.IS, "efo/0000712"),
        ],
        synonyms=["brain infarction", "apoplectic insult"],
    ),
    Choice(
        sid="disease-of-mental-health",
        name="disease of mental health",
        description="A disease that involves a psychological or behavioral pattern generally "
        "associated with subjective distress or disability that occurs in an "
        "individual, and which are not a part of normal development or culture.",
        parents=["disease"],
        annotations=[(BQB.IS, "doid/DOID:936")],
    ),
    Choice(
        sid="psychatric-disorder",
        name="psychatric disorder",
        description="A disorder characterized by behavioral and/or psychological "
        "abnormalities, often accompanied by physical symptoms. The symptoms "
        "may cause clinically significant distress or impairment in social and "
        "occupational areas of functioning. Representative examples include "
        "anxiety disorders, cognitive disorders, mood disorders and "
        "schizophrenia.",
        parents=["disease-of-mental-health"],
        annotations=[
            (BQB.IS, "NCIT:C2893"),
        ],
    ),
    Choice(
        sid="schizophrenia",
        description="Schizophrenia. A major psychotic disorder characterized by "
        "abnormalities in the perception or expression of reality. "
        "It affects the cognitive and psychomotor functions. Common clinical "
        "signs and symptoms include delusions, hallucinations, disorganized "
        "thinking, and retreat from reality.",
        parents=["disease-of-mental-health"],
        annotations=[
            (BQB.IS, "doid/DOID:5419"),
            (BQB.IS, "NCIT:C3362"),
            (BQB.IS, "efo/0000692"),
        ],
    ),
    Choice(
        sid="disease-of-glucose-metabolism",
        name="disease of glucose metabolism",
        description="Disease of glucose metabolism or abnormality of glucose homeostasis.",
        parents=["disease-of-metabolism"],
        annotations=[
            (BQB.IS, "doid/DOID:4194"),
        ],
        synonyms=["glucose metabolism disease"],
    ),
    Choice(
        sid="impaired-glucose-tolerance",
        name="impaired glucose tolerance",
        label="impaired glucose tolerance (IGT)",
        description="Impaired glucose tolerance (IGT) is an abnormal resistance to "
        "glucose, i.e., a reduction in the ability to maintain glucose levels "
        "in the blood stream within normal limits following oral or "
        "intravenous administration of glucose.",
        parents=["disease of glucose metabolism"],
        annotations=[
            (BQB.IS, "doid/DOID:11716"),
            (BQB.IS, "hp/HP:0040270"),
            (BQB.IS, "mp/MP:0005293"),
            (BQB.IS, "efo/0002546"),
        ],
        synonyms=["prediabetes"],
    ),
    Choice(
        sid="diabetes",
        description="Diabetes is a metabolic disorder characterized by abnormally high "
        "blood sugar levels due to diminished production of insulin or "
        "insulin resistance/desensitization.",
        parents=["disease-of-glucose-metabolism"],
        annotations=[
            (BQB.IS, "doid/DOID:9351"),
            (BQB.IS, "NCIT:C2985"),
            (BQB.IS, "efo/0000400"),
        ],
        synonyms=["diabetes mellitus"],
    ),
    Choice(
        sid="type-1-diabetes-mellitus",
        name="t1dm",
        label="type 1 diabetes mellitus (T1DM)",
        description="A diabetes mellitus that is characterized by destruction of pancreatic beta "
        "cells resulting in absent or extremely low insulin production.",
        parents=["diabetes"],
        annotations=[
            (BQB.IS, "doid/DOID:9744"),
            (BQB.IS, "NCIT:C2986"),
            (BQB.IS, "efo/0001359"),
        ],
    ),
    Choice(
        sid="type-2-diabetes-mellitus",
        name="t2dm",
        label="type 2 diabetes mellitus (T2DM)",
        description="Diabetes mellitus type 2. A type of diabetes mellitus that is "
        "characterized by insulin resistance or desensitization and increased "
        "blood glucose levels. This is a chronic disease that can develop "
        "gradually over the life of a patient and can be linked to both "
        "environmental factors and heredity.",
        parents=["diabetes"],
        annotations=[
            (BQB.IS, "doid/DOID:9352"),
            (BQB.IS, "NCIT:C26747"),
            (BQB.IS, "efo/0001360"),
        ],
    ),
    Choice(
        sid="diabetic-nephropathy",
        name="diabetic nephropathy",
        description="Diabetic nephropathy. Progressive kidney disorder "
        "caused by vascular damage to the glomerular "
        "capillaries, in patients with diabetes mellitus. "
        "It is usually manifested with nephritic syndrome and glomerulosclerosis.",
        parents=["renal disease", "diabetes"],
        annotations=[
            (BQB.IS, "NCIT:C84417"),
            (BQB.IS, "efo/0000401"),
        ],
    ),
    Choice(
        sid="benign-neoplasm",
        name="benign neoplasm",
        description="A disease of cellular proliferation that results in abnormal growths in "
        "the body which lack the ability to metastasize.",
        parents=["disease-of-cellular-proliferation"],
        synonyms=[],
        annotations=[(BQB.IS, "doid/DOID:0060072")],
    ),
    Choice(
        sid="prostata-adenoma",
        name="prostata adenoma",
        description="A disease caused by hyperplastic process of non-transformed "
        "prostatic cells. A non-cancerous nodular enlargement of the "
        "prostate gland. It is characterized by the presence of "
        "epithelial cell nodules, and stromal nodules containing "
        "fibrous and smooth muscle elements. It is the most common "
        "urologic disorder in men, causing blockage of urine flow. "
        "A non-cancerous nodular enlargement of the prostate gland. "
        "It is characterized by the presence of epithelial cell nodules, "
        "and stromal nodules containing fibrous and smooth muscle elements. "
        "It is the most common urologic disorder in men, causing blockage "
        "of urine flow. Increase in constituent cells in the PROSTATE, "
        "leading to enlargement of the organ (hypertrophy) and adverse "
        "impact on the lower urinary tract function. This can be caused"
        "by increased rate of cell proliferation, reduced rate of cell "
        "death, or both.",
        parents=["benign-neoplasm"],
        synonyms=[
            "benign prostatic hyperplasia",
            "prostatic adenoma",
            "prostate adenoma",
        ],
        annotations=[
            (BQB.IS, "doid/DOID:2883"),
            (BQB.IS, "efo/0000284"),
        ],
    ),
    Choice(
        sid="ovarian-cancer",
        name="ovarian cancer",
        description="A female reproductive organ cancer that is located in the ovary.",
        parents=["cancer"],
        synonyms=["Ovarian carcinoma"],
        annotations=[
            (BQB.IS, "DOID:2394"),
            (BQB.IS, "NCIT:C4908"),
        ],
    ),
    Choice(
        sid="breast-cancer",
        name="breast cancer",
        description="An organ system cancer that originates in the mammary gland. A primary or metastatic malignant neoplasm involving the breast. The vast majority of cases are carcinomas arising from the breast parenchyma or the nipple. Malignant breast neoplasms occur more frequently in females than in males.",
        parents=["cancer"],
        synonyms=["Breast carcinoma"],
        annotations=[
            (BQB.IS, "DOID:1612"),
        ],
    ),
    Choice(
        sid="bladder-cancer",
        name="bladder cancer",
        description="An organ system cancer that originates in the bladder.",
        parents=["cancer"],
        synonyms=[],
        annotations=[],
    ),
    Choice(
        sid="endometrial-cancer",
        name="endometrial cancer",
        description="A uterine cancer that is located in tissues lining the uterus.",
        parents=["cancer"],
        synonyms=["Endometrial carcinoma"],
        annotations=[
            (BQB.IS, "DOID:1380"),
            (BQB.IS, "NCIT:C7558"),
        ],
    ),
    Choice(
        sid="colorectal-cancer",
        name="colorectal cancer",
        description="A large intestine cancer that is located in the colon and/or located in the rectum.",
        parents=["cancer"],
        synonyms=[],
        annotations=[
            (BQB.IS, "DOID:9256"),
        ],
    ),
    Choice(
        sid="pancreatic-cancer",
        name="pancreatic cancer",
        description="An endocrine gland cancer located in the pancreas.",
        parents=["cancer"],
        synonyms=[],
        annotations=[
            (BQB.IS, "DOID:1793"),
        ],
    ),
    Choice(
        sid="stomach-cancer",
        name="stomach cancer",
        description="A gastrointestinal system cancer that is located in the stomach.",
        parents=["cancer"],
        synonyms=["gastric cancer"],
        annotations=[
            (BQB.IS, "DOID:10534"),
        ],
    ),
    Choice(
        sid="gastrointestinal-stromal-tumor",
        name="gastrointestinal stromal tumor",
        description="A stromal tumor most commonly seen in the gastrointestinal tract. Rare cases of solitary masses in the omentum or the mesentery have also been reported (extragastrointestinal gastrointestinal stromal tumor). It is a tumor that differentiates along the lines of interstitial cells of Cajal. Most cases contain KIT- or PDGFRA-activating mutations.",
        parents=["cancer"],
        synonyms=[],
        annotations=[
            (BQB.IS, "NCIT:C3868"),
            (BQB.IS, "DOID:9253"),
        ],
    ),
    # --- respiratory system disease ---
    Choice(
        sid="respiratory-system-disease",
        name="respiratory system disease",
        description="A disease of anatomical entity that located_in the respiratory system which "
        "extends from the nasal sinuses to the diaphragm.",
        parents=["disease"],
        synonyms=[],
        annotations=[
            (BQB.IS, "doid/DOID:1579"),
        ],
    ),
    Choice(
        sid="asthma",
        name="asthma",
        description="Asthma. A chronic respiratory disease manifested as difficulty "
        "breathing due to the narrowing of bronchial passageways. "
        "Asthma is characterized by increased responsiveness of the "
        "tracheobronchial tree to multiple stimuli, leading to narrowing "
        "of the air passages with resultant dyspnea, cough, and wheezing.",
        parents=["respiratory-system-disease"],
        annotations=[
            (BQB.IS, "doid/DOID:2841"),
            (BQB.IS, "NCIT:C28397"),
            (BQB.IS, "efo/0000270"),
        ],
    ),
    Choice(
        sid="bronchitis",
        name="bronchitis",
        description="A bronchial disease that is an inflammation of the bronchial tubes. "
        "It is caused by bacteria and viruses. The disease has_symptom cough with "
        "mucus, has_symptom shortness of breath, has_symptom low fever and "
        "has_symptom chest tightness.",
        parents=["respiratory-system-disease"],
        annotations=[
            (BQB.IS, "doid/DOID:6132"),
        ],
    ),
    Choice(
        sid="chronic-bronchitis",
        name="chronic bronchitis",
        description="A type of chronic obstructive pulmonary disease characterized by chronic "
        "inflammation in the bronchial tree that results in edema, mucus production,"
        "obstruction, and reduced airflow to and from the lung alveoli. The most common cause is "
        "tobacco smoking. Signs and symptoms include coughing with excessive mucus "
        "production, and shortness of breath.",
        parents=["bronchitis"],
        annotations=[
            (BQB.IS, "NCIT:C26722"),
        ],
    ),
    Choice(
        sid="lung-disease",
        name="lung disease",
        description="A lower respiratory tract disease in which the function of the lungs is "
        "adversely affected by narrowing or blockage of the airways resulting in "
        "poor air flow, a loss of elasticity in the lungs that produces a decrease "
        "in the total volume of air that the lungs are able to hold, and clotting, "
        "scarring, or inflammation of the blood vessels that affect the ability of "
        "the lungs to take up oxygen and to release carbon dioxide.",
        parents=["respiratory-system-disease"],
        synonyms=[],
        annotations=[
            (BQB.IS, "doid/DOID:850"),
        ],
    ),
    Choice(
        sid="lung-cancer",
        name="lung cancer",
        description="Lung cancer. (LNCR) - A common malignancy affecting "
        "tissues of the lung. The most common form of lung cancer "
        "is non-small cell lung cancer (NSCLC) that can be divided "
        "into 3 major histologic subtypes - squamous cell carcinoma, "
        "adenocarcinoma, and large cell lung cancer.",
        parents=["lung disease", "cancer"],
        synonyms=["Lung carcinoma", "LNCR"],
        annotations=[
            (BQB.IS, "doid/DOID:1324"),
            (BQB.IS, "NCIT:C2926"),
        ],
    ),
    Choice(
        sid="nsclc",
        name="NSCLC",
        label="Non small cell lung cancer (NSCLC)",
        description="Non small cell lung cancer (NSCLC). The most common form of lung cancer "
        "is non-small cell lung cancer (NSCLC) that can be divided "
        "into 3 major histologic subtypes - squamous cell carcinoma, "
        "adenocarcinoma, and large cell lung cancer."
        "NSCLC is often diagnosed at an advanced stage and has a "
        "poor prognosis.",
        parents=["lung cancer"],
        synonyms=[
            "Lung Non-Small Cell Carcinoma.",
            "lung non-squamous non-small cell carcinoma",
        ],
        annotations=[
            (BQB.IS, "doid/DOID:0080521"),
            (BQB.IS, "efo/0003060"),
        ],
    ),
    Choice(
        sid="pneumonia",
        name="pneumonia",
        description="A lung disease that involves lung parenchyma or alveolar "
        "inflammation and abnormal alveolar filling with fluid "
        "(consolidation and exudation). It results from infection with "
        "bacteria, viruses, fungi or parasites. It is accompanied by "
        "fever, chills, cough, and difficulty in breathing. An acute, "
        "acute and chronic, or chronic inflammation focally or diffusely "
        "affecting the lung parenchyma, caused by an infection in one or "
        "both of the lungs (by bacteria, viruses, fungi, or mycoplasma.). "
        "Symptoms include cough, shortness of breath, fevers, chills, "
        "chest pain, headache, sweating, and weakness.",
        parents=["lung-disease"],
        synonyms=[],
        annotations=[
            (BQB.IS, "doid/DOID:552"),
            (BQB.IS, "efo/0003106"),
        ],
    ),
    Choice(
        sid="extrahepatic-portal-obstruction",
        name="extrahepatic portal obstruction",
        description="Extrahepatic Portal Obstruction. An obstruction of the "
        "extrahepatic portal vein.",
        parents=["liver disease"],
        annotations=[],
    ),
    Choice(
        sid="sleep-disorder",
        name="central sleep apnea",
        description="A disease of mental health that involves disruption of sleep patterns.",
        parents=["disease-of-mental-health"],
        annotations=[
            (BQB.IS, "doid/DOID:535"),
        ],
    ),
    Choice(
        sid="central sleep apnea",
        name="central sleep apnea",
        description="Central Sleep Apnea. The periodic cessation of breathing while "
        "asleep that occurs secondary to the decreased responsiveness of "
        "the respiratory center of the brain to carbon dioxide, resulting "
        "in alternating cycles of apnea and hyperpnea.",
        parents=["sleep-disorder"],
        annotations=[
            (BQB.IS, "doid/DOID:9220"),
            (BQB.IS, "NCIT:C116046"),
        ],
    ),
    Choice(
        "hypertension",
        description="Blood pressure that is abnormally high. "
        "Persistently high systemic arterial blood pressure. Based on "
        "multiple readings, hypertension is currently defined as when "
        "systolic pressure is consistently greater than 140 mm Hg or when "
        "diastolic pressure is consistently 90 mm Hg or more ."
        "Use in addition 'blood pressure (categorical)' with choice 'elevated'. "
        "See also 'blood pressure'.",
        parents=["cardiovascular_disease"],
        annotations=[
            (BQB.IS, "doid/DOID:10763"),
            (BQB.IS, "NCIT:C3117"),
            (BQB.IS, "efo/0000537"),
        ],
        synonyms=["hypertensive"],
    ),
    Choice(
        sid="arterial-hypertension",
        name="arterial hypertension",
        description="Blood pressure that is abnormally high.",
        parents=["hypertension"],
        annotations=[],
        synonyms=[],
    ),
    Choice(
        sid="cardiomyopathy",
        description="A heart disease and a myopathy that is characterized by deterioration of the function of the "
        "heart muscle. A disease of the heart muscle or myocardium proper.",
        synonyms=[],
        parents=["heart-disease"],
        annotations=[
            (BQB.IS, "doid/DOID:0050700"),
            (BQB.IS, "NCIT:C34830"),
        ],
    ),
    Choice(
        sid="left-ventricular-dysfunction",
        name="left ventricular dysfunction",
        label="left ventricular dysfunction",
        description="Impairment of the left ventricle to "
        "either fill or eject adequately.",
        synonyms=["left ventricular impairment"],
        parents=["cardiomyopathy"],
        annotations=[
            (BQB.IS_VERSION_OF, "doid/DOID:0060480"),  # left ventricular noncompaction
            (BQB.IS, "NCIT:C50629"),
        ],
    ),
    Choice(
        sid="severe-left-ventricular-dysfunction",
        name="severe left ventricular dysfunction",
        label="severe Left ventricular dysfunction",
        description="Severe impairment of the left ventricle "
        "to either fill or eject adequately.",
        synonyms=["severe left ventricular impairment"],
        parents=["left-ventricular-dysfunction"],
        annotations=[],
    ),
    # -------------------------------------------------------------------------
    # Disease history
    # -------------------------------------------------------------------------
    MeasurementType(
        sid="family-history-disease",
        name="family history disease",
        description="Family history of disease. To encode the actual disease use "
        "'disease'.",
        parents=["health status"],
        dtype=DType.NUMERIC_CATEGORICAL,
        units=["year", NO_UNIT],
        annotations=[],
    ),
    MeasurementType(
        "family-history-diabetes",
        name="family history diabetes",
        description="Family history of diabetes.",
        parents=["family-history-disease"],
        dtype=DType.BOOLEAN,
    ),
]
