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
        label="Chinese",
        description="Chinese. A person having origins in any of the original peoples of China.",
        parents=["asian"],
        annotations=[
            (BQB.IS, "NCIT:C43391"),
        ],
    ),
    Choice(
        sid="japanese",
        label="Japanese",
        description="A person having origins in any of the original peoples of Japan.",
        parents=["asian"],
        annotations=[
            (BQB.IS, "NCIT:C43392"),
        ],
    ),
    Choice(
        sid="thai",
        label="Thai",
        description="Denotes the inhabitants of Thailand, a person from there, or their descendants elsewhere.",
        parents=["asian"],
        annotations=[
            (BQB.IS, "NCIT:C43400"),
        ],
    ),
    Choice(
        sid="caucasian",
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
        label="Finnish",
        description="Finnish. A person having origins in any of the original peoples of Finland.",
        parents=["caucasian"],
        annotations=[
            (BQB.IS, "NCIT:C64943"),
        ],
    ),
    Choice(
        sid="hispanic",
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
        label="Non-Hispanic",
        description="Not Hispanic or Latino.",
        parents=["ethnicity"],
    ),
    Choice(
        sid="mixed-race",
        name="mixed race",
        label="Mixed race",
        description="Mixed race origin.",
        parents=["ethnicity"],
        synonyms=[],
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
        label="Asian Indian",
        description="A person having origins in the original peoples of the Indian sub-continent.",
        parents=["ethnicity"],
        annotations=[
            (BQB.IS_VERSION_OF, "NCIT:C41262"),
        ],
    ),
    Choice(
        sid="egyptian",
        label="Egyptian",
        description="Denotes the inhabitants of Egypt, a person from there, or their descendants elsewhere.",
        parents=["ethnicity"],
        annotations=[
            (BQB.IS_VERSION_OF, "NCIT:C43868"),
        ],
    ),
    Choice(
        sid="jordanian",
        label="Jordanian",
        description="Denotes the inhabitants of Jordan, a person from there, or their descendants elsewhere.",
        parents=["ethnicity"],
    ),
    Choice(
        sid="swedish",
        label="Swedish",
        description="Denotes the inhabitants of Sweden, a person from there, or their descendants elsewhere.",
        parents=["ethnicity"],
        annotations=[
            (BQB.IS_VERSION_OF, "NCIT:C43861"),
        ],
    ),
    Choice(
        sid="spanish",
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
        description="A person from Trinidad and Tobago with African ancestry.",
        parents=["ethnicity"],
    ),
    Choice(
        sid="indo-trinidadians",
        name="indo trinidadians",
        label="Indo-Trinidadians",
        description="A person of Indian origin who are nationals of Trinidad and Tobago "
        "whose ancestors came from India and the wider subcontinent beginning in 1845.",
        parents=["ethnicity"],
    ),
    Choice(
        sid="black",
        label="Black",
        description="A person having origins in the original peoples of sub-Saharan Africa or the Caribbean.",
        parents=["ethnicity"],
        annotations=[
            (BQB.IS_VERSION_OF, "NCIT:C128938"),
        ],
    ),
    Choice(
        sid="pacific-islander",
        # (BQB.IS_VERSION_OF, "exo/0000154"),
        name="pacific islander",
        label="Pacific Islander",
        description="A person having origins in the original peoples of the Pacific Islands.",
        parents=["ethnicity"],
    ),
    Choice(
        sid="indian",
        label="Indian",
        description="A person having origins in India.",
        parents=["ethnicity"],
    ),
    Choice(
        sid="mexican",
        label="Mexican",
        description="A person having origins in Mexico.",
        parents=["ethnicity"],
    ),
    Choice(
        sid="west_asian",
        name="west asian",
        label="West Asian",
        description="A person having origins in West Asia.",
        parents=["ethnicity"],
    ),
    Choice(
        sid="taiwanese",
        label="Taiwanese",
        description="A person having origins in Taiwan.",
        parents=["ethnicity"],
    ),
    Choice(
        sid="hongkonger",
        label="Hongkonger",
        description="A person having origins in Hong Kong.",
        parents=["ethnicity"],
        synonyms=["Hong Konger", "Hong Kongese"],
    ),
    Choice(
        sid="aboriginal",
        label="Aboriginal",
        description="A person with indigenous australian origin.",
        parents=["ethnicity"],
        synonyms=["Aboriginy"],
    ),
    Choice(
        sid="russian",
        label="Russian",
        description="Denotes the inhabitants of Russia, a person from there, or their descendants elsewhere.",
        parents=["caucasian"],
    ),
]
