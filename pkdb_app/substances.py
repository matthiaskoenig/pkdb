"""
Handling of substance information.

FIXME: add types, molecular weights and links to data bases
"""

SUBSTANCES_DATA = [
    # acetaminophen
    "acetaminophen",

    # caffeine (CYP2A1)
    "caffeine",
    "paraxanthine",
    "theobromine",
    "theophylline",
    "AFMU",
    "AAMU",
    "1U",
    "17X",
    "17U",
    "37X",
    "1X",
    "methylxanthine",
    "paraxanthine/caffeine",
    "caffeine/paraxanthine",
    "theobromine/caffeine",
    "theophylline/caffeine",
    "1X/caffeine",
    "1X/paraxanthine",
    "1X/theophylline",
    "(AFMU+1U+1X)/17U",
    "(AAMU+1X+1U)/17U",
    "17U/17X",
    "1U/(1U+1X)",
    "1U/1X",
    "AFMU/(AFMU+1U+1X)",
    "AAMU/(AAMU+1U+1X)",
    # caffeine interaction
    "fluvoxamine",
    "naringenin",
    "grapefruit juice",
    "quinolone",
    "pipemidic acid",
    "norfloxacin",
    "enoxacin",
    "ciprofloxacin",
    "ofloxacin",

    # oral contraceptives
    "levonorgestrel",
    "gestodene",
    "EE2",

    # codeine
    "codeine",

    # chlorzoxazone (CYP2E1)
    "chlorzoxazone",
    "6-hydroxychlorzoxazone",

    # misc
    "tizanidine",
    "venlafaxine",
    "lomefloxacin",
    "ephedrine",
    "pseudoephedrine",

    "ibuprofen",
    "aspirin",
    "enoxacin",
    "ciprofloxacin",
    "pipemidic acid",
    "norfloxacin",
    "ofloxacin",
    "fluvoxamine",
    "ethanol",
    "chlorozoxazone",
    "lomefloxacin",

    "aminopyrine",
    "antipyrine",
    "bromsulpthalein",
    "phenylalanine",
    "indocyanine green",
    "morphine",

    "glycerol",
    "FFA",

    "carbamazepine",

    # midazolam
    "midazolam",
    "1-hydroxymidazolam",

    # losartan
    "losartan",
    "exp3174",

    # omeprazole (CYP2C19)
    "omeprazole",
    "5-hydroxyomeprazole",
    "5-hydroxyomeprazole/omeprazole",

    # dextromethorphan
    "dextromethorphan",
    "dextrorphan",

    "digoxin",
    "clozapine",

    "carbon monoxide",

]
SUBSTANCES_DATA_CHOICES = [(t, t) for t in SUBSTANCES_DATA]