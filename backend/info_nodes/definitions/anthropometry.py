"""Definition of anthropometric measurements."""

from pymetadata.core.miriam import BQB

from ..node import Choice, DType, InfoNode, MeasurementType

ANTHROPOMETRY_NODES: list[InfoNode] = [
    MeasurementType(
        sid="anthropometric-measurement",
        name="anthropometric measurement",
        description="Anthropometry is a measurement of the size, weight, and "
        "proportions of the human or other primate body.",
        parents=["physiological measurement"],
        dtype=DType.ABSTRACT,
        annotations=[
            (BQB.IS, "efo/0004302"),
            (BQB.IS, "omit/0002288"),
        ],
    ),
    MeasurementType(
        sid="age",
        description="Age of subject or animal. How long something has existed; "
        "elapsed time since birth.",
        parents=["anthropometric measurement"],
        dtype=DType.NUMERIC,
        units=["yr"],
        annotations=[
            (BQB.IS, "NCIT:C25150"),
            (BQB.IS, "efo/0000246"),
            (BQB.IS, "sio/SIO_001013"),
        ],
    ),
    MeasurementType(
        sid="age-categorial",
        name="age (categorial)",
        description="Age of subject or animal in age classes.",
        parents=["anthropometric measurement"],
        dtype=DType.CATEGORICAL,
        annotations=[
            (BQB.IS_VERSION_OF, "NCIT:C25150"),
            (BQB.IS_VERSION_OF, "efo/0000246"),
        ],
    ),
    Choice(
        sid="elder",
        description="Elder. Normally in the range >65 years. An age group comprised of "
        "individuals 65 years of age and older.",
        parents=["age (categorial)"],
        annotations=[
            (BQB.IS, "NCIT:C16268"),
        ],
        synonyms=["Elderly", "elderly", "geriatric"],
    ),
    Choice(
        sid="adult",
        description="Adult. Normally in the range 35 - 65 years. An age group "
        "comprised of humans who have reached reproductive age.",
        parents=["age (categorial)"],
        annotations=[
            (BQB.IS, "NCIT:C17600"),
            (BQB.IS, "omit/0001757"),
        ],
        synonyms=["mature individual", "middle-aged"],
    ),
    Choice(
        sid="young",
        description="Young subject. Normally in the range 18 - 35 years",
        parents=["age (categorial)"],
        annotations=[
            (BQB.IS, "omit/0026488"),
        ],
        synonyms=["young adult"],
    ),
    Choice(
        sid="adolescent",
        description="Adolescent. Normally in the range <18. An age group comprised "
        "of juveniles between the onset of puberty and maturity; in the "
        "state of development between puberty and maturity.",
        parents=["age (categorial)"],
        annotations=[
            (BQB.IS, "NCIT:C27954"),
            (BQB.IS, "omit/0001723"),
        ],
    ),
    Choice(
        sid="child",
        description="Child. An age group comprised of individuals who are not yet an "
        "adult. The specific cut-off age will vary by purpose. A young "
        "person who is between infancy and adulthood.",
        parents=["age (categorial)"],
        annotations=[
            (BQB.IS, "NCIT:C16423"),
            (BQB.IS, "omit/0003972"),
        ],
        synonyms=["juvenile"],
    ),
    Choice(
        sid="newborn",
        description="Newborn.",
        parents=["age (categorial)"],
        annotations=[(BQB.IS, "NCIT:C16731")],
        synonyms=["neonatal", "neonate"],
    ),
    MeasurementType(
        sid="sex",
        description="Sex of subject or animal. The assemblage of physical properties "
        "or qualities by which male is distinguished from female; "
        "the physical difference between male and female; the "
        "distinguishing peculiarity of male or female.",
        parents=["anthropometric measurement"],
        dtype=DType.CATEGORICAL,
        annotations=[
            (BQB.IS, "NCIT:C28421"),
            (BQB.IS, "omit/0013619"),
        ],
        synonyms=["gender"],
    ),
    Choice(
        sid="male",
        name="M",
        label="male",
        description="Male is a biological sex of an individual with "
        "male sexual organs.",
        parents=["sex"],
        annotations=[
            (BQB.IS, "NCIT:C20197"),
            (BQB.IS, "sio/SIO_010048"),
        ],
        synonyms=["man", "men"],
    ),
    Choice(
        sid="female",
        name="F",
        label="female",
        description="Female is a biological sex of an individual with female "
        "sexual organs.",
        parents=["sex"],
        annotations=[
            (BQB.IS, "NCIT:C166576"),
            (BQB.IS, "sio/SIO_010052"),
        ],
        synonyms=["woman", "women"],
    ),
    Choice(
        sid="mixed-sex",
        name="MF",
        label="male and female",
        description="Males and females without exact count. Mixed sex allows to "
        "encode that men and women participated in a group.",
        parents=["sex"],
        synonyms=["male and female"],
    ),
    MeasurementType(
        sid="height",
        description="Height of subject or animal. The vertical measurement or distance "
        "from the base to the top of an object; the vertical dimension of "
        "extension.",
        parents=["anthropometric measurement"],
        dtype=DType.NUMERIC,
        units=["m"],
        annotations=[
            (BQB.IS, "NCIT:C25347"),
            (BQB.IS, "efo/0004339"),
        ],
        synonyms=["size"],
    ),
    MeasurementType(
        sid="bmi",
        label="body mass index (BMI)",
        description="Body mass index (BMI) calculated as weight/height^2. An "
        "indicator of body density. For adults, BMI falls into "
        "these categories: "
        "below 18.5 (underweight); 18.5-24.9 (normal); "
        "25.0-29.9 (overweight); 30.0 and above (obese). "
        "See also `weight (categorial)` to encode these categories.",
        parents=["anthropometric measurement"],
        dtype=DType.NUMERIC,
        units=["kg/m^2"],
        annotations=[
            (BQB.IS, "NCIT:C16358"),
            (BQB.IS, "efo/0004340"),
            (BQB.IS, "omit/0016586"),
        ],
        synonyms=["bmi", "BMI", "body mass index"],
    ),
    MeasurementType(
        sid="weight-status",
        name="weight status",
        description="Information related to the body weight of subject or animal.",
        parents=["anthropometric measurement"],
        dtype=DType.ABSTRACT,
        annotations=[
            (BQB.IS, "efo/0004338"),
            (BQB.IS, "NCIT:C25208"),
        ],
    ),
    MeasurementType(
        sid="weight",
        description="Body weight of subject or animal. The mass or quantity of "
        "heaviness of an individual. It is expressed by units of kilograms "
        "or pounds.",
        parents=["weight status"],
        dtype=DType.NUMERIC,
        units=["kg"],
        annotations=[
            (BQB.IS, "efo/0004338"),
            (BQB.IS, "NCIT:C25208"),
            (BQB.IS, "https://bioregistry.io/CMO:0000012"),
        ],
        synonyms=["body weight"],
    ),
    MeasurementType(
        sid="weight (change)",
        description="Body weight change of subject or animal.",
        parents=["weight status"],
        dtype=DType.NUMERIC,
        units=["kg"],
        annotations=[
            (BQB.IS_VERSION_OF, "efo/0004338"),
            (BQB.IS_VERSION_OF, "NCIT:C25208"),
            (BQB.IS_VERSION_OF, "https://bioregistry.io/CMO:0000012"),
        ],
        synonyms=["body weight (change)"],
    ),
    MeasurementType(
        sid="weight (change relative)",
        description="Body weight relative change of subject or animal in percent.",
        parents=["weight status"],
        dtype=DType.NUMERIC,
        units=["percent"],
        annotations=[
            (BQB.IS_VERSION_OF, "efo/0004338"),
            (BQB.IS_VERSION_OF, "NCIT:C25208"),
            (BQB.IS_VERSION_OF, "https://bioregistry.io/CMO:0000012"),
        ],
        synonyms=["body weight relative (change)"],
    ),
    MeasurementType(
        sid="weight-categorial",
        name="weight (categorial)",
        description="body weight as class often defined via body mass index: "
        "below 18.5 (underweight); 18.5-24.9 (normal); "
        "25.0-29.9 (overweight); 30.0 and above (obese). "
        "(see also `bmi`).",
        parents=["weight status"],
        dtype=DType.CATEGORICAL,
        annotations=[
            (BQB.IS_VERSION_OF, "efo/0004338"),
            (BQB.IS_VERSION_OF, "NCIT:C25208"),
        ],
    ),
    Choice(
        sid="obese",
        description="Subject is obese. Weighing well above a person's ideal weight. "
        "Often defined via BMI 30.0 and above. "
        "See also `obesity index` and `body fat percentage`.",
        parents=["weight (categorial)"],
        annotations=[
            (BQB.IS, "NCIT:C159658"),
            (BQB.IS, "efo/0007041"),
        ],
        synonyms=["obesity"],
    ),
    Choice(
        sid="overweight",
        description="Subject is overweight. Often defined via BMI 25.0-29.9. "
        "See also `obesity index` and `body fat percentage`.",
        parents=["weight (categorial)"],
        annotations=[
            (BQB.IS, "NCIT:C94250"),
            (BQB.IS, "efo/0005935"),
            (BQB.IS, "HP:0025502"),
        ],
        synonyms=["increased weight"],
    ),
    Choice(
        sid="normal-weight",
        name="normal",
        label="normal weight",
        description="Subject is normal weight. Often defined via BMI 18.5-24.9. "
        "See also `obesity index` and `body fat percentage`.",
        parents=["weight (categorial)"],
    ),
    Choice(
        sid="underweight",
        description="Subject is underweight. Often defined via BMI below 18.5. "
        "See also `obesity index` and `body fat percentage`.",
        parents=["weight (categorial)"],
        annotations=[(BQB.IS, "efo/0005936")],
    ),
    MeasurementType(
        sid="body-surface-area",
        name="body surface area",
        label="body surface area (BSA)",
        description="Body surface area (BSA) of subject or animal. A measure of the "
        "2-dimensional extent of the body surface (i.e., the skin). "
        "Body surface area (BSA) can be calculated by mathematical formula or "
        "from a chart that relates height to weight. BSA is often an important "
        "factor in dosing.",
        parents=["anthropometric measurement"],
        dtype=DType.NUMERIC,
        units=["m^2"],
        annotations=[(BQB.IS, "NCIT:C25157"), (BQB.IS, "omit/0003188")],
        synonyms=["BSA", "body surface area"],
    ),
    MeasurementType(
        sid="waist-circumference",
        name="waist circumference",
        description="Waist circumference. A circumferential measurement of the waist, "
        "which may be classified as the area immediately below the lowest "
        "rib, at the narrowest part of the torso, midpoint between the lowest "
        "rib and the iliac crest, or immediately above the iliac crest.",
        parents=["anthropometric measurement"],
        dtype=DType.NUMERIC,
        units=["cm"],
        annotations=[
            (BQB.IS, "NCIT:C100948"),
            (BQB.IS, "efo/0004342"),
            (BQB.IS, "https://bioregistry.io/CMO:0000242"),
        ],
    ),
    MeasurementType(
        sid="waist-to-hip-ratio",
        name="waist to hip ratio",
        description="Waist to hip ratio (WHR). The ratio of the abdominal "
        "circumference at the navel to maximum hip and buttocks "
        "circumference; looks at "
        "the proportion of fat stored on the body around the waist and hip. "
        "Carrying extra weight around the waist is a greater health risk "
        "than carrying extra weight around the hips or thighs.",
        parents=["anthropometric measurement"],
        dtype=DType.NUMERIC,
        units=["percent"],
        annotations=[
            (BQB.IS, "NCIT:C17651"),
            (BQB.IS, "efo/0004343"),
            (BQB.IS, "https://bioregistry.io/CMO:0000020"),
        ],
    ),
    MeasurementType(
        sid="lean-body-mass",
        name="lean body mass",
        label="lean body mass (LBW)",
        description="Lean body mass or fat free mass (FFM). Weight of lean body mass "
        "without additional fat. See also `percent fat`.",
        parents=["anthropometric measurement"],
        dtype=DType.NUMERIC,
        units=["kg"],
        annotations=[
            (BQB.IS, "NCIT:C71258"),
            (BQB.IS, "efo/0004995"),
        ],
        synonyms=["LBM", "fat free mass", "FFM"],
    ),
    MeasurementType(
        sid="body-fat-percentage",
        name="body fat percentage",
        description="Amount of fat in percent of whole-body weight. "
        "Formerly `percent fat`",
        parents=["anthropometric measurement"],
        dtype=DType.NUMERIC,
        units=["percent"],
        annotations=[
            (BQB.IS, "NCIT:C139218"),
        ],
    ),
    MeasurementType(
        sid="obesity-index",
        name="obesity index",
        description="Obesity index (percent of normal body weight or ideal body "
        "weight - IBW). Values "
        ">100% or >1.0 indicate overweight, values <100% or <1.0 "
        "indicate underweight. See also `obese`.",
        parents=["anthropometric measurement"],
        dtype=DType.NUMERIC,
        units=["percent"],
        synonyms=["IBW", "ideal body weight"],
    ),
    MeasurementType(
        sid="fat-free-mass-index",
        name="fat free mass index",
        label="fat free mass index (FFMI)",
        description="Portion of the body not comprised of lipids often calculated as "
        "fat free mass equal to "
        "fat free mass divided by height squared.",
        parents=["anthropometric measurement"],
        dtype=DType.NUMERIC,
        units=["kg/m^2"],
        annotations=[(BQB.IS, "https://bioregistry.io/CMO:0000306")],
        synonyms=["FFMI"],
    ),
]
