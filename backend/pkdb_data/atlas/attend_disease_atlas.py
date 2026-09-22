"""Disease nodes for ATLAS."""

from pymetadata.core.miriam import BQB

from pkdb_data.info_nodes.node import (
    Choice,
    DType,
    InfoNode,
    MeasurementType,
)

# TODO names?
# TODO synonyms

ATTEND_DISEASE_ATLAS_NODES: list[InfoNode] = [
    Choice(
        sid="diabetes-mellitus",
        label="Diabetes Mellitus",
        description="Diabetes is a metabolic disorder characterized by abnormally high "
        "blood sugar levels due to diminished production of insulin or "
        "insulin resistance/desensitization.",
        dtype=DType.ABSTRACT,
        synonyms=["DM"],
        annotations=[
            (BQB.IS, "ncit/C2985"),
            (BQB.IS, "doid/9351"),
        ],
        parents=["attendant-disease"],
    ),
    Choice(
        sid="type-1-diabetes-mellitus",
        label="Type 1 Diabetes Mellitus",
        description="A chronic condition characterized by minimal or "
        "absent production of insulin by the pancreas. ",
        annotations=[
            (BQB.IS, "ncit/C2986"),
            (BQB.IS, "doid/9744"),
        ],
        parents=["diabetes-mellitus"],
    ),
    Choice(
        sid="type-2-diabetes-mellitus",
        label="Type 2 Diabetes Mellitus",
        description="Diabetes mellitus type 2. A type of diabetes mellitus "
        "that is characterized by insulin resistance or "
        "desensitization and increased blood glucose levels. "
        "This is a chronic disease that can develop gradually "
        "over the life of a patient and can be linked to both "
        "environmental factors and heredity.",
        annotations=[
            (BQB.IS, "ncit/C26747"),
            (BQB.IS, "doid/9352"),
        ],
        parents=["diabetes-mellitus"],
    ),
    MeasurementType(
        sid="liver-and-intrahepatic-bile-duct-disease",
        label="Liver and Intrahepatic Bile Duct Disease",
        description="A non-neoplastic or neoplastic disorder that affects "
        "the liver parenchyma and intrahepatic bile ducts. ",
        dtype=DType.ABSTRACT,
        annotations=[
            (BQB.IS, "ncit/C3196"),  # Liver and Intrahepatic Bile Duct Disorder
            (BQB.IS, "doid/409"),  # Liver disease
        ],
        parents=["attendant-disease", "liver-status"],
    ),
    Choice(
        sid="hepatitis",
        label="Hepatitis",
        description="Inflammation of the liver, usually from a viral "
        "infection, but sometimes from toxic agents.",
        annotations=[
            (BQB.IS, "ncit/C3095"),
            (BQB.IS, "doid/2237"),
        ],
        parents=["liver-and-intrahepatic-bile-duct-disease"],
    ),
    Choice(
        sid="alcoholic-hepatitis",
        label="Alcoholic Hepatitis",
        description="Inflammation of the liver resulting from ingestion of alcohol.",
        parents=["hepatitis"],
        annotations=[
            (BQB.IS, "ncit/C34684"),
            (BQB.IS, "doid/12351"),
        ],
    ),
    # Choice(
    #     sid="drug-induced-hepatitis",
    #     description="Drug-induced hepatitis.",
    #     parents=["hepatitis"],
    #     annotations=[
    #         (BQB.IS, "ncit/C34684"),
    #        # (BQB.IS, "doid/2044"),
    #     ],
    # ),
    # Choice(
    #     sid="chronic-hepatitis",
    #     name="chronic hepatitis",
    #     description="An active inflammatory process affecting the liver for more than "
    #     "six months. Causes include viral infections, autoimmune "
    #     "disorders, drugs, and metabolic disorders.",
    #     parents=["hepatitis"],
    #     annotations=[
    #         (BQB.IS, "ncit/C82978"),
    #         (BQB.IS, "efo/0008496"),
    #     ],
    # ),
    # Choice(
    #     sid="toxic-hepatitis",
    #     name="toxic hepatitis",
    #     description="Toxic hepatitis",
    #     parents=["hepatitis"],
    #     annotations=[(BQB.IS, "snomed/197352008")],
    # ),
    Choice(
        sid="viral-hepatitis",
        label="Viral Hepatitis",
        description="An acute or chronic inflammation of the liver parenchyma "
        "caused by viruses. Representative examples include hepatitis "
        "A, B, and C, cytomegalovirus hepatitis, and herpes simplex "
        "hepatitis.",
        annotations=[
            (BQB.IS, "ncit/C35124"),
            (BQB.IS, "doid/1844"),
        ],
        parents=["hepatitis"],
    ),
    Choice(
        sid="hepatitis-b-infection",
        label="Hepatitis B",
        description="A viral infection caused by the hepatitis B virus. ",
        synonyms=["HBV", "Hepatitis B"],
        annotations=[
            (BQB.IS, "ncit/C3097"),
            (BQB.IS, "doid/2043"),
        ],
        parents=["viral-hepatitis"],
    ),
    Choice(
        sid="hepatitis-c-infection",
        label="Hepatitis C",
        description="A viral infection caused by the hepatitis C virus. ",
        synonyms=["HCV", "Hepatitis C"],
        annotations=[
            (BQB.IS_VERSION_OF, "ncit/C3098"),
            (BQB.IS_VERSION_OF, "doid/1883"),
        ],
        parents=["viral-hepatitis"],
    ),
    MeasurementType(
        sid="nutrition-disorder",
        label="Nutrition Disease",
        description="Any condition related to a disturbance between "
        "proper intake and utilization of nourishment.",
        dtype=DType.ABSTRACT,
        annotations=[
            (BQB.IS_VERSION_OF, "ncit/C26836"),
            (BQB.IS_VERSION_OF, "doid/374"),
        ],
        parents=["attendant-disease"],
    ),
]
