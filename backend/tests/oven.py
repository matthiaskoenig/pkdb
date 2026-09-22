"""Test module for substance xrefs."""

from pymetadata.core.miriam import BQB

from pkdb_data.info_nodes.node import Substance

substance = Substance(
    sid="sorbitol",
    name="sorbitol",
    description="A sugar alcohol found in fruits and plants with diuretic, laxative and cathartic property. "
    "Unabsorbed sorbitol retains water in the large intestine through osmotic pressure thereby "
    "stimulating peristalsis of the intestine and exerting its diuretic, laxative and cathartic "
    "effect. ",
    annotations=[
        (BQB.IS, "chebi/CHEBI:30911"),
        (BQB.IS, "ncit/C29462"),
    ],
)


if __name__ == "__main__":
    substance.query_metadata()

    print(substance)
    print(substance.xrefs)
