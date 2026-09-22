"""Liver status for ATLAS."""

from pymetadata.core.miriam import BQB

from pkdb_data.atlas.units_atlas import (
    DIMENSIONLESS,
)
from pkdb_data.info_nodes.node import (
    Choice,
    DType,
    InfoNode,
    MeasurementType,
)

# TODO annotations
# TODO reference values?
# TODO labels
# TODO names?
# TODO synonyms

LIVER_STATUS_ATLAS_NODES: list[InfoNode] = [
    MeasurementType(
        sid="child-pugh-classification",
        description="A standardized rating scale used to assess the severity of liver cirrhosis and determine the prognosis, "
        "the required strength of treatment, and the necessity of liver transplantation. This instrument uses the "
        "following clinical and lab criteria: encephalopathy grade, ascites, bilirubin, albumin, and prothrombin index.",
        synonyms=["CPT", "Child-Pugh clinical classification"],
        dtype=DType.ABSTRACT,
        annotations=[
            (BQB.IS, "ncit/C121007"),
        ],
        parents=["liver-status"],
    ),
    MeasurementType(
        "child-pugh-grade",
        description="Child-Pugh Classification (Child-Pugh) Child-Pugh grade.",
        synonyms=["Child Turcotte Pugh Score"],
        dtype=DType.CATEGORICAL,
        annotations=[
            (BQB.IS, "ncit/C121075"),
        ],
        parents=["child-pugh-classification"],
    ),
    Choice(
        "child-pugh-class-A",
        description="Child-Pugh score indicating one-year survival of 100% in patients with chronic liver disease and cirrhosis. "
        "This score is determined by the study of the following five factors: bilirubin, albumin, international "
        "normalized ratio, presence and degree of ascites, and presence and degree of encephalopathy.",
        synonyms=["CPT A"],
        annotations=[
            (BQB.IS, "ncit/C113691"),
        ],
        parents=["child-pugh-grade"],
    ),
    Choice(
        "child-pugh-class-B",
        description="Child-Pugh score indicating one-year survival of 80% in patients with chronic liver disease and cirrhosis. "
        "This score is determined by the study of the following five factors: bilirubin, albumin, international "
        "normalized ratio, presence and degree of ascites, and presence and degree of encephalopathy.",
        synonyms=["CPT B"],
        annotations=[
            (BQB.IS, "ncit/C113692"),
        ],
        parents=["child-pugh-grade"],
    ),
    Choice(
        "child-pugh-class-C",
        description="Child-Pugh score indicating one-year survival of 45% in patients with chronic liver disease and cirrhosis. "
        "This score is determined by the study of the following five factors: bilirubin, albumin, "
        "international normalized ratio, presence and degree of ascites, and presence and degree of encephalopathy.",
        synonyms=["CPT C"],
        annotations=[
            (BQB.IS, "ncit/C113694"),
        ],
        parents=["child-pugh-grade"],
    ),
    Choice(
        "child-pugh-class-unknown",
        description="Unable to determine the Child-Pugh class.",
        annotations=[
            (BQB.IS, "ncit/C159867"),
        ],
        parents=["child-pugh-grade"],
    ),
    MeasurementType(
        sid="child-pugh-score-numeric",
        description="Child-Pugh Classification (Child-Pugh) Child-Pugh total score.",
        dtype=DType.NUMERIC,
        units=[DIMENSIONLESS],
        annotations=[
            (BQB.IS, "ncit/C121074"),
        ],
        parents=["child-pugh-classification"],
    ),
    MeasurementType(
        sid="meld-score",
        description="A scoring system of disease severity in patients with end-stage liver disease. "
        "It is used to help prioritize allocation of liver allografts for transplantation "
        "and replaces the Child-Pugh score. "
        "This instrument uses the values of serum bilirubin and creatinine, "
        "and the international normalized ratio for prothrombin time (INR) to predict "
        "survival for patients with advanced liver disease. ",
        synonyms=["Model for End-Stage Liver Disease", "MELD", "MELD score"],
        dtype=DType.NUMERIC,
        units=[DIMENSIONLESS],
        annotations=[
            (BQB.IS, "ncit/C121076"),
            (BQB.IS, "ncit/C121008"),
        ],
        parents=["liver-status"],
    ),
    MeasurementType(
        sid="portal-hypertension",
        description="Presence of portal hypertension. ",
        dtype=DType.BOOLEAN,
        parents=["liver-status"],
    ),
]
