"""Scientific measurement policies used when compiling vocabulary definitions."""

TIME_REQUIRED_MEASUREMENT_TYPES = [
    "concentration",
    "cumulative amount",
    "metabolic ratio",
    "cumulative metabolic ratio",
    "recovery",
    "auc_end",
    "ptf",
]

CAN_NEGATIVE = [
    "tmax",
    "concentration change",
    "concentration change absolute",
    "cumulative amount (change)",
    "blood pressure systolic (change)",
    "blood pressure systolic (change relative)",
    "blood pressure systolic auc_end (change)",
    "blood pressure diastolic (change)",
    "blood pressure diastolic (change relative)",
    "blood pressure diastolic auc_end (change)",
    "MAP (change absolute)",
    "renin activity (change absolute)",
    "heart rate (change)",
    "EHR change",
    "weight (change)",
    "hba1c (change)",
    "inr (change)",
    "prothrombin time (change)",
    "aPTT (change)",
]
