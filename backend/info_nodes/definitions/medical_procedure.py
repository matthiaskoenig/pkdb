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
]
