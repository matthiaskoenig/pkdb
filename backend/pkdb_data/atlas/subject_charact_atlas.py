"""Subject characteristics for ATLAS."""

from pymetadata.core.miriam import BQB

from pkdb_data.atlas.units_atlas import (
    BMI_UNITS,
    HEIGHT_UNITS,
    TIME_UNITS,
    WEIGHT_UNITS,
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

SUBJ_CHARACT_ATLAS_NODES: list[InfoNode] = [
    MeasurementType(
        "age",
        description="Age of patient who is the subject of observations. ",
        dtype=DType.ABSTRACT,
        annotations=[
            (BQB.IS, "ncit/C69260"),
        ],
        parents=["subject-characteristics"],
    ),
    MeasurementType(
        sid="age-numeric",
        description="Age of subject or animal. How long something has existed. "
        "Elapsed time since birth.",
        dtype=DType.NUMERIC,
        units=TIME_UNITS,
        annotations=[
            (BQB.IS, "ncit/C25150"),
            # (BQB.IS, "efo/0000246"),
            # (BQB.IS, "sio/SIO_001013"),
        ],
        parents=["age"],
    ),
    MeasurementType(
        sid="age-of-enrollment",
        description="The age of a subject when entering a group, catalog, list, or study. ",
        dtype=DType.NUMERIC,
        units=TIME_UNITS,
        annotations=[
            (BQB.IS, "ncit/C164338"),
            # (BQB.IS, "efo/0000246"),
            # (BQB.IS, "sio/SIO_001013"),
        ],
        parents=["age-numeric"],
    ),
    MeasurementType(
        sid="age-at-diagnosis",
        description="The age of an individual at the time of initial pathologic diagnosis. ",
        dtype=DType.NUMERIC,
        units=TIME_UNITS,
        annotations=[
            (BQB.IS, "ncit/C156420"),
            # (BQB.IS, "efo/0000246"),
            # (BQB.IS, "sio/SIO_001013"),
        ],
        parents=["age-numeric"],
    ),
    MeasurementType(
        sid="age-related-group",
        description="Subgroups of populations based on age. ",
        synonyms=["Age group", "Group of age"],
        dtype=DType.CATEGORICAL,
        annotations=[
            (BQB.IS, "ncit/C20587"),
            # (BQB.IS, "efo/0000246"),
            # (BQB.IS, "sio/SIO_001013"),
        ],
        parents=["age"],
    ),
    Choice(
        sid="adolescent",
        description="An age group comprised of juveniles between the onset of puberty and maturity. "
        "In the state of development between puberty and maturity. ",
        annotations=[
            (BQB.IS, "ncit/C27954"),
            #   (BQB.IS, "efo/0001359"),
        ],
        parents=["age-related-group"],
    ),
    Choice(
        sid="adult",
        description="An age group comprised of humans who have reached reproductive age. ",
        annotations=[
            (BQB.IS, "ncit/C17600"),
            #   (BQB.IS, "efo/0001359"),
        ],
        parents=["age-related-group"],
    ),
    Choice(
        sid="child",
        description="An age group comprised of individuals who are not yet an adult. The specific cut-off age will vary by purpose. ",
        annotations=[
            (BQB.IS, "ncit/C16423"),
            #   (BQB.IS, "efo/0001359"),
        ],
        parents=["age-related-group"],
    ),
    Choice(
        sid="elderly",
        description="An age group comprised of individuals 65 years of age and older. ",
        annotations=[
            (BQB.IS, "ncit/C16268"),
            #   (BQB.IS, "efo/0001359"),
        ],
        parents=["age-related-group"],
    ),
    Choice(
        sid="infant-and-toddler",
        description="An age group comprised of individuals between 28 days to 23 months of age. ",
        annotations=[
            (BQB.IS, "ncit/C49643"),
            #   (BQB.IS, "efo/0001359"),
        ],
        parents=["age-related-group"],
    ),
    MeasurementType(
        sid="sex",
        description="Sex of subject or animal. The assemblage of physical properties "
        "or qualities by which male is distinguished from female. "
        "The physical difference between male and female, the "
        "distinguishing peculiarity of male or female.",
        synonyms=["Gender"],
        dtype=DType.CATEGORICAL,
        annotations=[
            (BQB.IS, "ncit/C28421"),
            # (BQB.IS, "omit/0013619"),
        ],
        parents=["subject-characteristics"],
    ),
    Choice(
        sid="male",
        description="Male is a biological sex of an individual with "
        "male sexual organs.",
        synonyms=["man", "men"],
        annotations=[
            (BQB.IS, "ncit/C20197"),
            # (BQB.IS, "sio/SIO_010048"),
        ],
        parents=["sex"],
    ),
    Choice(
        sid="female",
        description="Female is a biological sex of an individual with female "
        "sexual organs.",
        synonyms=["woman", "women"],
        annotations=[
            (BQB.IS, "ncit/C16576"),
            # (BQB.IS, "sio/SIO_010052"),
        ],
        parents=["sex"],
    ),
    Choice(
        sid="other-sex",
        description="Different than the one(s) previously specified or mentioned. ",
        annotations=[
            (BQB.IS, "ncit/C17649"),
            # (BQB.IS, "sio/SIO_010052"),
        ],
        parents=["sex"],
    ),
    Choice(
        sid="undifferentiated-sex",
        description="Sex could not be determined, not uniquely defined, undifferentiated. ",
        synonyms=["Undifferentiated Sex"],
        annotations=[
            (BQB.IS, "ncit/C41438"),
            # (BQB.IS, "sio/SIO_010052"),
        ],
        parents=["sex"],
    ),
    Choice(
        sid="unknown-sex",
        description="Not known, not observed, not recorded, or refused. ",
        annotations=[
            (BQB.IS, "ncit/C17998"),
            # (BQB.IS, "sio/SIO_010052"),
        ],
        parents=["sex"],
    ),
    # Choice(
    #     sid="mixed-sex",
    #     description="Males and females without exact count. Mixed sex allows to "
    #                 "encode that men and women participated in a group.",
    #     parents = ["sex"],
    #     synonyms=["male and female"],
    # ),
    MeasurementType(
        sid="body-measurement",
        description="Measurement of the body weight of a subject. ",
        dtype=DType.ABSTRACT,
        annotations=[
            (BQB.IS, "ncit/C92648"),
        ],
        parents=["subject-characteristics"],
    ),
    MeasurementType(
        sid="total-body-weight",
        description="The weight of a subject. ",
        synonyms=["TBW", "Total body weight", "Body weight", "Weight"],
        dtype=DType.NUMERIC,
        units=WEIGHT_UNITS,
        annotations=[
            # (BQB.IS, "efo/0004338"),
            (BQB.IS, "ncit/C81328"),
            # (BQB.IS, "ncit/C92648"),
            # (BQB.IS, "cmo/CMO:0000012"),
        ],
        parents=["body-weight"],
    ),
    MeasurementType(
        sid="lbw",
        description="The mass of the body minus the fat. ",
        synonyms=["Lean body weight", "Lean body mass"],
        dtype=DType.NUMERIC,
        units=WEIGHT_UNITS,
        annotations=[
            # (BQB.IS, "efo/0004338"),
            (BQB.IS, "ncit/C71258"),
            # (BQB.IS, "ncit/C92648"),
            # (BQB.IS, "cmo/CMO:0000012"),
        ],
        parents=["body-weight", "total-body-weight", "bmi"],
    ),
    MeasurementType(
        sid="ibw",
        description="A person's optimum weight as calculated by a standard methodology. ",
        synonyms=["Ideal body weight", "Ideal body mass"],
        dtype=DType.NUMERIC,
        units=WEIGHT_UNITS,
        annotations=[
            (BQB.IS, "ncit/C117976"),
        ],
        parents=["body-weight", "body-height"],
    ),
    MeasurementType(
        sid="fm",
        description="The weight of the body fat associated with either a particular body part or the whole body. ",
        synonyms=["Fat mass"],
        dtype=DType.NUMERIC,
        units=WEIGHT_UNITS,
        annotations=[
            (BQB.IS, "ncit/C158256"),
        ],
        parents=["body-weight", "lbw"],
    ),
    MeasurementType(
        sid="ffm",
        description="Fat free mass",
        synonyms=["Fat free mass"],
        dtype=DType.NUMERIC,
        units=WEIGHT_UNITS,
        annotations=[],
        parents=["body-weight", "total-body-weight", "body-height"],
    ),
    MeasurementType(
        sid="abw",
        description="Adujusted body weight",
        synonyms=["Adjusted body weight", "Adjusted body mass"],
        dtype=DType.NUMERIC,
        units=WEIGHT_UNITS,
        annotations=[],
        parents=["body-weight", "total-body-weight", "ibw"],
    ),
    MeasurementType(
        sid="body-height",
        description="A measurement that describes the vertical measurement or distance from the base, "
        "or bottom, of the patient, to the top of the patient; this can be taken as the "
        "dimension of extension of a patient who cannot stand. ",
        dtype=DType.NUMERIC,
        units=HEIGHT_UNITS,
        annotations=[
            # (BQB.IS, "efo/0004338"),
            (BQB.IS, "ncit/C164634"),
            # (BQB.IS, "ncit/C92648"),
            # (BQB.IS, "cmo/CMO:0000012"),
        ],
        parents=["subject-characteristics"],
    ),
    MeasurementType(
        sid="smoking-status",
        description="An indication of a person's current tobacco and nicotine consumption "
        "as well as some indication of smoking history.",
        dtype=DType.CATEGORICAL,
        annotations=[
            # (BQB.IS, "efo/0004338"),
            (BQB.IS, "ncit/C19796"),
            # (BQB.IS, "cmo/CMO:0000012"),
        ],
        parents=["subject-characteristics"],
    ),
    Choice(
        sid="never-smoker",
        description="A person who has never smoked at the time of the interview or has smoked less than 100 cigarettes in their life. ",
        annotations=[
            # (BQB.IS, "efo/0004338"),
            (BQB.IS, "ncit/C65108"),
            # (BQB.IS, "cmo/CMO:0000012"),
        ],
        parents=["smoking-status"],
    ),
    Choice(
        sid="smoker",
        description="A person who inhales or has inhaled combustible products of organic material during their lifetime. ",
        dtype=DType.CATEGORICAL,
        annotations=[
            # (BQB.IS, "efo/0004338"),
            (BQB.IS, "ncit/C68751"),
            # (BQB.IS, "cmo/CMO:0000012"),
        ],
        parents=["smoking-status"],
    ),
    Choice(
        sid="smoking-at-diagnosis",
        description="An indication that a person was a smoker at the time they received a pathologic diagnosis. ",
        annotations=[
            # (BQB.IS, "efo/0004338"),
            (BQB.IS, "ncit/C164079"),
            # (BQB.IS, "cmo/CMO:0000012"),
        ],
        parents=["smoker"],
    ),
    Choice(
        sid="not-smoking-at-diagnosis",
        description="An indication that a person was not a smoker at the time they received a pathologic diagnosis. ",
        parents=["smoker"],
    ),
    Choice(
        sid="smoking-status-not-documented",
        description="Indicates that a person's smoking status has not been recorded. ",
        dtype=DType.BOOLEAN,
        annotations=[
            # (BQB.IS, "efo/0004338"),
            (BQB.IS, "ncit/C163971"),
            # (BQB.IS, "cmo/CMO:0000012"),
        ],
        parents=["smoking-status"],
    ),
    MeasurementType(
        sid="ecog-performance-status",
        description="A performance status scale designed to assess disease progression and "
        "its affect on the daily living abilities of the patient. ",
        synonyms=["PS"],
        dtype=DType.CATEGORICAL,
        annotations=[
            (BQB.IS, "ncit/C105721"),
        ],
        parents=["subject-characteristics"],
    ),
    Choice(
        sid="ps-grade-0",
        description="Fully active, able to carry on all pre-disease performance without restriction. ",
        synonyms=["PS0"],
        annotations=[
            (BQB.IS, "ncit/C105722"),
        ],
        parents=["ecog-performance-status"],
    ),
    Choice(
        sid="grade-1",
        description="Restricted in physically strenuous activity but ambulatory and able to carry out work "
        "of a light or sedentary nature, e.g., light house work, office work. ",
        synonyms=["PS1"],
        annotations=[
            (BQB.IS, "ncit/C105723"),
        ],
        parents=["ecog-performance-status"],
    ),
    Choice(
        sid="ps-grade-2",
        description="Ambulatory and capable of all self care but unable to carry out any work activities. "
        "Up and about more than 50% of waking hours. ",
        synonyms=["PS2"],
        annotations=[
            (BQB.IS, "ncit/C105725"),
        ],
        parents=["ecog-performance-status"],
    ),
    Choice(
        sid="ps-grade-3",
        description="Capable of only limited selfcare, confined to bed or chair more than 50% of waking hours. ",
        synonyms=["PS3"],
        annotations=[
            (BQB.IS, "ncit/C105726"),
        ],
        parents=["ecog-performance-status"],
    ),
    Choice(
        sid="ps-grade-4",
        description="Completely disabled. Cannot carry on any selfcare. Totally confined to bed or chair. ",
        synonyms=["PS4"],
        annotations=[
            (BQB.IS, "ncit/C105727"),
        ],
        parents=["ecog-performance-status"],
    ),
    Choice(
        sid="ps-grade-5",
        description="Dead. ",
        synonyms=["PS5"],
        annotations=[
            (BQB.IS, "ncit/C105728"),
        ],
        parents=["ecog-performance-status"],
    ),
    MeasurementType(
        sid="bmi",
        description="An individual's weight in kilograms divided "
        "by the square of the height in meters. ",
        dtype=DType.NUMERIC,
        units=BMI_UNITS,
        annotations=[
            (BQB.IS, "ncit/C16358"),
        ],
        parents=["subject-characteristics"],
    ),
    Choice(
        sid="severely-underweight",
        description="BMI less than 16.5 kg/m^2. ",
        annotations=[
            # (https://www.ncbi.nlm.nih.gov/books/NBK541070/),
        ],
        parents=["bmi", "body-fat-disorders"],
    ),
    Choice(
        sid="underweight",
        description="BMI under 18.5 kg/m^2. ",
        annotations=[
            # (https://www.ncbi.nlm.nih.gov/books/NBK541070/),
        ],
        parents=["bmi"],
    ),
    Choice(
        sid="normal-weight",
        description="BMI greater than or equal to 18.5 to 24.9 kg/m^2. ",
        annotations=[
            # (https://www.ncbi.nlm.nih.gov/books/NBK541070/),
        ],
        parents=["bmi"],
    ),
    Choice(
        sid="overweight",
        description="BMI greater than or equal to 25 to 29.9 kg/m^2. ",
        annotations=[
            # (https://www.ncbi.nlm.nih.gov/books/NBK541070/),
        ],
        parents=["bmi"],
    ),
    MeasurementType(
        sid="obesity",
        description="Having a high amount of body fat (body mass index [BMI] of 30 or more). ",
        dtype=DType.CATEGORICAL,
        annotations=[
            (BQB.IS, "ncit/C3283"),
        ],
        parents=["bmi", "body-fat-disorders"],
    ),
    Choice(
        sid="class-1-obesity",
        description="BMI 30 to 34.9 kg/m^2. ",
        annotations=[
            # (https://www.ncbi.nlm.nih.gov/books/NBK541070/),
        ],
        parents=["obesity"],
    ),
    Choice(
        sid="class-2-obesity",
        description="BMI 30 to 34.9 kg/m^2. ",
        annotations=[
            # (https://www.ncbi.nlm.nih.gov/books/NBK541070/),
        ],
        parents=["obesity"],
    ),
    Choice(
        sid="class-3-obesity",
        description="BMI greater than or equal to 40 kg/m^2. ",
        synonyms=["Severe obesity", "Extreme obesity", "Massive obesity"],
        annotations=[
            (BQB.IS, "ncit/C178882"),
        ],
        parents=["obesity"],
    ),
]
