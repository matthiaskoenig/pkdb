"""HCC nodes for ATLAS."""

from pymetadata.core.miriam import BQB

from pkdb_data.info_nodes.node import Choice, DType, InfoNode, MeasurementType

# TODO names?
# TODO synonyms

HCC_ATLAS_NODES: list[InfoNode] = [
    MeasurementType(
        sid="tnm-classification",
        label="TNM Classification",
        description="One of a systems for clinicopathologic evaluation of tumors. ",
        synonyms=["TNM", "TNM staging system", "TNM staging"],
        dtype=DType.ABSTRACT,
        annotations=[
            (BQB.IS, "ncit/C25384"),
            (BQB.IS, "snomed/254293002"),  # general TNM
            (BQB.IS, "snomed/254312005"),  # liver tumor TNM
        ],
        parents=["hcc"],
    ),
    MeasurementType(
        sid="T",
        label="Primary Tumor Characteristics",
        description="Size of the tumor and whether it has invaded nearby tissue. ",
        synonyms=[],
        dtype=DType.CATEGORICAL,
        annotations=[],
        parents=["tnm-classification"],
    ),
    Choice(
        sid="TX",
        label="TX",
        description="Primary tumor cannot be assessed. ",
        synonyms=[],
        annotations=[],
        parents=["T"],
    ),
    Choice(
        sid="T0",
        label="T0",
        description="No evidence of primary tumor. ",
        synonyms=[],
        annotations=[],
        parents=["T"],
    ),
    MeasurementType(
        sid="T1",
        label="T1",
        description="Solitary tumor < 2 cm, or >2 cm without vascular invasion. ",
        synonyms=[],
        dtype=DType.CATEGORICAL,
        annotations=[],
        parents=["T"],
    ),
    Choice(
        sid="T1a",
        label="T1a",
        description="Solitary tumor <= 2 cm. ",
        synonyms=[],
        annotations=[],
        parents=["T1"],
    ),
    Choice(
        sid="T1b",
        label="T1b",
        description="Solitary tumor > 2 cm without vascular invasion. ",
        synonyms=[],
        annotations=[],
        parents=["T1"],
    ),
    Choice(
        sid="T2",
        label="T2",
        description="Solitary tumor > 2 cm with vascular invasion,"
        " or multiple tumors, none > 5 cm. ",
        synonyms=[],
        annotations=[],
        parents=["T"],
    ),
    Choice(
        sid="T3",
        label="T3",
        description="Multiple tumors, at least one of which is > 5 cm. ",
        synonyms=[],
        annotations=[],
        parents=["T"],
    ),
    Choice(
        sid="T4",
        label="T4",
        description="Single tumor or tumors of any size involving a major branch "
        "of the portal vein or hepatic vein, or tumor(s) with direct "
        "invasion of adjacent organs other than the gallbladder or "
        "with perforation of visceral peritoneum. ",
        synonyms=[],
        annotations=[],
        parents=["T"],
    ),
    MeasurementType(
        sid="N",
        label="Lymph Nodes Involvement",
        description="Regional lymph nodes involvement. ",
        synonyms=[],
        dtype=DType.CATEGORICAL,
        annotations=[],
        parents=["tnm-classification"],
    ),
    Choice(
        sid="NX",
        label="NX",
        description="Regional lymph nodes cannot be assessed. ",
        synonyms=[],
        annotations=[],
        parents=["N"],
    ),
    Choice(
        sid="N0",
        label="N0",
        description="No regional lymph node metastasis. ",
        synonyms=[],
        annotations=[],
        parents=["N"],
    ),
    Choice(
        sid="N1",
        label="N1",
        description="Regional lymph node metastasis. ",
        synonyms=[],
        annotations=[],
        parents=["N"],
    ),
    MeasurementType(
        sid="M",
        label="Metastasis Presence",
        description="Presence of distant metastasis. ",
        synonyms=[],
        dtype=DType.CATEGORICAL,
        annotations=[],
        parents=["tnm-classification"],
    ),
    Choice(
        sid="M0",
        label="M0",
        description="No distant metastasis. ",
        synonyms=[],
        annotations=[],
    ),
    Choice(
        sid="M1",
        label="M1",
        description="Distant metastasis. ",
        synonyms=[],
        annotations=[],
        parents=["M"],
    ),
    MeasurementType(
        sid="bclc-score",
        label="Barcelona-Clinic Liver Cancer Staging System",
        description="A staging classification system for hepatocellular carcinoma "
        "that uses variables related to tumor stage, liver functional "
        "status, physical status, and cancer-related symptoms, and links "
        "the stages with a treatment algorithm. ",
        synonyms=["BCLC", "BCLC Staging", "Barcelona Clinic Liver Cancer Stage"],
        dtype=DType.CATEGORICAL,
        annotations=[
            (BQB.IS, "ncit/C115132"),
        ],
        parents=["hcc", "liver-status", "ecog-performance-status"],
    ),
    Choice(
        sid="bclc-stage-0",
        label="BCLC Stage 0 Hepatocellular Carcinoma",
        description="PS0 + Child-Pugh A + tumor <2cm (T1a?): very early "
        "hepatocellular carcinoma. Patients are optimal "
        "candidates for resection. ",
        synonyms=["BCLC 0"],
        annotations=[
            (BQB.IS, "ncit/C115133"),
        ],
        parents=["bclc-score"],
    ),
    Choice(
        sid="bclc-stage-a",
        label="BCLC Stage A Hepatocellular Carcinoma",
        description="PS0 + Child-Pugh A/B + single tumor <5cm or up to "
        "3 tumors all <3 cm: early hepatocellular carcinoma. "
        "Patients are candidates for radical therapies "
        "(resection, liver transplantation, or percutaneous treatments). ",
        synonyms=["BCLC A"],
        annotations=[
            (BQB.IS, "ncit/C115135"),
        ],
        parents=["bclc-score"],
    ),
    Choice(
        sid="bclc-stage-b",
        label="BCLC Stage B Hepatocellular Carcinoma",
        description="PS0 + Child-Pugh A/B + multiple tumors: early hepatocellular "
        "carcinoma. Patients are candidates for radical therapies "
        "(resection, liver transplantation, or percutaneous treatments). ",
        synonyms=["BCLC B"],
        annotations=[
            (BQB.IS, "ncit/C115135"),
        ],
        parents=["bclc-score"],
    ),
    Choice(
        sid="bclc-stage-c",
        label="BCLC Stage C Hepatocellular Carcinoma",
        description="PS1-2 + Child-Pugh A/B + portal invasion, lymph nodes or "
        "M1: advanced hepatocellular carcinoma. Patients may receive "
        "new agents in the setting of randomized controlled trials. ",
        synonyms=["BCLC C"],
        annotations=[
            (BQB.IS, "ncit/C115137"),
        ],
        parents=["bclc-score"],
    ),
    Choice(
        sid="bclc-stage-d",
        label="BCLC Stage D Hepatocellular Carcinoma",
        description="PS3-4 or Child-Pugh C: end-stage hepatocellular carcinoma. "
        "Patients will receive symptomatic treatment. ",
        synonyms=["BCLC D"],
        annotations=[
            (BQB.IS, "ncit/C115138"),
        ],
        parents=["bclc-score"],
    ),
]
