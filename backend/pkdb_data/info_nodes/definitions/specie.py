"""Definition of species and strains."""

from pymetadata.core.miriam import BQB

from ..node import Choice, DType, InfoNode, MeasurementType

SPECIE_NODES: list[InfoNode] = [
    # --- SPECIES ---
    MeasurementType(
        "species",
        description="Species. A group of organisms that differ from all other groups of "
        "organisms and that are capable of breeding and producing fertile "
        "offspring.",
        parents=["measurement"],
        dtype=DType.CATEGORICAL,
        annotations=[
            (BQB.IS, "NCIT:C45293"),
        ],
    ),
    Choice(
        sid="homo-sapiens",
        name="homo sapiens",
        label="Homo sapiens",
        description="Homo sapiens",
        parents=["species"],
        annotations=[
            (BQB.IS, "taxonomy/9606"),
            (BQB.IS, "https://bioregistry.io/VTO:0011993"),
        ],
        synonyms=["Human", "human"],
    ),
    Choice(
        sid="mus-musculus",
        name="mus musculus",
        label="Mus musculus",
        description="Mus musculus. The common house mouse, often used as an experimental "
        "organism.",
        parents=["species"],
        annotations=[
            (BQB.IS, "taxonomy/10090"),
            (BQB.IS, "https://bioregistry.io/VTO:0014661"),
            (BQB.IS, "NCIT:C45247"),
        ],
        synonyms=["Mouse", "mouse"],
    ),
    Choice(
        sid="rattus-norvegicus",
        name="rattus norvegicus",
        label="Rattus norvegicus",
        description="Rattus norvegicus",
        parents=["species"],
        annotations=[
            (BQB.IS, "taxonomy/10116"),
            (BQB.IS, "https://bioregistry.io/VTO:0014927"),
            (BQB.IS, "NCIT:C15172"),
        ],
        synonyms=["Rat", "rat"],
    ),
    Choice(
        sid="bos-taurus",
        name="bos taurus",
        label="Bos taurus",
        description="Bos taurus",
        parents=["species"],
        annotations=[
            (BQB.IS, "taxonomy/9913"),
            (BQB.IS, "https://bioregistry.io/VTO:0011065"),
        ],
    ),
    Choice(
        sid="canis-familiaris",
        name="canis familiaris",
        label="Canis familiaris",
        description="Dog.",
        parents=["species"],
        annotations=[
            (BQB.IS, "taxonomy/9615"),
            (BQB.IS, "NCIT:C14201"),
        ],
        synonyms=["Dog", "dog", "canis lupus familiaris"],
    ),
    Choice(
        sid="mongrel-dog",
        name="mongrel dog",
        label="Mongrel dog",
        description="Mongrel dog. A dog that does not belong to one officially recognized breed.",
        parents=["canis familiaris"],
        annotations=[(BQB.IS, "NCIT:C53951")],
    ),
    Choice(
        sid="swine",
        name="swine",
        label="Swine",
        description="Swine",
        parents=["species"],
        annotations=[
            (BQB.IS, "omit/0014417"),
        ],
        synonyms=["pig", "procine", "sus"],
    ),
    # --- STRAINS ---
    MeasurementType(
        "strain",
        description="Strain. An identifier of a group of animals that is genetically uniform. "
        "A population of organisms that is geneticaly different from others of the same species and possessing a set of defined characteristics.",
        parents=["measurement"],
        dtype=DType.CATEGORICAL,
        annotations=[
            (BQB.IS, "efo/0005135"),
        ],
    ),
    MeasurementType(
        sid="mouse-strain",
        name="mouse strain",
        description="Mouse strain. An identifier of a group of mice that is genetically uniform.",
        parents=["strain"],
        dtype=DType.CATEGORICAL,
        annotations=[],
    ),
    MeasurementType(
        sid="mouse-strain-c57bl",
        name="C57BL",
        description="C57BL Mouse strain. An inbred strain of mouse created in 1921 "
        "by C. C. Little at the Bussey Institute for Research in Applied Biology.",
        parents=["mouse-strain"],
        dtype=DType.CATEGORICAL,
        annotations=[(BQB.IS, "efo/0005181")],
    ),
    MeasurementType(
        sid="mouse-strain-c57bl6",
        name="C57BL6",
        description="C57BL6 Mouse strain.",
        parents=["mouse-strain-c57bl"],
        dtype=DType.CATEGORICAL,
        annotations=[],
    ),
    MeasurementType(
        sid="mouse-strain-c57bl6j",
        name="C57BL/6J",
        description="C57BL/6J Mouse strain. C57BL/6J is a mouse strain as described "
        "in Jackson Laboratory "
        "http://phenome.jax.org/db/q?rtn=strains/details&strainid=7",
        parents=["mouse-strain-c57bl6"],
        dtype=DType.CATEGORICAL,
        annotations=[(BQB.IS, "efo/0000606")],
    ),
    MeasurementType(
        sid="mouse-strain-c57bl6n",
        name="C57BL/6N",
        description="C57BL/6N Mouse strain.",
        parents=["mouse-strain-c57bl"],
        dtype=DType.CATEGORICAL,
        annotations=[],
    ),
    MeasurementType(
        sid="rat-strain",
        name="rat strain",
        description="Rat strain. An identifier of a group of rats that is genetically uniform.",
        parents=["strain"],
        dtype=DType.CATEGORICAL,
        annotations=[],
    ),
]
