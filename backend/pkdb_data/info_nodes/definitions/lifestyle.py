"""Definition of information related to lifestyle."""

from pymetadata.core.miriam import BQB

from ..node import Choice, DType, InfoNode, MeasurementType
from ..units import DIMENSIONLESS, NO_UNIT

LIFESTYLE_NODES: list[InfoNode] = [
    # -------------------------------------------------------------------------
    # Lifestyle measurements
    # -------------------------------------------------------------------------
    MeasurementType(
        sid="lifestyle measurement",
        name="lifestyle measurement",
        description="lifestyle measurement",
        parents=["measurement"],
        dtype=DType.ABSTRACT,
    ),
    MeasurementType(
        sid="key-lifestyle-measurement",
        name="key lifestyle measurement",
        description="Key lifestyle measurement.",
        parents=["lifestyle measurement"],
        dtype=DType.ABSTRACT,
    ),
    # -------------------------------------------------------------------------
    # Abstinence or consumption of substances
    # -------------------------------------------------------------------------
    MeasurementType(
        "abstinence",
        description="Abstinence of given substance (substance is required). "
        "Use the value fields to encode duration of abstinence if provided. "
        "Key lifestyle measurements have to be encoded via dedicated "
        "measurement types found under `key lifestyle measurements`, "
        "e.g., smoking, alcohol and oral contraceptives.",
        parents=["lifestyle measurement"],
        dtype=DType.NUMERIC,
        units=["day", NO_UNIT],
    ),
    MeasurementType(
        "consumption",
        description="Consumption of given substance (substance is required). "
        "Key lifestyle measurements have to be encoded via dedicated "
        "measurement types found under `key lifestyle measurements`, "
        "e.g., smoking, alcohol and oral contraceptives.",
        parents=["lifestyle measurement"],
        dtype=DType.NUMERIC,
        units=["mg/day", "beverages/day"],
    ),
    # -------------------------------------------------------------------------
    # Smoking
    # -------------------------------------------------------------------------
    MeasurementType(
        sid="smoking-status",
        name="smoking status",
        description="smoking status",
        parents=["key lifestyle measurement"],
        dtype=DType.ABSTRACT,
    ),
    MeasurementType(
        sid="smoking",
        name="smoking",
        description="Information on the smoking status. Does subject or group smoke?",
        parents=["smoking status"],
        dtype=DType.BOOLEAN,
    ),
    MeasurementType(
        sid="abstinence-smoking",
        name="abstinence smoking",
        description="How long no smoking?",
        parents=["smoking status"],
        dtype=DType.NUMERIC,
        units=["yr"],
        synonyms=["smoking cessation"],
    ),
    MeasurementType(
        "smoking amount (cigarettes)",
        description="How many cigarettes are smoked?",
        parents=["smoking status"],
        dtype=DType.NUMERIC,
        units=["1/day"],
    ),
    MeasurementType(
        "smoking amount (packyears)",
        description="How many pack years smoked? The pack-year is a unit for "
        "measuring the amount a person has smoked over a long period of time. "
        "It is calculated by multiplying the number of packs of cigarettes "
        "smoked per day by the number of years the person has smoked. "
        "For example, 1 pack-year is equal to smoking 20 cigarettes (1 pack) "
        "per day for 1 year, or 40 cigarettes per day for half a year, "
        "and so on.",
        parents=["smoking status"],
        dtype=DType.NUMERIC,
        units=["yr"],
    ),
    MeasurementType(
        "smoking duration",
        description="How many years smoking?",
        parents=["smoking status"],
        dtype=DType.NUMERIC,
        units=["yr"],
    ),
    MeasurementType(
        "marijuana status",
        description="marijuana status",
        parents=["key lifestyle measurement"],
        dtype=DType.ABSTRACT,
    ),
    MeasurementType(
        "marijuana",
        description="Does subject or group smoke marijuana?",
        parents=["marijuana status"],
        dtype=DType.BOOLEAN,
    ),
    MeasurementType(
        "abstinence marijuana",
        description="How long no marijuana?",
        parents=["marijuana status"],
        dtype=DType.NUMERIC,
        units=["yr"],
    ),
    MeasurementType(
        "marijuana amount (joints)",
        description="How many joints are smoked?",
        parents=["marijuana status"],
        dtype=DType.NUMERIC,
        units=["1/day"],
    ),
    MeasurementType(
        "marijuana duration",
        description="How many years smoking marijuana?",
        parents=["marijuana status"],
        dtype=DType.NUMERIC,
        units=["yr"],
    ),
    # -------------------------------------------------------------------------
    # Alcohol
    # -------------------------------------------------------------------------
    MeasurementType(
        "alcohol status",
        description="alcohol status",
        parents=["key lifestyle measurement"],
        dtype=DType.ABSTRACT,
    ),
    MeasurementType(
        "alcohol",
        description="Does subject or group drink alcohol? (use in combination with "
        "'abstinence' and 'consumption' with choice 'alcohol' to provide"
        "details about duration of abstinence or consumed amount). Use to encode 'drinker' or "
        "'non-drinker'.",
        parents=["alcohol status"],
        dtype=DType.BOOLEAN,
    ),
    MeasurementType(
        "alcohol duration",
        description="How many years alcohol?",
        parents=["alcohol status"],
        dtype=DType.NUMERIC,
        units=["yr"],
    ),
    MeasurementType(
        "abstinence alcohol",
        description="How long no alcohol?",
        parents=["alcohol status"],
        dtype=DType.NUMERIC,
        units=["day", NO_UNIT],
    ),
    MeasurementType(
        "alcohol amount",
        description="How many alcohol consumed per day? Either in amount alcohol "
        "or beverages per day.",
        parents=["alcohol status"],
        dtype=DType.NUMERIC,
        units=["1/day", "g/day"],
    ),
    # -------------------------------------------------------------------------
    # Medication
    # -------------------------------------------------------------------------
    MeasurementType(
        "medication status",
        description="mediation related information",
        parents=["lifestyle measurement"],
        dtype=DType.ABSTRACT,
    ),
    MeasurementType(
        "medication",
        description="subjects did take any medication (see also `medication (type)` "
        "and `medication (amount)`). To encode the abstinence of any "
        "medication use the measurement_type `abstinence medication`. "
        "To encode the substance given as medication use 'substance' field. "
        "Certain medications which are key lifestyle measurements "
        "have to be encoded via dedicated measurement types found "
        "under `key lifestyle measurements`, e.g., `oral contraceptives`.",
        parents=["medication status"],
        dtype=DType.BOOLEAN,
    ),
    MeasurementType(
        "medication amount",
        description="type of medication taken, optionally the amount can be encoded "
        "(store duration in `medication duration`). "
        "To encode the substance given as medication use the "
        "'substance' field. ",
        parents=["medication status"],
        dtype=DType.NUMERIC,
        units=["mg/day"],
    ),
    MeasurementType(
        "abstinence medication",
        description="How long was no medication taken? Use value fields to encode duration "
        "of abstinence. If substance is provided use 'abstinence' with substance instead. "
        "Also encode the boolen 'medication' measurement type in addition.",
        parents=["medication status"],
        dtype=DType.NUMERIC,
        units=["day", NO_UNIT],
        synonyms=["abstinence drug"],
    ),
    MeasurementType(
        "medication duration",
        description="Type of medication taken, optionally the amount can be encoded "
        "(store amount in `medication amount`)",
        parents=["medication status"],
        dtype=DType.NUMERIC,
        units=["day"],
    ),
    # -------------------------------------------------------------------------
    # Oral contraceptives
    # -------------------------------------------------------------------------
    MeasurementType(
        "oral contraceptive status",
        description="oral contraceptive status",
        parents=["key lifestyle measurement"],
        dtype=DType.ABSTRACT,
    ),
    MeasurementType(
        "oral contraceptives",
        description="Subjects took oral contraceptives (details about the used oral "
        "contraceptive, should be encoded via "
        "'medication amount' and/or 'medication duration'). See also"
        "'abstinence oral contraceptives' or 'oral contraceptives duration'.",
        parents=["oral contraceptive status"],
        dtype=DType.BOOLEAN,
    ),
    MeasurementType(
        "abstinence oral contraceptives",
        description="How long no oral contraceptives?",
        parents=["oral contraceptive status"],
        dtype=DType.NUMERIC,
        units=["day", NO_UNIT],
    ),
    MeasurementType(
        "oral contraceptives duration",
        description="How many years oral contraceptives?",
        parents=["oral contraceptive status"],
        dtype=DType.NUMERIC,
        units=["yr"],
    ),
    # -------------------------------------------------------------------------
    # Diet, fasting, nutrition & metabolic challenges
    # -------------------------------------------------------------------------
    MeasurementType(
        "diet",
        description="Special nutrition or diet of subjects, e.g., vegetarian. The "
        "customary allowance of food and drink taken by a person or an "
        "animal from day to day, particularly one especially planned to "
        "meet specific requirements of the individual, including or "
        "excluding certain items of food; ",
        parents=["lifestyle measurement"],
        dtype=DType.CATEGORICAL,
        annotations=[
            (BQB.IS, "NCIT:C15222"),
            (BQB.IS, "efo/0002755"),
        ],
    ),
    Choice(
        sid="vegetarian",
        name="vegetarian",
        description="Vegetarian diet. A person who eats no meat; some may eat fish, "
        "eggs, or dairy products.",
        parents=["diet"],
        annotations=[
            (BQB.IS, "NCIT:C92993"),
        ],
    ),
    MeasurementType(
        sid="feeding-protocol",
        name="feeding protocol",
        description="Feeding protocol (animal experiments). For human studies see 'diet'.",
        parents=["lifestyle measurement"],
        dtype=DType.CATEGORICAL,
        annotations=[],
    ),
    Choice(
        sid="feeding-ad-libitum",
        name="ad libitum",
        description="Ad libitum feeding. Continuous access to food.",
        parents=["feeding protocol"],
        annotations=[],
    ),
    Choice(
        sid="feeding-time-restricted",
        name="time restricted",
        description="Time restricted access to food.",
        parents=["feeding protocol"],
        annotations=[],
    ),
    MeasurementType(
        "fasting status",
        description="Fasting information. The state of a subject that represents to "
        "what extent they have abstained from consuming food or liquid.",
        parents=["lifestyle measurement"],
        dtype=DType.ABSTRACT,
        annotations=[(BQB.IS, "NCIT:C120460")],
    ),
    MeasurementType(
        "fasting",
        description="Subjects were fasted (see also `overnight fast` and "
        "`fasting (duration)`).",
        parents=["fasting status"],
        dtype=DType.BOOLEAN,
        annotations=[
            (BQB.IS, "NCIT:C63663"),
            (BQB.IS, "efo/0002756"),
        ],
    ),
    MeasurementType(
        "overnight fast",
        description="subjects were overnight fasted (see also `fasting (duration)`).",
        parents=["fasting status"],
        dtype=DType.BOOLEAN,
        annotations=[
            (BQB.IS_VERSION_OF, "NCIT:C63663"),
            (BQB.IS_VERSION_OF, "efo/0002756"),
        ],
    ),
    MeasurementType(
        "fasting (duration)",
        description="Duration of fasting before study. Abstaining from food.",
        parents=["fasting status"],
        dtype=DType.NUMERIC,
        units=["day"],
        annotations=[
            (BQB.IS, "NCIT:C63663"),
            (BQB.IS, "efo/0002756"),
        ],
    ),
    MeasurementType(
        "appetite-rating",
        name="appetite rating",
        description="Appetite rating (assessed by visual analog scale, VAS).",
        parents=["lifestyle measurement"],
        dtype=DType.ABSTRACT,
        annotations=[],
    ),
    MeasurementType(
        "satiety",
        description="Satiety appetite rating (assessed by visual analog scale, VAS).",
        parents=["appetite rating"],
        dtype=DType.NUMERIC,
        units=["mm"],
        annotations=[
            (BQB.IS, "SNOMEDCT:75121008"),
        ],
    ),
    MeasurementType(
        "hunger",
        description="Hunger appetite rating (assessed by visual analog scale, VAS).",
        parents=["appetite rating"],
        dtype=DType.NUMERIC,
        units=["mm"],
        annotations=[],
    ),
    MeasurementType(
        "fullness",
        description="Fullness appetite rating (assessed by visual analog scale, VAS).",
        parents=["appetite rating"],
        dtype=DType.NUMERIC,
        units=["mm"],
        annotations=[],
    ),
    MeasurementType(
        "prospective-food-consumption",
        name="prospective food consumption",
        description="Prospective food consumption appetite rating (assessed by visual analog scale, VAS).",
        parents=["appetite rating"],
        dtype=DType.NUMERIC,
        units=["mm"],
        annotations=[],
    ),
    MeasurementType(
        "overall-appetite-score",
        name="overall appetite score",
        label="overall appetite score (OAS)",
        description="Overall appetite rating (assessed by visual analog scale, VAS)."
        "OAS = (satiety + fullness + (100 - hunger) + (100 - prospective food consumption))/4",
        parents=["appetite rating"],
        dtype=DType.NUMERIC,
        units=["mm"],
        annotations=[],
    ),
    MeasurementType(
        "metabolic challenge",
        description="nutritional challenge by meal or infusion",
        parents=["lifestyle measurement"],
        dtype=DType.CATEGORICAL,
    ),
    MeasurementType(
        "glucose metabolism challenge",
        description="Nutritional challenge, clamp or infusion to characterize "
        "glucose metabolism",
        parents=["metabolic challenge"],
        dtype=DType.CATEGORICAL,
    ),
    Choice(
        "oral glucose tolerance test (OGTT)",
        description="Oral glucose tolerance test.",
        parents=["glucose metabolism challenge"],
        name="ogtt",
    ),
    Choice(
        "intravenous glucose tolerance test (IVGTT)",
        description="Intravenous glucose tolerance test (IVGTT).",
        parents=["glucose metabolism challenge"],
        name="ivgtt",
    ),
    MeasurementType(
        "meal",
        description="Meal. Any of the occasions for eating food that occur by custom or "
        "habit at more or less fixed times.",
        parents=["metabolic challenge"],
        dtype=DType.ABSTRACT,
        annotations=[(BQB.IS, "NCIT:C80248")],
    ),
    Choice(
        "mixed meal",
        description="Mixed meal or multicomponent meal. "
        "A meal consisting of multiple components, i.e., carbohydrates, "
        "lipids, and proteins. A multiple-component food product typically "
        "containing a protein source, a vegetable, and a potato, rice or "
        "cereal-based component packaged to be served after heating, "
        "either as separate items or courses or mixed as recipe components",
        parents=["meal"],
        annotations=[(BQB.IS, "foodon/FOODON:03400139")],
    ),
    Choice(
        "single component meal",
        description="Single component meal. A meal consisting of a single meal component, "
        "i.e., either carbohydrates, lipids or proteins.",
        parents=["meal"],
    ),
    Choice(
        "hypoglycemic clamp",
        description="hypoglycemic clamp",
        parents=["glucose metabolism challenge"],
    ),
    Choice(
        "hyperinsulinemic euglycemic clamp",
        description="hyperinsulinemic euglycemic clamp",
        parents=["glucose metabolism challenge"],
    ),
    Choice(
        "isoglycemic glucose infusion",
        description="isoglycemic glucose infusion",
        parents=["glucose metabolism challenge"],
    ),
    Choice(
        "protein metabolic challenge",
        description="nutritional challenge with protein",
        parents=["single component meal"],
    ),
    Choice(
        "protein solution",
        description="protein solution",
        parents=["protein metabolic challenge"],
    ),
    Choice(
        "lipid-glucose-protein challenge",
        description="lipid-glucose-protein challenge",
        parents=["mixed meal"],
    ),
    # -------------------------------------------------------------------------
    # Physiological status
    # -------------------------------------------------------------------------
    MeasurementType(
        "physiological status",
        description="Any change in physiological status, e.g., exercise, sleeping, "
        "day/night time.",
        parents=["lifestyle measurement"],
        dtype=DType.ABSTRACT,
    ),
    # -------------------------------------------------------------------------
    # Temperature
    # -------------------------------------------------------------------------
    MeasurementType(
        "body-temperature",
        name="body temperature",
        description="Body temperature. A measurement of the temperature of the body.",
        parents=["physiological status"],
        dtype=DType.NUMERIC,
        units=["K", "C"],
        annotations=[
            (BQB.IS, "NCIT:C174446"),
            (BQB.IS, "https://bioregistry.io/CMO:0000015"),
        ],
        synonyms=["temperature"],
    ),
    # -------------------------------------------------------------------------
    # Exercise
    # -------------------------------------------------------------------------
    MeasurementType(
        sid="exercise",
        name="exercise",
        description="Exercise performed or not? "
        "Activity that requires physical or mental exertion, especially when "
        "performed to develop or maintain fitness.",
        parents=["physiological status"],
        dtype=DType.BOOLEAN,
        annotations=[
            (BQB.IS, "NCIT:C16567"),
            (BQB.IS, "efo/0000483"),
        ],
    ),
    MeasurementType(
        "exercise (categorial)",
        description="What kind of exercise was performed."
        "Activity that requires physical or mental exertion, especially when "
        "performed to develop or maintain fitness.",
        parents=["physiological status"],
        dtype=DType.CATEGORICAL,
        annotations=[
            (BQB.IS, "NCIT:C16567"),
            (BQB.IS, "efo/0000483"),
        ],
    ),
    Choice(
        "rest",
        description="Rest. Subjects rested. Often default or control group which must not"
        "be encoded.",
        parents=["exercise (categorial)"],
    ),
    Choice(
        "light exercise",
        description="Subjects performed light exercise",
        parents=["exercise (categorial)"],
    ),
    Choice(
        "moderate exercise",
        description="Subjects performed moderate exercise",
        parents=["exercise (categorial)"],
    ),
    MeasurementType(
        "sleeping status",
        description="status in regard to sleeping during study",
        parents=["physiological status"],
        dtype=DType.CATEGORICAL,
    ),
    Choice(
        "asleep",
        description="subjects are asleep during test",
        parents=["sleeping status"],
        annotations=[
            (BQB.IS, "https://bioregistry.io/NBO:0000067"),
        ],
    ),
    Choice(
        "awake",
        description="subjects are awake during test",
        parents=["sleeping status"],
    ),
    # -------------------------------------------------------------------------
    # Pregnancy
    # -------------------------------------------------------------------------
    MeasurementType(
        "pregnancy status",
        description="Abstract status in regard to pregnancy. Use either the boolean "
        "'pregnant' or the categorial 'pregnant (categorial)' to "
        "encode information related to the pregnancy status.",
        parents=["physiological status"],
        dtype=DType.ABSTRACT,
    ),
    MeasurementType(
        "pregnant",
        description="Is subject pregnant or not?",
        parents=["pregnancy status"],
        dtype=DType.BOOLEAN,
        annotations=[
            (BQB.IS, "NCIT:C124295"),
            (BQB.IS, "omit/0022808"),
        ],
    ),
    MeasurementType(
        "lactating",
        description="Is subject lactating or not? An indication that the subject "
        "is currently producing milk. See also 'breastfeeding'.",
        parents=["pregnancy status"],
        dtype=DType.BOOLEAN,
        annotations=[
            (BQB.IS, "NCIT:C82463"),
        ],
    ),
    MeasurementType(
        "breastfeeding",
        description="Is subject breastfeeding or not? The nursing of an infant at the "
        "mother's breast. See also 'lactating'.",
        parents=["pregnancy status"],
        dtype=DType.BOOLEAN,
        annotations=[
            (BQB.IS, "NCIT:C25596"),
            # (BQB.IS, "http://purl.bioontology.org/ontology/LNC/LP420040-0"),  # Loinc
        ],
    ),
    MeasurementType(
        "pregnant (categorial)",
        description="Is subject pregnant or not?",
        parents=["pregnancy status"],
        dtype=DType.CATEGORICAL,
        annotations=[
            (BQB.IS, "NCIT:C124295"),
            (BQB.IS, "omit/0022808"),
        ],
    ),
    Choice(
        "pregnant (first trimester)",
        description="Pregnant woman in the first trimester.",
        parents=["pregnant (categorial)"],
        annotations=[
            (BQB.IS, "NCIT:C92799"),
            (BQB.IS, "omit/0012222"),
            (BQB.IS_VERSION_OF, "NCIT:C124295"),
        ],
    ),
    Choice(
        "pregnant (second trimester)",
        description="Pregnant woman in the second trimester",
        parents=["pregnant (categorial)"],
        annotations=[
            (BQB.IS, "NCIT:C92876"),
            (BQB.IS, "omit/0012223"),
            (BQB.IS_VERSION_OF, "NCIT:C124295"),
        ],
    ),
    Choice(
        "pregnant (third trimester)",
        description="Pregnant woman in the third trimester.",
        parents=["pregnant (categorial)"],
        annotations=[
            (BQB.IS, "NCIT:C92896"),
            (BQB.IS, "omit/0012224"),
            (BQB.IS_VERSION_OF, "NCIT:C124295"),
        ],
    ),
    Choice(
        "postpartum",
        description="The period of time immediately after labor and delivery",
        parents=["pregnant (categorial)"],
        annotations=[
            (BQB.IS, "NCIT:C92851"),
            (BQB.IS, "omit/0024181"),
        ],
    ),
    # -------------------------------------------------------------------------
    # Menstrual status
    # -------------------------------------------------------------------------
    MeasurementType(
        "menstrual status",
        description="status in regard to menstrual cycle",
        parents=["physiological status"],
        dtype=DType.CATEGORICAL,
    ),
    MeasurementType(
        "menstrual time of cycle",
        description="Week of menstrual cycle [1-4].",
        units=["week"],
        parents=["menstrual status"],
        dtype=DType.NUMERIC,
    ),
    Choice("luteal phase", description="luteal phase", parents=["menstrual status"]),
    Choice(
        "follicular phase", description="follicular phase", parents=["menstrual status"]
    ),
    Choice(
        "ovulatory phase", description="ovulatory phase", parents=["menstrual status"]
    ),
    # -------------------------------------------------------------------------
    # Housing (animal experiments)
    # -------------------------------------------------------------------------
    MeasurementType(
        sid="housing",
        name="housing",
        description="Housing conditions (for animal experiments)",
        parents=["lifestyle measurement"],
        dtype=DType.ABSTRACT,
    ),
    MeasurementType(
        sid="housing-temperature",
        name="housing temperature",
        description="Room temperature (housing conditions)",
        parents=["housing"],
        dtype=DType.NUMERIC,
        units=["K", "C"],
    ),
    MeasurementType(
        sid="housing-humidity",
        name="housing humidity",
        description="Housing humidity (housing conditions)",
        parents=["housing"],
        dtype=DType.NUMERIC,
        units=[DIMENSIONLESS],
    ),
    MeasurementType(
        sid="housing-group-size",
        name="housing group size",
        description="Housing group size (housing conditions). Number of animals per "
        "unit or cage.",
        parents=["housing"],
        dtype=DType.NUMERIC,
        units=[DIMENSIONLESS],
    ),
    MeasurementType(
        sid="housing-acclimatization-time",
        name="housing acclimatization time",
        description="Housing acclimatization time (housing conditions). Duration for acclimatization.",
        parents=["housing"],
        dtype=DType.NUMERIC,
        units=[DIMENSIONLESS],
    ),
    # -------------------------------------------------------------------------
    # Circadian information
    # -------------------------------------------------------------------------
    MeasurementType(
        "light-dark-cycle",
        description="Light-dark cycle. To encode time of day see also 'circadian status'.",
        parents=["physiological status"],
        dtype=DType.CATEGORICAL,
    ),
    MeasurementType(
        "light-dark-cycle-12-12",
        name="light/dark 12/12",
        description="12 hours light, 12 hours dark",
        parents=["light-dark-cycle"],
        dtype=DType.CATEGORICAL,
    ),
    MeasurementType(
        "light-dark-cycle-24-0",
        name="light/dark 24/0",
        description="24 hours light, 0 hours dark; continuous light.",
        parents=["light-dark-cycle"],
        dtype=DType.CATEGORICAL,
    ),
    MeasurementType(
        "light-dark-cycle-0-24",
        name="light/dark 0/24",
        description="0 hours light, 24 hours dark; continuous dark.",
        parents=["light-dark-cycle"],
        dtype=DType.CATEGORICAL,
    ),
    MeasurementType(
        "light-dark-cycle-16-8",
        name="light/dark 16/8",
        description="16 hours light, 8 hours dark",
        parents=["light-dark-cycle"],
        dtype=DType.CATEGORICAL,
    ),
    MeasurementType(
        "circadian-status",
        name="circadian status (time of day)",
        description="Circadian status, i.e. time of day. For experimental protocols see "
        "also 'light-dark-cycle'.",
        parents=["physiological status"],
        dtype=DType.CATEGORICAL,
    ),
    Choice(
        "morning",
        description="Subjects were studied in the morning after sleep. "
        "The time period between dawn and noon.",
        parents=["circadian status"],
        synonyms=["AM"],
        annotations=[(BQB.IS, "NCIT:C64934")],
    ),
    Choice(
        "daytime",
        description="subjects were studied during the day",
        parents=["circadian status"],
    ),
    Choice(
        "evening",
        description="Subjects were studied at the evening. "
        "The time period between late afternoon and bedtime.",
        parents=["circadian status"],
        synonyms=["PM"],
        annotations=[(BQB.IS, "NCIT:C64936")],
    ),
    Choice(
        "nighttime (pre-sleep)",
        description="Subjects were studied during the night before sleep",
        parents=["circadian status"],
    ),
    Choice(
        "nighttime",
        description="subjects were studied during the night",
        parents=["circadian status"],
    ),
    MeasurementType(
        "body position",
        description="Body position. The spatial property of a body; where it is or the way "
        "in which it is situated.",
        parents=["physiological status"],
        dtype=DType.CATEGORICAL,
        annotations=[(BQB.IS, "NCIT:C62164")],
    ),
    Choice("sitting", description="Sitting body position.", parents=["body position"]),
    Choice(
        "recumbent position",
        description="Recumbent body position. Lying down, see also 'supine' and 'prone'.",
        parents=["body position"],
        annotations=[(BQB.IS, "NCIT:C77532")],
    ),
    Choice(
        "supine",
        description="Supine body position. A posterior recumbent body position whereby "
        "the person lies on its back and faces upward.",
        parents=["recumbent position"],
        annotations=[(BQB.IS, "NCIT:C62167")],
    ),
    Choice(
        "erect",
        description="Erect or standing body position. A positional quality inhering in a bearer "
        "by virtue of the bearer's being upright in position or posture.",
        parents=["body position"],
        annotations=[(BQB.IS, "NCIT:C62166")],
        synonyms=["standing"],
    ),
    Choice(
        "prone",
        description="Prone body position. An anterior recumbent body position whereby the "
        "person lies on its stomach and faces downward.",
        parents=["recumbent position"],
        annotations=[(BQB.IS, "NCIT:C62165")],
    ),
    Choice(
        "ambulant",
        description="Ambulant body position. Subjects are sitting/walking.",
        parents=["body position"],
    ),
]
