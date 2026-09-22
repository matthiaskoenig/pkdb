"""Laboratory diagnostics for ATLAS."""

from pymetadata.core.miriam import BQB

from pkdb_data.atlas.units_atlas import (
    CLEARANCE_UNITS,
    CONCENTRATION_UNITS,
    DIMENSIONLESS,
    RATIO_UNITS,
    TIME_UNITS,
)
from pkdb_data.info_nodes.node import (
    DType,
    InfoNode,
    MeasurementType,
)

# TODO annotations
# TODO reference values?
# TODO labels
# TODO names?
# TODO synonyms

LAB_DIAGN_ATLAS_NODES: list[InfoNode] = [
    MeasurementType(
        sid="comprehensive-metabolic-panel",
        label="Comprehensive Metabolic Panel",
        description="A broad screening tool that measures glucose, electrolytes "
        "and metabolites in blood serum to evaluate organ function and "
        "check for conditions such as diabetes, liver disease, and kidney "
        "disease.",
        synonyms=["Comprehensive Metabolic Panel"],
        dtype=DType.ABSTRACT,
        annotations=[
            (BQB.IS, "ncit/C137828"),
        ],
        parents=["laboratory-diagnostics"],
    ),
    MeasurementType(
        sid="serum-creatinine-measurement",
        label="Creatinine",
        description="A quantitative measurement of the amount "
        "of creatinine present in a sample of serum.",
        synonyms=["Creatinine"],
        dtype=DType.NUMERIC,
        units=CONCENTRATION_UNITS,
        annotations=[
            (BQB.IS, "chebi/CHEBI:16737"),
            (BQB.IS, "ncit/C61023"),
        ],
        parents=["comprehensive-metabolic-panel"],
    ),
    MeasurementType(
        sid="plasma-glucose-measurement",
        label="Glucose",
        description="The determination of the amount of glucose present in plasma.",
        synonyms=["D-glucopyranose"],
        dtype=DType.NUMERIC,
        units=CONCENTRATION_UNITS,
        annotations=[
            (BQB.IS, "chebi/CHEBI:4167"),
            (BQB.IS, "ncit/C41376"),
        ],
        parents=["comprehensive-metabolic-panel"],
    ),
    MeasurementType(
        sid="serum-albumin-measurement",
        label="Albumin",
        description="A quantitative measurement of albumin "
        "present in a sample of serum. ",
        synonyms=["Albumin"],
        dtype=DType.NUMERIC,
        units=CONCENTRATION_UNITS,
        annotations=[
            (BQB.IS, "chebi/CHEBI:166964"),
            (BQB.IS, "ncit/C61015"),
        ],
        parents=["comprehensive-metabolic-panel", "liver-status"],
    ),
    MeasurementType(
        sid="serum-bilirubin-measurement",
        label="Bilirubin",
        description="The substrate most often tested is blood, but other "
        "fluids extracted from the body may be used periodically "
        "depending on the purpose of the test.",
        synonyms=[],
        dtype=DType.ABSTRACT,
        parents=["comprehensive-metabolic-panel", "liver-status"],
    ),
    MeasurementType(
        sid="serum-bilirubin-measurement-total",
        label="Bilirubin, Total",
        description="A quantitative measurement of the total amount "
        "of bilirubin present in a sample of serum. ",
        synonyms=["Total Bilirubin"],
        dtype=DType.NUMERIC,
        units=CONCENTRATION_UNITS,
        annotations=[
            # (BQB.IS, "chebi/CHEBI:16990"),
            (BQB.IS, "ncit/C61031"),
            # (BQB.IS, "inchikey/BPYKTIZUTYGOLE-IFADSCNNSA-N"),
        ],
        parents=["serum-bilirubin-measurement"],
    ),
    MeasurementType(
        sid="serum-bilirubin-measurement-indirect",
        label="Bilirubin, Unconjugated",
        description="A quantitative measurement of the amount of "
        "indirect bilirubin present in a sample of serum. ",
        synonyms=["Indirect Bilirubin"],
        dtype=DType.NUMERIC,
        units=CONCENTRATION_UNITS,
        annotations=[
            # (BQB.IS_VERSION_OF, "chebi/CHEBI:16990"),
            (BQB.IS_VERSION_OF, "ncit/C64483"),
            # (BQB.IS_VERSION_OF, "inchikey/BPYKTIZUTYGOLE-IFADSCNNSA-N"),
        ],
        parents=["serum-bilirubin-measurement"],
    ),
    MeasurementType(
        sid="serum-bilirubin-measurement-direct",
        label="Bilirubin, Conjugated",
        description="A quantitative measurement of the amount of conjugated "
        "or water-soluble bilirubin present in a sample of serum. ",
        synonyms=["Direct Bilirubin"],
        dtype=DType.NUMERIC,
        units=CONCENTRATION_UNITS,
        annotations=[
            # (BQB.IS_VERSION_OF, "chebi/CHEBI:16990"),
            (BQB.IS_VERSION_OF, "ncit/C61024"),
            # (BQB.IS_VERSION_OF, "inchikey/BPYKTIZUTYGOLE-IFADSCNNSA-N"),
        ],
        parents=["serum-bilirubin-measurement"],
    ),
    MeasurementType(
        sid="serum-alp-measurement",
        label="Alkaline Phosphatase",
        description="A quantitative measurement of the amount of "
        "alkaline phosphatase present in a sample of serum. ",
        synonyms=["Afos", "Alkaline phosphatase", "ALP"],
        dtype=DType.NUMERIC,
        units=CONCENTRATION_UNITS,
        annotations=[
            (BQB.IS, "ncit/C61016"),
        ],
        parents=["comprehensive-metabolic-panel", "liver-status"],
    ),
    MeasurementType(
        sid="serum-alt-measurement",
        label="ALT",
        description="A quantitative measurement of the amount of alanine "
        "aminotransferase present in a sample of serum. ",
        synonyms=["Alanine Aminotransferase", "ALT"],
        dtype=DType.NUMERIC,
        units=CONCENTRATION_UNITS,
        annotations=[
            (BQB.IS, "ncit/C61017"),
        ],
        parents=["comprehensive-metabolic-panel", "liver-status"],
    ),
    MeasurementType(
        sid="serum-ast-measurement",
        label="AST",
        description="A quantitative measurement of the amount of aspartate "
        "aminotransferase present in a sample of serum. ",
        synonyms=["Aspartate Aminotransferase", "AST"],
        dtype=DType.NUMERIC,
        units=CONCENTRATION_UNITS,
        annotations=[
            (BQB.IS, "ncit/C61018"),
        ],
        parents=["comprehensive-metabolic-panel", "liver-status"],
    ),
    MeasurementType(
        sid="c-reactive-protein-measurement",
        label="C Reactive Protein",
        description="A quantitative measurement of the amount of "
        "C-reactive protein present in a sample.",
        synonyms=["CRP"],
        dtype=DType.NUMERIC,
        units=CONCENTRATION_UNITS,
        annotations=[
            (BQB.IS, "ncit/C64548"),
        ],
        parents=["comprehensive-metabolic-panel"],
    ),
    MeasurementType(
        sid="serum-gamma-globulin-measurement",
        label="Gamma Globulin",
        description="Measurement of gamma-globulins in a sample of serum. ",
        synonyms=["Gamma-globulin", "Gamma globulin"],
        dtype=DType.NUMERIC,
        units=CONCENTRATION_UNITS,
        annotations=[
            # (BQB.IS_VERSION_OF, "snomed/116648000"),
            (BQB.IS_VERSION_OF, "ncit/C92257"),
        ],
        parents=["comprehensive-metabolic-panel", "liver-status"],
    ),
    MeasurementType(
        sid="blood-cell-count",
        label="Blood Cell Count",
        description="The determination of the number of red blood cells, "
        "white blood cells, and platelets in a biospecimen. ",
        synonyms=[],
        dtype=DType.ABSTRACT,
        annotations=[
            (BQB.IS_VERSION_OF, "ncit/C28133"),
        ],
        parents=["laboratory-diagnostics"],
    ),
    MeasurementType(
        "hematocrit-measurement",
        label="Hematocrit",
        description="A measure of the volume of red blood cells expressed "
        "as a ratio to the total blood volume. ",
        synonyms=["Hematocrit"],
        dtype=DType.NUMERIC,
        units=RATIO_UNITS,
        annotations=[
            (BQB.IS_VERSION_OF, "ncit/C64796"),
        ],
        parents=["blood-cell-count"],
    ),
    MeasurementType(
        sid="glomular-filtration-rate",
        label="GFR",
        description="A kidney function test that measures the fluid volume "
        "that is filtered from the kidney glomeruli to the Bowman's "
        "capsule per unit of time.",
        synonyms=["Glomerular filtration rate"],
        dtype=DType.ABSTRACT,
        annotations=[
            (BQB.IS, "ncit/C90505"),
        ],
        parents=["laboratory-diagnostics"],
    ),
    MeasurementType(
        sid="estimated-creatinine-clearance",
        label="Creatinine Clearance",
        description="An estimate of the clearance of endogenous creatinine, "
        "used for evaluating the glomerular filtration rate. ",
        synonyms=["Estimated creatinine clearance", "Creatinine clearance", "eGFR"],
        dtype=DType.NUMERIC,
        units=CLEARANCE_UNITS,
        annotations=[
            (BQB.IS, "ncit/C150847"),
            (BQB.IS, "ncit/C25747"),
        ],
        parents=["glomular-filtration-rate", "clearance-renal"],
    ),
    # coagulation measurements
    MeasurementType(
        "coagulation-study",
        label="Coagulation study",
        description="Coagulation study.",
        synonyms=["Coagulation study"],
        dtype=DType.ABSTRACT,
        annotations=[
            # (BQB.IS, "cmo/CMO:0000211"),
            (BQB.IS, "ncit/C62662"),
        ],
        parents=["laboratory-diagnostics"],
    ),
    MeasurementType(
        "prothrombin-time",
        label="Prothrombin Time",
        description="A measurement of the clotting time of plasma recalcified in the "
        "presence of excess tissue thromboplastin. It is a measure of the "
        "extrinsic pathway of coagulation. It is used to determine the "
        "clotting tendency of blood, in the measure of warfarin dosage, "
        "liver damage and vitamin K status. Factors measured are "
        "fibrinogen, prothrombin, and factors V, VII, and X.",
        synonyms=["Prothrombin time"],
        dtype=DType.NUMERIC,
        units=TIME_UNITS,
        annotations=[
            # (BQB.IS, "cmo/CMO:0000211"),
            (BQB.IS, "ncit/C62656"),
        ],
        parents=["coagulation-study", "liver-status"],
    ),
    MeasurementType(
        sid="inr-prothrombin-time",
        label="INR",
        description="A measure of the extrinsic pathway of coagulation. "
        "The International Normalized Ratio of Prothrombin Time (INR) "
        "is the ratio of a patient prothrombin time to a normal (control) "
        "sample raised to the power of the International Sensitivity Index "
        "(ISI) with a range of 0.8 to 1.2 seconds.",
        synonyms=["INR", "International normalized ratio of prothrombin time"],
        dtype=DType.NUMERIC,
        units=[DIMENSIONLESS],
        annotations=[
            (BQB.IS_VERSION_OF, "ncit/C64805"),
        ],
        parents=["prothrombin-time"],
    ),
    # MeasurementType(
    #     sid="prothrombin-time-ratio",
    #     name="prothrombin time ratio",
    #     description="Prothrombin time ratio. Measurement of the clotting ability of "
    #                 "fibrinogen, prothrombin, proaccelerin, proconvertin and Stuart "
    #                 "factor, usually given in seconds to formation of clot after the "
    #                 "addition of a tissue factor or thromboplastin.",
    #     parents=["liver function test"],
    #     dtype=DType.NUMERIC,
    #     units=[DIMENSIONLESS],
    #     annotations=[
    #         (BQB.IS_VERSION_OF, "cmo/CMO:0000211"),
    #         (BQB.IS_VERSION_OF, "ncit/C62656"),
    #     ],
    # ),
    # MeasurementType(
    #     sid="plasma-thromboplastin-activity",
    #     name="plasma thromboplastin activity",
    #     description="Plasma thromboplastin activity. A test for the functional "
    #                 "intactness of the prothrombin complex that is used in "
    #                 "controlling the amount of anticoagulant used in preventing thrombosis",
    #     parents=["liver function test"],
    #     synonyms=["Thrombotest"],
    #     dtype=DType.NUMERIC,
    #     units=[DIMENSIONLESS],
    #     annotations=[],
    # ),
    MeasurementType(
        sid="laboratory-blood-measurement-other",
        label="Blood measurement Other",
        description="",
        synonyms=[],
        dtype=DType.ABSTRACT,
        parents=["laboratory-diagnostics"],
    ),
    MeasurementType(
        sid="serum-lactic-acid-measurement",
        label="Lactic Acid",
        description="The determination of the amount of lactic acid present in a sample of serum. ",
        synonyms=["Lactic acid"],
        dtype=DType.NUMERIC,
        units=CONCENTRATION_UNITS,
        annotations=[
            #  (BQB.IS, "chebi/CHEBI:24996"),
            (BQB.IS, "ncit/C79450"),
        ],
        parents=["laboratory-blood-measurement-other", "liver-status"],
    ),
    MeasurementType(
        sid="serum-ldh-measurement",
        description="A quantitative measurement of the amount of lactate dehydrogenase present in a sample of serum. ",
        synonyms=["LDH", "Lactate dehydrogenase"],
        dtype=DType.NUMERIC,
        units=CONCENTRATION_UNITS,
        annotations=[
            (BQB.IS, "ncit/C61026"),
        ],
        parents=["laboratory-blood-measurement-other", "liver-status"],
    ),
    MeasurementType(
        sid="serum-bile-acids-measurement",
        description="The determination of the amount of bile acids present in a sample of serum. ",
        synonyms=["BA", "Bile acids"],
        dtype=DType.NUMERIC,
        units=CONCENTRATION_UNITS,
        annotations=[
            (BQB.IS, "ncit/C74800"),
        ],
        parents=["laboratory-blood-measurement-other", "liver-status"],
    ),
]
