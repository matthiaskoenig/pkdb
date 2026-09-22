"""Definition of ethnicities."""

from pymetadata.core.miriam import BQB

from ..node import Choice, DType, InfoNode, MeasurementType

ETHNICITY_NODES: list[InfoNode] = [
    MeasurementType(
        sid="ethnicity",
        description="Ethnicity is the biological quality of membership in a social group "
        "based on a common heritage.",
        parents=["homo sapiens"],
        dtype=DType.CATEGORICAL,
        annotations=[(BQB.IS, "sio/SIO_001014"), (BQB.IS, "efo/0001799")],
        synonyms=["race"],
    ),
    Choice(
        sid="african",
        label="African",
        description="African denotes a person with ancestral origins are in any of "
        "the countries of Africa.",
        parents=["ethnicity"],
        annotations=[
            (BQB.IS, "NCIT:C42331"),
            (BQB.IS, "efo/0004561"),
        ],
    ),
    Choice(
        sid="african-american",
        name="african american",
        label="African American",
        description="African American denotes a person of African ancestral origins whose "
        "family settled in America.",
        parents=["ethnicity"],
        annotations=[(BQB.IS, "NCIT:C128937")],
    ),
    Choice(
        sid="arab-american",
        name="arab american",
        label="Arab American",
        description="Arab American denotes a person of Arab ancestral origins whose "
        "family settled in America.",
        parents=["ethnicity"],
    ),
    Choice(
        sid="american-indian",
        name="american indian",
        label="American Indian",
        description="American Indian denotes a person having origins in one of the "
        "indigenous peoples of North America, who lived on the continent prior "
        "to the European colonization. The term includes individuals belonging "
        "to a large number of tribes, states, and ethnic groups, many of them "
        "still enduring as communities.",
        parents=["ethnicity"],
        annotations=[(BQB.IS, "NCIT:C43877")],
    ),
    Choice(
        sid="asian",
        name="asian",
        label="Asian",
        description="Asian. A person having origins in any of the original peoples of the "
        "Far East, Southeast Asia, or the Indian subcontinent, including for "
        "example, Cambodia, China, India, Japan, Korea, Malaysia, Pakistan, "
        "the Philippine Islands, Thailand, and Vietnam.",
        parents=["ethnicity"],
        annotations=[
            (BQB.IS, "NCIT:C41260"),
        ],
    ),
    Choice(
        sid="korean",
        name="korean",
        label="Korean",
        description="Korean. A person having origins in any of the original peoples of "
        "Korea.",
        parents=["asian"],
        annotations=[
            (BQB.IS, "NCIT:C43395"),
        ],
    ),
    Choice(
        sid="chinese",
        name="chinese",
        label="Chinese",
        description="Chinese. A person having origins in any of the original peoples of China.",
        parents=["asian"],
        annotations=[
            (BQB.IS, "NCIT:C43391"),
        ],
    ),
    Choice(
        sid="japanese",
        name="japanese",
        label="Japanese",
        description="A person having origins in any of the original peoples of Japan.",
        parents=["asian"],
        annotations=[
            (BQB.IS, "NCIT:C43392"),
        ],
    ),
    Choice(
        sid="thai",
        name="thai",
        label="Thai",
        description="Denotes the inhabitants of Thailand, a person from there, or their descendants elsewhere.",
        parents=["asian"],
        annotations=[
            (BQB.IS, "NCIT:C43400"),
        ],
    ),
    Choice(
        sid="caucasian",
        name="caucasian",
        label="Caucasian",
        description="Caucasian. An ethnic group comprised of persons having origins in any "
        "of the original peoples of Europe, the Middle East, or North Africa.",
        parents=["ethnicity"],
        annotations=[
            (BQB.IS, "efo/0003156"),
        ],
        synonyms=["white"],
    ),
    Choice(
        sid="finish",
        name="finish",
        label="Finish",
        description="Finish. A person having origins in any of the original peoples of Finnland.",
        parents=["caucasian"],
        annotations=[
            (BQB.IS, "NCIT:C64943"),
        ],
    ),
    Choice(
        sid="hispanic",
        name="hispanic",
        label="Hispanic",
        description="Hispanic or Latino. A person of Cuban, Mexican, "
        "Puerto Rican, South or Central American, or other Spanish culture or "
        "origin, regardless of race. The term, 'Spanish origin', can be used "
        "in addition to 'Hispanic or Latino'.",
        parents=["ethnicity"],
        annotations=[
            (BQB.IS_VERSION_OF, "NCIT:C17459"),
        ],
    ),
    Choice(
        sid="non-hispanic",
        name="non-hispanic",
        label="Non-Hispanic",
        description="Not Hispanic or Latino.",
        parents=["ethnicity"],
        annotations=[],
    ),
    Choice(
        sid="mixed-race",
        name="mixed race",
        label="Mixed race",
        description="Mixed race origin.",
        parents=["ethnicity"],
        annotations=[
            (BQB.IS, "efo/0003156"),
        ],
        synonyms=["white"],
    ),
    Choice(
        sid="white-new-zealanders",
        name="white new zealanders",
        label="White New Zealanders",
        description="A collection of ethnic geographical categories including "
        "Australian and New Zealander.",
        parents=["ethnicity"],
        annotations=[
            (BQB.IS_VERSION_OF, "NCIT:C128458"),
        ],
    ),
    Choice(
        sid="asian indian",
        name="asian indian",
        label="Asian Indian",
        description="A person having origins in the original peoples of the Indian sub-continent.",
        parents=["ethnicity"],
        annotations=[
            (BQB.IS_VERSION_OF, "NCIT:C41262"),
        ],
    ),
    Choice(
        sid="egyptian",
        name="egyptian",
        label="Egyptian",
        description="Denotes the inhabitants of Egypt, a person from there, or their descendants elsewhere.",
        parents=["ethnicity"],
        annotations=[
            (BQB.IS_VERSION_OF, "NCIT:C43868"),
        ],
    ),
    Choice(
        sid="jordanian",
        name="jordanian",
        label="Jordanian",
        description="Denotes the inhabitants of Jordan, a person from there, or their descendants elsewhere.",
        parents=["ethnicity"],
        annotations=[],
    ),
    Choice(
        sid="swedish",
        name="swedish",
        label="Swedish",
        description="Denotes the inhabitants of Sweden, a person from there, or their descendants elsewhere.",
        parents=["ethnicity"],
        annotations=[
            (BQB.IS_VERSION_OF, "NCIT:C43861"),
        ],
    ),
    Choice(
        sid="spanish",
        name="spanish",
        label="Spanish",
        description="Denotes the inhabitants of Spain, a person from there, or their descendants elsewhere.",
        parents=["ethnicity"],
        annotations=[
            (BQB.IS_VERSION_OF, "NCIT:C67120"),
        ],
    ),
    Choice(
        sid="afro-trinidadians",
        name="afro trinidadians",
        label="Afro–Trinidadians",
        description="A person having origins in the original peoples of the Indian sub-continent. ",
        parents=["ethnicity"],
        annotations=[],
    ),
    Choice(
        sid="indo-trinidadians",
        name="indo trinidadians",
        label="Indo-Trinidadians",
        description="A person of Indian origin who are nationals of Trinidad and Tobago "
        "whose ancestors came from India and the wider subcontinent beginning in 1845.",
        parents=["ethnicity"],
        annotations=[],
    ),
    Choice(
        sid="black",
        name="black",
        label="Black",
        description="A person having origins in the original peoples of sub-Saharan Africa or the Caribbean.",
        parents=["ethnicity"],
        annotations=[
            (BQB.IS_VERSION_OF, "NCIT:C128938"),
        ],
    ),
    Choice(
        sid="pacific-islander",
        name="pacific islander",
        label="Pacific Islander",
        description="A person having origins in the original peoples of Pacific Islander.",
        parents=["ethnicity"],
        annotations=[
            # (BQB.IS_VERSION_OF, "exo/0000154"),
        ],
    ),
    Choice(
        sid="indian",
        name="indian",
        label="Indian",
        description="A person having origins in India.",
        parents=["ethnicity"],
        annotations=[],
    ),
    Choice(
        sid="mexican",
        name="mexican",
        label="Mexican",
        description="A person having origins in Mexico.",
        parents=["ethnicity"],
        annotations=[],
    ),
    Choice(
        sid="west_asian",
        name="west asian",
        label="West Asian",
        description="A person having origins in West Asia.",
        parents=["ethnicity"],
        annotations=[],
    ),
    Choice(
        sid="taiwanese",
        name="taiwanese",
        label="Taiwanese",
        description="A person having origins in Taiwan.",
        parents=["ethnicity"],
        annotations=[],
    ),
    Choice(
        sid="hongkonger",
        name="hongkonger",
        label="Hongkonger",
        description="A person having origins in Hong Kong.",
        parents=["ethnicity"],
        annotations=[],
        synonyms=["Hong Konger", "Hong Kongese"],
    ),
    Choice(
        sid="aboriginal",
        name="aboriginal",
        label="Aboriginal",
        description="A person with indigenous australian origin.",
        parents=["ethnicity"],
        annotations=[],
        synonyms=["Aboriginy"],
    ),
    Choice(
        sid="russian",
        name="russian",
        label="Russian",
        description="Denotes the inhabitants of Russia, a person from there, or their descendants elsewhere.",
        parents=["caucasian"],
        annotations=[],
    ),
]
