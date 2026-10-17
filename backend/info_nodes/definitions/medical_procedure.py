"""Definition of medical procedures such as operations or medical interventions."""

from pymetadata.core.miriam import BQB

from ..node import Choice, DType, InfoNode, MeasurementType

MEDICAL_PROCEDURE_NODES: list[InfoNode] = [
    MeasurementType(
        sid="medical-procedure",
        name="medical procedure",
        description="Surgical intervention, operation or medical procedure. "
        "A medical intervention that refers to any series of pre-defined "
        "steps that should be followed to achieve a desired result.",
        parents=["measurement"],
        dtype=DType.CATEGORICAL,
        annotations=[
            (BQB.IS, "sio/SIO_001024"),
            (BQB.IS, "efo/0002571"),
        ],
    ),
    MeasurementType(
        sid="liver-operation",
        name="liver operation",
        description="Surgical intervention or operation of the liver.",
        parents=["medical procedure"],
        dtype=DType.CATEGORICAL,
        annotations=[(BQB.IS_VERSION_OF, "NCIT:C88213")],
    ),
    Choice(
        sid="cholecystectomy",
        description="Cholecystectomy. Surgical removal of the gallbladder.",
        parents=["medical procedure"],
        annotations=[
            (BQB.IS, "NCIT:C51676"),
            (BQB.IS, "omit/0004084"),
        ],
    ),
    Choice(
        sid="hepatectomy",
        description="Hepatectomy. Surgical removal of all or part of the liver.",
        parents=["liver operation"],
        annotations=[
            (BQB.IS, "NCIT:C15249"),
            (BQB.IS, "omit/0007667"),
        ],
    ),
    Choice(
        sid="spinal-anaesthesia",
        name="spinal anaesthesia",
        description="spinal anaesthesia",
        parents=["medical procedure"],
    ),
    Choice(
        sid="hemodialysis",
        description="Hemodialysis is a therapeutic procedure used in patients with "
        "kidney failure. It involves the extracorporeal removal of harmful "
        "wastes and fluids from the blood using a dialysis machine. "
        "Following the dialysis, the blood is returned to the body.",
        parents=["medical procedure"],
        annotations=[
            (BQB.IS, "NCIT:C15248"),
        ],
    ),
    Choice(
        sid="lipoprotein-apheresis",
        name="lipoprotein apheresis",
        description="Lipoprotein apheresis. An extracorporeal procedure that removes "
        "low-density lipoprotein (LDL) and lipoprotein(a) from the blood or plasma, e.g. by "
        "adsorption or precipitation, in patients with severe hypercholesterolemia such as "
        "familial hypercholesterolemia.",
        parents=["medical procedure"],
        annotations=[
            (BQB.IS, "SNOMEDCT:448955002"),
            (BQB.IS_VERSION_OF, "NCIT:C173286"),
        ],
        synonyms=["LDL apheresis", "low density lipoprotein apheresis"],
    ),
    Choice(
        sid="tubal_ligation",
        name="tubal ligation",
        label="tubal ligation (TL)",
        description="A method of female sterilization where the fallopian tubes are "
        "surgically ligated to prevent conception.",
        parents=["medical procedure"],
        annotations=[
            (BQB.IS, "NCIT:C92901"),
        ],
    ),
    Choice(
        sid="kidney-transplantation",
        name="kidney transplantation",
        description="Kidney transplantation. Surgical transfer of a kidney from a living or "
        "deceased donor to a recipient with end-stage renal disease. Encodes renal transplant "
        "recipients; see also 'time since medical procedure' and 'transplant donor'.",
        parents=["medical procedure"],
        annotations=[
            (BQB.IS, "NCIT:C15265"),
        ],
        synonyms=["renal transplantation", "kidney transplant recipient"],
    ),
    MeasurementType(
        sid="transplant-donor",
        name="transplant donor",
        description="Donor type of the transplanted organ of the subjects, e.g. a deceased or a "
        "living donor. The transplantation is encoded by a 'medical procedure' characteristic of "
        "the same subjects.",
        parents=["medical procedure"],
        dtype=DType.CATEGORICAL,
    ),
    Choice(
        sid="deceased-donor",
        name="deceased donor",
        description="The transplanted organ comes from a deceased donor.",
        parents=["transplant donor"],
        annotations=[
            (BQB.IS_VERSION_OF, "NCIT:C139270"),
        ],
        synonyms=["cadaveric donor"],
    ),
    Choice(
        sid="living-donor",
        name="living donor",
        description="The transplanted organ comes from a living donor.",
        parents=["transplant donor"],
    ),
    Choice(
        sid="roux-en-y-gastric-bypass",
        name="roux-en-y gastric bypass",
        label="Roux-en-Y gastric bypass",
        description="Roux-en-Y gastric bypass, a bariatric operation that creates a small gastric "
        "pouch connected to a Roux limb of the jejunum, bypassing the distal stomach, the "
        "duodenum and the proximal jejunum.",
        parents=["medical procedure"],
        annotations=[
            (BQB.IS_VERSION_OF, "NCIT:C51758"),
        ],
        synonyms=["RYGB", "gastric bypass"],
    ),
    Choice(
        sid="liver-biopsy",
        name="liver biopsy",
        description="Liver biopsy. Removal of a sample of liver tissue for histological "
        "examination.",
        parents=["medical procedure"],
        annotations=[
            (BQB.IS, "NCIT:C51677"),
        ],
    ),
    MeasurementType(
        sid="time-since-medical-procedure",
        name="time since medical procedure",
        description="Time since the medical procedure of the subjects, such as the time since "
        "kidney transplantation or since a gastric bypass. The procedure is encoded by a "
        "'medical procedure' characteristic of the same subjects.",
        parents=["health status"],
        dtype=DType.NUMERIC,
        units=["year"],
        synonyms=["time since transplantation", "posttransplant interval"],
    ),
]
