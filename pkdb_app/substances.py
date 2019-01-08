"""
Handling of substance information.

FIXME: add types, molecular weights and links to data bases

To update the database content execute the setup_database script.
"""

SUBSTANCES_DATA = [
    # indocyanogreen/icg
    "indocyanogreen",

    # acetaminophen/paracetamol
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
    "cimetidine",
    "fluvoxamine",
    "disulfiram",
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
    "codeine-6-glucuronide",
    "norcodeine",
    "norcodeine-glucuronide",
    "codeine/morphine",
    "morphine/codine",
    "(Mor+M3G+M6G)/(Cod+C6G)",
    "morphine+M3G+M6G",
    "M+N+C-6-G",
    "quinidine",
    # medication
    "salbutamol",
    "beclometasone",
    "enalapril",
    "diltiazem",
    "hydrochlorthiazide",
    "amiloride",
    "chlordiazepoxide",
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
    "morphine-3-glucuronide",
    "morphine-6-glucuronide",
    "normorphine",
    "normorphine-glucuronide",
    "norcodeine-conjugates",
    "diclofenac",
    "glycerol",
    "FFA",
    "carbamazepine",
    # midazolam
    "metropolol",
    "warfarin",
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

    # ----------------------
    # glucose metabolism
    # ----------------------
    'glucose',
    'lactate',
    '[2-3H]glucose',
    '[6-3H]glucose',
    '[U-13C]glucose',
    '[3-OMG]glucose',
    'insulin',
    'c-peptide',
    'cortisol',
    'epinephrine',
    'norepinephrine',
    'cortisol',
    'growth hormone',
    'glucagon',
    'TAA',  # total amino acids
    'EAA',  # essential amino acids
    'NEAA',  # non-essential amino acids
    'BCAA',  # branch-chained amino acids
    'exenatide',  # GLP1 analoque
    'GIP',
    'GLP-1',
    'insulin/glucose',
]

SUBSTANCES_DATA_CHOICES = [(t, t) for t in SUBSTANCES_DATA]
