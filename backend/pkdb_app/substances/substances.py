"""
Handling of substance information.

FIXME: add types, molecular weights and links to data bases

To update the database content execute the setup_database script.
"""
from collections import namedtuple

Substance = namedtuple("Substance", ["sid","name","parents", "chebi", "derived"])

#todo: remove chebi:None and find actual chebis and make sids
basic_substance = {"parents": None, "derived": None, "chebi": None, "sid":None}
derived_substance = {"chebi": None, "sid": None}

SUBSTANCES_DATA = [

    # indocyanogreen/icg
    Substance(name="indocyanogreen", **basic_substance),
    # acetaminophen/paracetamol
    Substance(name="acetaminophen", **basic_substance),

    # caffeine (CYP2A1)
    Substance(name="caffeine", **basic_substance),
    Substance(name="paraxanthine", **basic_substance),
    Substance(name="theophylline", **basic_substance),
    Substance(name="theobromine", **basic_substance),
    Substance(name="AFMU", **basic_substance),
    Substance(name="AAMU", **basic_substance),
    Substance(name="1U", **basic_substance),
    Substance(name="17X", **basic_substance),
    Substance(name="17U", **basic_substance),
    Substance(name="37X", **basic_substance),
    Substance(name="1X", **basic_substance),
    Substance(name="methylxanthine", **basic_substance),
    Substance(name="theobromine", **basic_substance),

    # caffeine derived
    Substance(name="caf/para", parents=["paraxanthine", "caffeine"], derived ="paraxanthine/caffeine",
              **derived_substance),
    Substance(name="para/caf", parents=["paraxanthine", "caffeine"], derived="caffeine/paraxanthine",
              **derived_substance),

    Substance(name="theobro/caf", parents=["theobromine", "caffeine"], derived="theobromine/caffeine",
              **derived_substance),

    Substance(name="theophy/caf", parents=["theophylline", "caffeine"], derived="theophylline/caffeine",
              **derived_substance),

    Substance(name="1X/caf", parents=["1X", "caffeine"], derived="1X/caffeine",
              **derived_substance),

    Substance(name="1X/para", parents=["1X", "paraxanthine"], derived="1X/paraxanthine",
              **derived_substance),

    Substance(name="1X/theophy", parents=["1X", "theophylline"], derived="1X/theophylline",
              **derived_substance),

    Substance(name="(AFMU+1U+1X)/17U", parents=["AFMU", "1U", "1X", "17U"], derived="(AFMU+1U+1X)/17U",
              **derived_substance),

    Substance(name="(AAMU+1U+1X)/17U", parents=["AAMU", "1U", "1X", "17U"], derived="(AAMU+1U+1X)/17U",
              **derived_substance),

    Substance(name="17U/17X", parents=["17U", "17X"], derived="17U/17X",**derived_substance),
    Substance(name="1U/(1U+1X)", parents=["1U", "1X"], derived="1U/(1U+1X)", **derived_substance),
    Substance(name="1U/1X", parents=["1U", "1X"], derived="1U/1X", **derived_substance),
    Substance(name="AFMU/(AFMU+1U+1X)", parents=["AFMU", "1U", "1X"], derived="AFMU/(AFMU+1U+1X)", **derived_substance),
    Substance(name="AAMU/(AAMU+1U+1X)", parents=["AAMU", "1U", "1X"], derived="AAMU/(AAMU+1U+1X)",
              **derived_substance),

    # caffeine interaction
    Substance(name="cimetidine", **basic_substance),
    Substance(name="fluvoxamine", **basic_substance),
    Substance(name="disulfiram", **basic_substance),
    Substance(name="naringenin", **basic_substance),
    Substance(name="grapefruit juice", **basic_substance),
    Substance(name="naringenin", **basic_substance),
    Substance(name="grapefruit juice", **basic_substance),
    Substance(name="quinolone", **basic_substance),
    Substance(name="pipemidic acid", **basic_substance),
    Substance(name="norfloxacin", **basic_substance),
    Substance(name="enoxacin", **basic_substance),
    Substance(name="ciprofloxacin", **basic_substance),
    Substance(name="ofloxacin", **basic_substance),

    # oral contraceptives
    Substance(name="levonorgestrel", **basic_substance),
    Substance(name="gestodene", **basic_substance),
    Substance(name="EE2", **basic_substance),

    # codeine
    Substance(name="codeine", **basic_substance),
    Substance(name="codeine-6-glucuronide", **basic_substance),
    Substance(name="norcodeine", **basic_substance),
    Substance(name="norcodeine-glucuronide", **basic_substance),
    Substance(name="norcodeine-conjugates", **basic_substance),

    # morphine
    Substance(name="morphine", **basic_substance),
    Substance(name="morphine-3-glucuronide", **basic_substance),
    Substance(name="morphine-6-glucuronide", **basic_substance),
    Substance(name="normorphine", **basic_substance),
    Substance(name="normorphine-glucuronide", **basic_substance),

    # codeine/morphine derived

    Substance(name="cod/mor",
              parents=["codeine", "morphine"],
              derived="codeine/morphine",
              **derived_substance),
    Substance(name="mor/cod",
              parents=["codeine", "morphine"],
              derived="morphine/codeine",
              **derived_substance),

    Substance(name="(mor+m3g+m6g)/(cod+c6g)",
              parents=["codeine",
                       "codeine-6-glucuronide",
                       "morphine",
                       "morphine-3-glucuronide",
                       "morphine-6-glucuronide"],
              derived="(morphine + morphine-3-glucuronide + morphine-6-glucuronide)/(codeine + codeine-6-glucuronide)",
              **derived_substance),

    Substance(name="mor+m3g+m6g",
              parents=["morphine",
                       "morphine-3-glucuronide",
                       "morphine-6-glucuronide"],
              derived="morphine + morphine-3-glucuronide + morphine-6-glucuronide",
              **derived_substance),

    Substance(name="mor+m3g+m6g+nmor+cod+ncod+c6g+ncg",
              parents=["morphine",
                       "morphine-3-glucuronide",
                       "morphine-6-glucuronide",
                       "normorphine",
                       "codeine",
                       "norcodeine",
                       "codeine-6-glucuronide",
                       "norcodeine-glucuronide"],

              derived="morphine + morphine-3-glucuronide + morphine-6-glucuronide + normorphine + "
                      "codeine + norcodeine + codeine-6-glucuronide + norcodeine-glucuronide",
              **derived_substance),

    Substance(name="mor+ncod+c6g",
              parents=["morphine", "norcodeine", "codeine-6-glucuronide"],
              derived="morphine + norcodeine + codeine-6-glucuronide",
              **derived_substance),

    Substance(name="cod/(mor+m3g+m6g+nmor)",
              parents=["morphine",
                       "morphine-3-glucuronide",
                       "morphine-6-glucuronide",
                       "normorphine",
                       "codeine"],
              derived="codeine/(morphine + morphine-3-glucuronide + morphine-6-glucuronide + normorphine)",
              **derived_substance),

    Substance(name="cod/(ncod+ncg+nmor)",  #N-demethylation
              parents=["codeine", "norcodeine", "norcodeine-glucuronide", "normorphine"],
              derived="codeine/(norcodeine + norcodeine-glucuronide + normorphine)",
              **derived_substance),

    Substance(name="cod/c6g",  # N-demethylation
              parents=["codeine", "codeine-6-glucuronide"],
              derived="codeine/codeine-6-glucuronide",
              **derived_substance),

    # CYP2D6 related
    Substance(name="quinidine", **basic_substance),

    Substance(name="debrisoquine", **basic_substance), #CYP2D6 Phenotyping
    Substance(name="4-hydroxydebrisoquine", **basic_substance), #CYP2D6 Phenotyping
    Substance(name="deb/4hdeb",
              parents=["debrisoquine", "4-hydroxydebrisoquine"],
              derived="debrisoquine/4-hydroxydebrisoquine",
              **derived_substance),

    Substance(name="mephenytoin", **basic_substance),  # CYP2D6 Phenotyping

    Substance(name="sparteine", **basic_substance),  # CYP2D6 Phenotyping
    Substance(name="2-dehydrosparteine", **basic_substance),  # CYP2D6 Phenotyping
    Substance(name="5-dehydrosparteine", **basic_substance),  # CYP2D6 Phenotyping
    Substance(name="(spar/2hspar +5hspar)",  # Metabolic Ratio of Sparteine #CYP2D6 Phenotyping
              parents=["sparteine", "2-dehydrosparteine"],
              derived="sparteine/(2-dehydrosparteine + 5-dehydrosparteine)",
              **derived_substance),

    # medication
    Substance(name="salbutamol", **basic_substance),
    Substance(name="beclometasone", **basic_substance),
    Substance(name="enalapril", **basic_substance),
    Substance(name="diltiazem", **basic_substance),
    Substance(name="hydrochlorthiazide", **basic_substance),
    Substance(name="amiloride", **basic_substance),

    # chlorzoxazone (CYP2E1)
    Substance(name="chlordiazepoxide", **basic_substance),
    Substance(name="6-hydroxychlorzoxazone", **basic_substance),

    # misc
    Substance(name="tizanidine", **basic_substance),
    Substance(name="venlafaxine", **basic_substance),
    Substance(name="lomefloxacin", **basic_substance),
    Substance(name="ephedrine", **basic_substance),
    Substance(name="pseudoephedrine", **basic_substance),
    Substance(name="ibuprofen", **basic_substance),
    Substance(name="aspirin", **basic_substance),
    Substance(name="enoxacin", **basic_substance),
    Substance(name="pipemidic acid", **basic_substance),
    Substance(name="norfloxacin", **basic_substance),
    Substance(name="ofloxacin", **basic_substance),
    Substance(name="fluvoxamine", **basic_substance),
    Substance(name="ethanol", **basic_substance),
    Substance(name="chlorozoxazone", **basic_substance),
    Substance(name="lomefloxacin", **basic_substance),
    Substance(name="aminopyrine", **basic_substance),
    Substance(name="antipyrine", **basic_substance),
    Substance(name="bromsulpthalein", **basic_substance),
    Substance(name="phenylalanine", **basic_substance),
    Substance(name="indocyanine green", **basic_substance),

    Substance(name="diclofenac", **basic_substance),
    Substance(name="glycerol", **basic_substance),
    Substance(name="FFA", **basic_substance),
    Substance(name="carbamazepine", **basic_substance),

    # midazolam
    Substance(name="metropolol", **basic_substance),
    Substance(name="warfarin", **basic_substance),
    Substance(name="midazolam", **basic_substance),
    Substance(name="1-hydroxymidazolam", **basic_substance),

    # losartan
    Substance(name="losartan", **basic_substance),
    Substance(name="exp3174", **basic_substance),

    # omeprazole (CYP2C19)
    Substance(name="omeprazole", **basic_substance),
    Substance(name="5-hydroxyomeprazole", **basic_substance),
    Substance(name="ome/5home",
              parents=["omeprazole", "5-hydroxyomeprazole"],
              derived="omeprazole/5-hydroxyomeprazole",
              **derived_substance),

    # dextromethorphan
    Substance(name="dextromethorphan", **basic_substance),
    Substance(name="dextrorphan", **basic_substance),
    Substance(name="digoxin", **basic_substance),
    Substance(name="clozapine", **basic_substance),
    Substance(name="carbon monoxide", **basic_substance),
    Substance(name="bromsulpthalein", **basic_substance),
    Substance(name="bromsulpthalein", **basic_substance),


    #other
    Substance(name="hydrogen", **basic_substance),
    Substance(name="sulfasalazine", **basic_substance),
    Substance(name="sulfapyridine", **basic_substance),


    # ----------------------
    # glucose metabolism
    # ----------------------
    Substance(name="glucose", **basic_substance),
    Substance(name="lactate", **basic_substance),
    Substance(name="[2-3H]glucose", **basic_substance),
    Substance(name="[6-3H]glucose", **basic_substance),
    Substance(name="[U-13C]glucose", **basic_substance),
    Substance(name="[3-OMG]glucose", **basic_substance),
    Substance(name="insulin", **basic_substance),
    Substance(name="c-peptide", **basic_substance),
    Substance(name="cortisol", **basic_substance),
    Substance(name="epinephrine", **basic_substance),
    Substance(name="norepinephrine", **basic_substance),
    Substance(name="growth hormone", **basic_substance),
    Substance(name="glucagon", **basic_substance),
    Substance(name="TAA", **basic_substance),  # total amino acids
    Substance(name="EAA", **basic_substance),  # essential amino acids
    Substance(name="NEAA", **basic_substance),  # non-essential amino acids
    Substance(name="BCAA", **basic_substance),  # branch-chained amino acids
    Substance(name="exenatide", **basic_substance),  # GLP1 analoque
    Substance(name="GIP", **basic_substance),
    Substance(name="GLP-1", **basic_substance),

    Substance(name="ins/glu",
              parents=["insulin", "glucose"],
              derived="insulin/glucose",
              **derived_substance),
]

SUBSTANCES_DATA_CHOICES = [(t.name, t.name) for t in SUBSTANCES_DATA]
