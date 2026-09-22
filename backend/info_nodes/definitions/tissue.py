"""Definition of tissues."""

from pymetadata.core.miriam import BQB

from ..node import DType, InfoNode, Tissue

TISSUE_NODES: list[InfoNode] = [
    Tissue(
        sid="tissue",
        description="Tissue information, part of the body (fluid or tissue)",
        parents=[],
        dtype=DType.ABSTRACT,
        annotations=[(BQB.IS, "NCIT:C12801")],
    ),
    Tissue(
        sid="nr-tissue",
        name="NR",
        label="Not reported (tissue)",
        description="Tissue not reported.",
        parents=["tissue"],
        annotations=[],
    ),
    Tissue(
        sid="blood",
        description="Blood (normally venous). A liquid tissue; its major function is to transport oxygen "
        "throughout the body. It also supplies the tissues with nutrients, "
        "removes waste products, and contains various components of the "
        "immune system defending the body against infection. (see also "
        "'serum' and 'plasma'). See also 'arterial blood'.",
        parents=["tissue"],
        annotations=[
            (BQB.IS, "NCIT:C12434"),
            (BQB.IS, "bto/BTO:0000089"),
        ],
    ),
    Tissue(
        sid="dried-blood-spot",
        name="dried blood spot",
        description="Capillary blood collected on blotting paper, typically from heel "
        "or finger stick.",
        parents=["tissue"],
        annotations=[
            (BQB.IS, "NCIT:C113746"),
            (BQB.IS, "SNOMEDCT:440500007"),
        ],
    ),
    Tissue(
        sid="arterial-blood",
        name="arterial blood",
        description="Arterial blood.",
        parents=["blood"],
        annotations=[
            (BQB.IS_VERSION_OF, "NCIT:C12434"),
            (BQB.IS_VERSION_OF, "bto/BTO:0000089"),
        ],
    ),
    Tissue(
        sid="breath",
        description="Breath. The air that is inhaled and exhaled during respiration.",
        parents=["tissue"],
        annotations=[(BQB.IS, "NCIT:C94552")],
    ),
    Tissue(
        sid="inferior-vena-cava",
        name="inferior vena cava",
        description="Trunk of systemic vein which is formed by the union of the right "
        "common iliac vein and the left common iliac vein and terminates "
        "in the right atrium.",
        parents=["tissue"],
        annotations=[(BQB.IS, "fma/FMA:10951")],
    ),
    Tissue(
        sid="aorta",
        name="aorta",
        description="The main artery of the circulatory system which carries "
        "oxygenated blood from the heart to all the arteries of the body "
        "except those of the lungs.",
        parents=["tissue"],
        annotations=[
            (BQB.IS, "uberon/UBERON:0000947"),
            (BQB.IS, "bto/BTO:0000135"),
        ],
    ),
    Tissue(
        sid="carotid-artery",
        name="carotid artery",
        description="A key artery located in the front of the neck that carries blood "
        "from the heart to the brain. Cholesterol plaques on the inner "
        "wall of the carotid artery can lead to stroke.",
        parents=["tissue"],
        annotations=[
            (BQB.IS, "uberon/UBERON:0005396"),
            (BQB.IS, "bto/BTO:0000168"),
        ],
    ),
    Tissue(
        sid="cerebrospinal-fluid",
        name="cerebrospinal fluid",
        description="Cerebrospinal fluid. A clear, colorless, bodily fluid, that occupies "
        "the subarachnoid space and the ventricular system around and "
        "inside the brain and spinal cord.",
        parents=["tissue"],
        annotations=[
            (BQB.IS, "NCIT:C12692"),
            (BQB.IS, "bto/BTO:0000237"),
        ],
    ),
    Tissue(
        sid="plasma",
        description="Plasma (venous plasma). Plasma is the fluid (noncellular) portion of the "
        "circulating blood, as distinguished from the serum that is the "
        "fluid portion of the blood obtained by removal of the fibrin clot and "
        "blood cells after coagulation. (see also 'blood' and 'serum')",
        parents=["tissue"],
        annotations=[
            (BQB.IS, "NCIT:C13356"),
            (BQB.IS, "bto/BTO:0000131"),
        ],
        synonyms=["blood plasma"],
    ),
    Tissue(
        sid="arterial-plasma",
        name="arterial plasma",
        description="Arterial plasma.",
        parents=["plasma"],
        annotations=[
            (BQB.IS_VERSION_OF, "NCIT:C13356"),
            (BQB.IS_VERSION_OF, "bto/BTO:0000131"),
        ],
        synonyms=["blood plasma"],
    ),
    Tissue(
        sid="saliva",
        description="Saliva. The watery fluid in the mouth made by the salivary glands. "
        "Saliva moistens food to help digestion and it helps protect the "
        "mouth against infections.",
        parents=["tissue"],
        annotations=[
            (BQB.IS, "NCIT:C13275"),
            (BQB.IS, "bto/BTO:0001202"),
            (BQB.IS, "fma/FMA:59862"),
        ],
    ),
    Tissue(
        sid="saliva/plasma",
        name="saliva/plasma",
        description="helper tissue for a ratios between saliva and plasma measurements.",
        parents=["tissue"],
        annotations=[],
        deprecated=True,  # FIXME better encoding of ratios between tissues
    ),
    Tissue(
        sid="serum",
        description="Serum. The clear portion of the blood that remains after the removal "
        "of the blood cells and the clotting proteins. (see also "
        "'blood' and 'plasma')",
        parents=["tissue"],
        annotations=[
            (BQB.IS, "NCIT:C13325"),
            (BQB.IS, "bto/BTO:0001239"),
        ],
        synonyms=["blood serum"],
    ),
    Tissue(
        sid="spinal-fluid",
        name="spinal fluid",
        description="measurement of substance in spinal fluid "
        "(see also 'cerebrospinal fluid').",
        parents=["cerebrospinal fluid"],
        annotations=[
            (BQB.IS_VERSION_OF, "NCIT:C12692"),
            (BQB.IS_VERSION_OF, "bto/BTO:0000237"),
        ],
    ),
    Tissue(
        "urine",
        description="Urine. The fluid that is excreted by the kidneys. It is stored in "
        "the bladder and discharged through the urethra.",
        parents=["tissue"],
        annotations=[
            (BQB.IS, "NCIT:C13283"),
            (BQB.IS, "bto/BTO:0001419"),
            (BQB.IS, "fma/FMA:12274"),
        ],
    ),
    Tissue(
        sid="bile-duct",
        name="bile duct",
        description="Bile duct. Any of the ducts conveying bile between the liver and the "
        "intestine, including hepatic, cystic, and common bile duct.",
        parents=["tissue"],
        annotations=[
            (BQB.IS, "NCIT:C12376"),
            (BQB.IS, "bto/BTO:0001419"),
        ],
    ),
    Tissue(
        sid="bile-fluid",
        name="bile",
        label="bile",
        description="Fluid composed of waste products, bile acids, salts, cholesterol, and electrolytes."
        " It is secreted by the liver parenchyma and stored in the gallbladder.",
        parents=["tissue"],
        annotations=[
            (BQB.IS, "NCIT:C13192"),
        ],
    ),
    Tissue(
        sid="gallbladder",
        name="gallbladder",
        description="Organ with organ cavity which is continuous proximally with the "
        "cystic duct and distally terminates in the fundus of the "
        "gallbladder.",
        parents=["tissue"],
        annotations=[
            (BQB.IS, "fma/FMA:7202"),
        ],
    ),
    Tissue(
        "stomach",
        description="Stomach. An organ located under the diaphragm, between the liver "
        "and the spleen as well as between the esophagus and the small "
        "intestine. The stomach is the primary organ of food digestion.",
        parents=["tissue"],
        annotations=[
            (BQB.IS, "NCIT:C12391"),
            (BQB.IS, "bto/BTO:0001307"),
            (BQB.IS, "fma/FMA:7148"),
        ],
        synonyms=["intragastric"],
    ),
    Tissue(
        "spleen",
        description="Spleen. An organ that is part of the hematopoietic and immune "
        "systems. It is composed of the white pulp and the red pulp and "
        "is surrounded by a capsule. It is located in the left "
        "hypochondriac region. Its functions include lymphocyte production, "
        "blood cell storage, and blood cell destruction.",
        parents=["tissue"],
        annotations=[
            (BQB.IS, "NCIT:C12432"),
            (BQB.IS, "bto/BTO:0001281"),
            (BQB.IS, "uberon/UBERON:0002106"),
            (BQB.IS, "fma/FMA:7196"),
        ],
    ),
    Tissue(
        "intestine",
        description="Intestine. The portion of the gastrointestinal tract between the "
        "stomach and the anus. It includes the small intestine and large "
        "intestine.",
        parents=["tissue"],
        annotations=[
            (BQB.IS, "NCIT:C12736"),
            (BQB.IS, "bto/BTO:0000648"),
            (BQB.IS, "fma/FMA:7199"),
        ],
        synonyms=["intestines", "bowel"],
    ),
    Tissue(
        sid="small-intestine",
        name="small intestine",
        description="Small intestine. The section of the intestines between the pylorus "
        "and cecum. The small intestine is approximately 20 feet long and "
        "consists of the duodenum, the jejunum, and the ileum. Its main "
        "function is to absorb nutrients from food as the food is "
        "transported to the large intestine.",
        parents=["intestine"],
        annotations=[(BQB.IS, "NCIT:C12386"), (BQB.IS, "fma/FMA:7200")],
        synonyms=[],
    ),
    Tissue(
        sid="large-intestine",
        name="large intestine",
        description="Large intestine. A muscular tube that extends from the end of the "
        "small intestine to the anus.",
        parents=["intestine"],
        annotations=[(BQB.IS, "NCIT:C12379"), (BQB.IS, "fma/FMA:7201")],
        synonyms=[],
    ),
    Tissue(
        sid="cecum",
        name="cecum",
        description="Cecum. A blind pouch-like commencement of the colon in the right "
        "lower quadrant of the abdomen at the end of the small intestine "
        "and the start of the large intestine.",
        parents=["tissue"],
        annotations=[
            (BQB.IS, "NCIT:C12381"),
            (BQB.IS, "fma/FMA:14541"),
        ],
        synonyms=["caecum"],
    ),
    Tissue(
        "muscle",
        description="Muscle. One of the contractile organs of the body.",
        parents=["tissue"],
        annotations=[
            (BQB.IS, "NCIT:C13056"),
            (BQB.IS, "bto/BTO:0000887"),
            (BQB.IS, "fma/FMA:30316"),
        ],
        synonyms=["muscles", "muscle tissue"],
    ),
    Tissue(
        "pancreas",
        description="Pancreas. An organ behind the lower part of the stomach that is "
        "the shape of a fish and about the size of a hand. It is a compound "
        "gland composed of both exocrine and endocrine tissues. ",
        parents=["tissue"],
        annotations=[
            (BQB.IS, "NCIT:C12393"),
            (BQB.IS, "bto/BTO:0000988"),
            (BQB.IS, "fma/FMA:7198"),
        ],
    ),
    Tissue(
        "liver",
        description="Liver. A triangular-shaped organ located under the diaphragm in the "
        "right hypochondrium. It is the largest internal organ of the body, "
        "weighting up to 2 kg. Metabolism and bile secretion are its main "
        "functions. It is composed of cells which have the ability to "
        "regenerate.",
        parents=["tissue"],
        annotations=[
            (BQB.IS, "NCIT:C12392"),
            (BQB.IS, "bto/BTO:0000759"),
            (BQB.IS, "fma/FMA:7197"),
        ],
    ),
    Tissue(
        sid="liver-homogenate",
        name="liver homogenate",
        description="Liver homogenate. Mainly for in vitro experiments.",
        parents=["tissue"],
        annotations=[],
    ),
    Tissue(
        "adipose",
        label="adipose tissue",
        description="Adipose tissue. Connective tissue in which fat is stored and which "
        "has the cells distended by droplets of fat.",
        parents=["tissue"],
        annotations=[
            (BQB.IS, "NCIT:C12472"),
            (BQB.IS, "bto/BTO:0001487"),
            (BQB.IS, "fma/FMA:20110"),
        ],
        synonyms=["adipose tissue"],
    ),
    Tissue(
        "heart",
        label="heart",
        description="Heart or heart tissue. A hollow organ located slightly to the "
        "left of the middle portion of the chest. It is composed of muscle "
        "and it is divided by a septum into two sides: the right side which "
        "receives de-oxygenated blood from the body and the left side which "
        "sends newly oxygenated blood to the body.",
        parents=["tissue"],
        annotations=[
            (BQB.IS, "NCIT:C12727"),
            (BQB.IS, "bto/BTO:0000562"),
            (BQB.IS, "fma/FMA:7088"),
        ],
        synonyms=["heart tissue"],
    ),
    Tissue(
        "kidney",
        description="Kidney. One of the two bean-shaped organs located on each side of "
        "the spine in the retroperitoneum. The right kidney is located below "
        "the liver and the left kidney below the diaphragm. The kidneys "
        "filter and secret the metabolic products and minerals from the "
        "blood, thus maintaining the homeostasis.",
        parents=["tissue"],
        annotations=[
            (BQB.IS, "NCIT:C12415"),
            (BQB.IS, "bto/BTO:0000671"),
            (BQB.IS, "fma/FMA:7203"),
        ],
        synonyms=["kidneys"],
    ),
    Tissue(
        "feces",
        description="The material discharged from the bowel during defecation. "
        "It consists of undigested food, intestinal mucus, epithelial cells, "
        "and bacteria.",
        parents=["tissue"],
        annotations=[
            (BQB.IS, "NCIT:C13234"),
            (BQB.IS, "bto/BTO:0000440"),
        ],
        synonyms=["faeces", "Faeces"],
    ),
    Tissue(
        "feces_urine",
        description="Combination of urine and faeces (e.g. in recovery studies).",
        parents=["tissue"],
        annotations=[
            (BQB.HAS_PART, "NCIT:C13234"),
            (BQB.HAS_PART, "bto/BTO:0000440"),
            (BQB.HAS_PART, "NCIT:C13283"),
            (BQB.HAS_PART, "bto/BTO:0001419"),
            (BQB.HAS_PART, "fma/FMA:12274"),
        ],
        synonyms=["faeces and urine"],
    ),
    Tissue(
        "feces_urine_bile",
        description="Combination of urine, faeces and bile (e.g. in recovery studies).",
        parents=["tissue"],
        annotations=[
            (BQB.HAS_PART, "NCIT:C13234"),
            (BQB.HAS_PART, "bto/BTO:0000440"),
            (BQB.HAS_PART, "NCIT:C13283"),
            (BQB.HAS_PART, "bto/BTO:0001419"),
            (BQB.HAS_PART, "fma/FMA:12274"),
        ],
        synonyms=["faeces and urine and bile"],
    ),
    Tissue(
        "erythrocyte",
        description="Any of the hemoglobin-containing cells that carry oxygen to the "
        "tissues and are responsible for the red color of vertebrate blood.",
        parents=["tissue"],
        annotations=[
            (BQB.IS, "NCIT:C12521"),
            (BQB.IS, "bto/BTO:0000424"),
        ],
        synonyms=["red blood cell"],
    ),
]
