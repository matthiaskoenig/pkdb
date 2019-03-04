"""
Handling of substance information.

FIXME: add types, molecular weights and links to data bases

To update the database content execute the setup_database script.
"""

class Substance(object):
    def __init__(self, sid, name=None, parents=None, chebi=None, synonyms=None):
        self.sid = sid
        self._name = name
        self.parents = parents
        self.chebi = chebi
        self.synonyms = synonyms

    @property
    def name(self):
        if self._name:
            return self._name
        else:
            return self.sid
    @property
    def stype(self):
        if self.parents:
            return "derived"
        else:
            return "basic"


SUBSTANCES_DATA = [

    # indocyanogreen/icg
    Substance(sid="icg", name="indocyanine green", chebi="CHEBI:31696"),

    # acetaminophen/paracetamol
    Substance(sid="apap",  name="paracetamol", chebi="CHEBI:46195", synonyms=["acetaminophen"]),
    Substance(sid="panadol extend",  name="panadol extend", synonyms=[]),
    Substance(sid="apapglu",  name="paracetamol glucuronide", chebi="CHEBI:32636", synonyms=["acetaminophen O-β-D-glucosiduronic acid"]),
    Substance(sid="apapsul",  name="paracetamol sulfate", chebi="CHEBI:32635", synonyms=["4-acetaminophen sulfate"]),
    Substance(sid="apapcys",  name="paracetamol cysteine conjugate", chebi="CHEBI:133066", synonyms=["S-(5-acetamido-2-hydroxyphenyl)cysteine"]),

    # caffeine (CYP2A1)
    Substance(sid="caf", name="caffeine", chebi="CHEBI:27732", synonyms=["1,3,7-TMX"]),
    Substance(sid="px", name="paraxanthine", chebi="CHEBI:25858", synonyms=["1,7-dimethylxanthine", "1,7-DMX", "17X"]),
    Substance(sid="tp", name="theophylline", chebi="CHEBI:28177", synonyms=["1,3-dimethylxanthine", "1,3-DMX", "13X"]),
    Substance(sid="tb", name="theobromine", chebi="CHEBI:28946", synonyms=["3,7-dimethylxanthine", "3,7-DMX", "37X"]),
    Substance(sid="AFMU", name="AFMU", chebi="CHEBI:32643"),
    Substance(sid="AAMU", name="AAMU", chebi="CHEBI:80473"),
    Substance(sid="1U", name="1U", synonyms=["1-methyluric acid"]),
    Substance(sid="17U", name="17U", chebi="CHEBI:68449", synonyms=["1,7-dimethyluric acid", "1,7 DMU"]),
    Substance(sid="1X", name="1X", chebi="CHEBI:68444"),
    Substance(sid="MX", name="methylxanthine"),

    # caffeine derived
    Substance(sid="caf/px", parents=["paraxanthine", "caffeine"]),
    Substance(sid="px/caf", parents=["paraxanthine", "caffeine"]),
    Substance(sid="tb/caf", parents=["theobromine", "caffeine"]),
    Substance(sid="tp/caf", parents=["theophylline", "caffeine"]),
    Substance(sid="1X/caf", parents=["1X", "caffeine"]),
    Substance(sid="1X/px", parents=["1X", "paraxanthine"]),
    Substance(sid="1X/tp", parents=["1X", "theophylline"]),
    Substance(sid="(AFMU+1U+1X)/17U", parents=["AFMU", "1U", "1X", "17U"]),
    Substance(sid="(AAMU+1U+1X)/17U", parents=["AAMU", "1U", "1X", "17U"]),
    Substance(sid="17U/px", parents=["17U", "paraxanthine"]),
    Substance(sid="1U/(1U+1X)", parents=["1U", "1X"]),
    Substance(sid="1U/1X", parents=["1U", "1X"]),
    Substance(sid="AFMU/(AFMU+1U+1X)", parents=["AFMU", "1U", "1X"]),
    Substance(sid="AAMU/(AAMU+1U+1X)", parents=["AAMU", "1U", "1X"]),

    # caffeine interaction
    Substance(sid="cimetidine", chebi="CHEBI:3699"),
    Substance(sid="fluvoxamine", chebi="CHEBI:5138"),
    Substance(sid="disulfiram", chebi="CHEBI:4659"),
    Substance(sid="naringenin", chebi="CHEBI:50202"),
    Substance(sid="grapefruit juice"),
    Substance(sid="quinolone", chebi="CHEBI:23765"),
    Substance(sid="pipemidic acid", chebi="CHEBI:75250"),
    Substance(sid="norfloxacin", chebi="CHEBI:100246"),
    Substance(sid="enoxacin", chebi="CHEBI:157175"),
    Substance(sid="ciprofloxacin", chebi="CHEBI:100241"),
    Substance(sid="ofloxacin", chebi="CHEBI:7731"),

    # oral contraceptives
    Substance(sid="levonorgestrel", chebi="CHEBI:6443"),
    Substance(sid="gestodene", chebi="CHEBI:135323"),
    Substance(sid="EE2", name="ethinylestradiol"),

    # codeine/morphine
    Substance(sid="cod", name="codeine", chebi="CHEBI:16714"),
    Substance(sid="c6g", name="codeine-6-glucuronide",chebi="CHEBI:80580",),
    Substance(sid="ncod", name="norcodeine", chebi="CHEBI:80579"),
    Substance(sid="ncg", name="norcodeine-glucuronide"),
    Substance(sid="ncc", name="norcodeine-conjugates"),
    Substance(sid="mor", name="morphine",chebi="CHEBI:17303"),
    Substance(sid="m3g", name="morphine-3-glucuronide", chebi="CHEBI:80631"),
    Substance(sid="m6g", name="morphine-6-glucuronide",chebi="CHEBI:80581"),
    Substance(sid="nmor", name="normorphine", chebi="CHEBI:7633"),
    Substance(sid="nmg", name="normorphine-glucuronide"),

    # codeine/morphine derived
    Substance(sid="cod/mor", parents=["codeine", "morphine"]),
    Substance(sid="mor/cod", parents=["codeine", "morphine"]),

    Substance(sid="(mor+m3g+m6g)/(cod+c6g)",
              parents=["codeine",
                       "codeine-6-glucuronide",
                       "morphine",
                       "morphine-3-glucuronide",
                       "morphine-6-glucuronide"],
              ),
    Substance(sid="mor+m3g+m6g",
              parents=["morphine", "morphine-3-glucuronide","morphine-6-glucuronide"],
        ),

    Substance(sid="mor+m3g+m6g+nmor+cod+ncod+c6g+ncg",
              parents=["morphine",
                       "morphine-3-glucuronide",
                       "morphine-6-glucuronide",
                       "normorphine",
                       "codeine",
                       "norcodeine",
                       "codeine-6-glucuronide",
                       "norcodeine-glucuronide"],
        ),

    Substance(sid="mor+ncod+c6g", parents=["morphine", "norcodeine", "codeine-6-glucuronide"]),

    Substance(sid="cod/(mor+m3g+m6g+nmor)",
              parents=["morphine",
                       "morphine-3-glucuronide",
                       "morphine-6-glucuronide",
                       "normorphine",
                       "codeine"],
        ),

    Substance(sid="cod/(ncod+ncg+nmor)",  #N-demethylation
              parents=["codeine", "norcodeine", "norcodeine-glucuronide", "normorphine"],
        ),

    Substance(sid="cod/c6g",  parents=["codeine", "codeine-6-glucuronide"]),# N-demethylation

    # CYP2D6 related
    Substance(sid = "qui", name="quinidine", chebi="CHEBI:28593"),

    Substance(sid = "deb", name="debrisoquine", chebi="CHEBI:34665"), #CYP2D6 Phenotyping
    Substance(sid = "4hdeb", name="4-hydroxydebrisoquine",chebi="CHEBI:63800"), #CYP2D6 Phenotyping
    Substance(sid="deb/4hdeb", parents=["debrisoquine", "4-hydroxydebrisoquine"]),

    Substance(sid ="mep", name="mephenytoin",chebi="CHEBI:6757"),  # CYP2D6 Phenotyping

    Substance(sid ="spar", name="sparteine", chebi="CHEBI:28827"),  # CYP2D6 Phenotyping
    Substance(sid ="2hspar", name="2-dehydrosparteine",chebi="CHEBI:29130"),  # CYP2D6 Phenotyping
    Substance(sid ="5hspar", name="5-dehydrosparteine"),  # soon avialble, chebi="CHEBI:143195"),  # CYP2D6 Phenotyping # Molecular Weight: 232.371 g/mol

    # for phenotyping
    Substance(sid="spar/(2hspar+5hspar)", parents=["sparteine", "2-dehydrosparteine","5-dehydrosparteine"],
        ),



    # medication
    Substance(sid="salbutamol", chebi="	CHEBI:8746"),
    Substance(sid="beclometasone",chebi="CHEBI:3001",),
    Substance(sid="enalapril", chebi="CHEBI:4784"),
    Substance(sid="diltiazem", chebi="CHEBI:101278"),
    Substance(sid="hydrochlorothiazide",chebi="CHEBI:5778"),
    Substance(sid="amiloride",chebi="CHEBI:2639"),


    # chlorzoxazone (CYP2E1)
    Substance(sid="chlordiazepoxide"),
    Substance(sid="6-hydroxychlorzoxazone"),

    # misc
    Substance(sid="tizanidine"),
    Substance(sid="venlafaxine"),
    Substance(sid="lomefloxacin"),
    Substance(sid="ephedrine"),
    Substance(sid="pseudoephedrine"),
    Substance(sid="ibuprofen"),
    Substance(sid="aspirin"),
    Substance(sid="enoxacin"),
    Substance(sid="pipemidic acid"),
    Substance(sid="norfloxacin"),
    Substance(sid="ofloxacin"),
    Substance(sid="fluvoxamine"),
    Substance(sid="ethanol"),
    Substance(sid="chlorzoxazone"),
    Substance(sid="lomefloxacin"),
    Substance(sid="aminopyrine"),
    Substance(sid="antipyrine"),
    Substance(sid="bromsulpthalein"),
    Substance(sid="phenylalanine"),

    Substance(sid="diclofenac"),
    Substance(sid="glycerol"),
    Substance(sid="FFA"),
    Substance(sid="carbamazepine"),

    # midazolam
    Substance(sid="metropolol"),
    Substance(sid="warfarin"),
    Substance(sid="midazolam"),
    Substance(sid="1-hydroxymidazolam"),

    # losartan
    Substance(sid="losartan"),
    Substance(sid="exp3174"),

    # omeprazole (CYP2C19)
    Substance(sid="omeprazole"),
    Substance(sid="5-hydroxyomeprazole"),
    Substance(sid="5home/ome",
              parents=["omeprazole", "5-hydroxyomeprazole"],
              ),

    # dextromethorphan
    Substance(sid="dextromethorphan"),
    Substance(sid="dextrorphan"),
    Substance(sid="digoxin"),
    Substance(sid="clozapine"),
    Substance(sid="carbon monoxide"),
    Substance(sid="bromsulpthalein"),


    # other
    Substance(sid="hydrogen"),
    Substance(sid="sulfasalazine"),
    Substance(sid="sulfapyridine"),


    # ----------------------
    # glucose metabolism
    # ----------------------
    Substance(sid="glucose"),
    Substance(sid="lactate"),
    Substance(sid="[2-3H]glucose"),
    Substance(sid="[6-3H]glucose"),
    Substance(sid="[U-13C]glucose"),
    Substance(sid="[3-OMG]glucose"),
    Substance(sid="insulin"),
    Substance(sid="c-peptide"),
    Substance(sid="cortisol"),
    Substance(sid="epinephrine"),
    Substance(sid="norepinephrine"),
    Substance(sid="growth hormone"),
    Substance(sid="glucagon"),
    Substance(sid="TAA"),  # total amino acids
    Substance(sid="EAA"),  # essential amino acids
    Substance(sid="NEAA"),  # non-essential amino acids
    Substance(sid="BCAA"),  # branch-chained amino acids
    Substance(sid="exenatide"),  # GLP1 analoque
    Substance(sid="GIP"),
    Substance(sid="GLP-1"),
    Substance(sid="ins/glu", parents=["insulin", "glucose"]),
]

SUBSTANCES_DATA_CHOICES = [(t.name, t.name) for t in SUBSTANCES_DATA]
