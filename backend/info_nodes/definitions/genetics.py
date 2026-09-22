"""Definition of information related to genetics."""

from ..node import Choice, DType, InfoNode, MeasurementType
from ..units import DIMENSIONLESS

GENETICS_NODES: list[InfoNode] = [
    MeasurementType(
        sid="gene-measurement",
        name="gene measurement",
        label="gene measurement",
        description="Measurement related to genotype or phenotype of gene",
        parents=["measurement"],
        dtype=DType.ABSTRACT,
    ),
    MeasurementType(
        sid="genotype",
        description="Genotype.",
        parents=["gene-measurement"],
        dtype=DType.ABSTRACT,
    ),
    MeasurementType(
        sid="gene-phenotype",
        name="gene phenotype",
        description="Gene phenotype.",
        parents=["gene-measurement"],
        dtype=DType.ABSTRACT,
    ),
    MeasurementType(
        sid="gene-variant",
        name="gene variant",
        description="Gene variant. Gene variants are larger variants such as "
        "wildtype gene or gene duplications. For genotypes see the "
        "respective genotype information.",
        parents=["gene-measurement"],
        dtype=DType.ABSTRACT,
    ),
    MeasurementType(
        sid="nat2-activity",
        name="nat2 activity",
        label="NAT2 activity",
        description="Activity score inferred from  NAT2 genotype ([*4/*4 ]-> 2 "
        ";[*5A,*5B,*5C, *6A, *7B] -> 0; [*4/x]-> 1).",
        parents=["gene-phenotype"],
        dtype=DType.CATEGORICAL,
        synonyms=[],
    ),
    Choice(
        sid="nat2-activity-0",
        name="0",
        label="0",
        description="Any of NAT2 genotype [*5A,*5B,*5C, *6A, *7B] -> 0.",
        parents=["nat2-activity"],
        synonyms=[],
    ),
    Choice(
        sid="nat2-activity-1",
        name="1",
        label="1",
        description="Any of NAT2 genotype [*4/x]-> 1. x is any of [*5A,*5B,*5C, *6A, *7B] genotypes.",
        parents=["nat2-activity"],
        synonyms=[],
    ),
    Choice(
        sid="nat2-activity-2",
        name="2",
        label="2",
        description=" NAT2 genotype *4/*4 has activity 2 ",
        parents=["nat2-activity"],
        synonyms=[],
    ),
    MeasurementType(
        sid="nat2-phenotype",
        name="nat2 phenotype",
        label="NAT2 phenotype",
        description="NAT2 gene phenotype, i.e., acetylation phenotype by N-acetyltransferase 2",
        parents=["gene-phenotype"],
        dtype=DType.CATEGORICAL,
        synonyms=[
            "N-acetyltransferase 2 phenotype",
            "N-acetyltransferase 2 genotype",
            "NAT2 genotype",
        ],
    ),
    MeasurementType(
        sid="nat2-genotype",
        name="nat2 genotype",
        label="NAT2 genotype",
        description="NAT2 gene genotype, i.e., acetylation genotype by N-acetyltransferase 2",
        parents=["genotype"],
        dtype=DType.CATEGORICAL,
        synonyms=[
            "N-acetyltransferase 2 genotype",
            "N-acetyltransferase 2 genotype",
            "NAT2 genotype",
        ],
    ),
    MeasurementType(
        sid="cyp1a2-phenotype",
        name="cyp1a2 phenotype",
        label="CYP1A2 phenotype",
        description="CYP1A2 gene phenotype.",
        parents=["gene-phenotype"],
        dtype=DType.CATEGORICAL,
    ),
    MeasurementType(
        sid="cyp2c19-phenotype",
        name="cyp2c19 phenotype",
        label="CYP2C19 phenotype",
        description="CYP2C19 metabolic phenotype. Commonly measurement either by cumulative metabolic ratios in urine "
        "or by metabolic ratios in plasma and serum.",
        parents=["gene-phenotype"],
        dtype=DType.CATEGORICAL,
    ),
    MeasurementType(
        sid="cyp2d6-activity-score",
        name="cyp2d6 activity score",
        label="CYP2D6 activity score",
        description="CYP2D6 activity score. Calculated based on the allele combination "
        "and allele scores. Values are in the range [0-3].",
        parents=["gene-phenotype"],
        dtype=DType.NUMERIC,
        units=[DIMENSIONLESS],
    ),
    # FIXME: create measurement type for phenotypes estimated from genetic variants.
    MeasurementType(
        sid="cyp2d6-phenotype",
        name="cyp2d6 phenotype",
        label="CYP2D6 phenotype",
        description="CYP2D6 metabolic phenotype. Commonly measurement either by cumulative metabolic ratios in urine "
        "or by metabolic ratios in plasma and serum.",
        parents=["gene-phenotype"],
        dtype=DType.CATEGORICAL,
    ),
    Choice(
        sid="poor-metabolizer",
        name="pm",
        label="poor metabolizer (PM)",
        description="Poor metabolizer (PM).",
        parents=[
            "cyp2d6-phenotype",
            "nat2-phenotype",
            "cyp1a2-phenotype",
            "cyp2c19-phenotype",
        ],
        synonyms=["slow metabolizer", "PM", "PM/PM"],
    ),
    Choice(
        sid="intermediate-poor-metabolizer",
        name="im/pm",
        label="intermediate/poor metabolizer (IM/PM)",
        description="intermediate/poor metabolizer (IM/PM)",
        parents=[
            "cyp2d6-phenotype",
            "nat2-phenotype",
            "cyp1a2-phenotype",
            "cyp2c19-phenotype",
        ],
        synonyms=["IM/PM"],
    ),
    Choice(
        sid="intermediate-metabolizer",
        name="im",
        label="intermediate metabolizer (IM)",
        description="Intermediate metabolizer (IM)",
        parents=[
            "cyp2d6-phenotype",
            "nat2-phenotype",
            "cyp1a2-phenotype",
            "cyp2c19-phenotype",
        ],
        synonyms=["IM", "IM/IM"],
    ),
    Choice(
        sid="extensive-poor-metabolizer",
        name="em/pm",
        label="extensive/poor metabolizer (EM/PM)",
        description="extensive/poor metabolizer (EM/PM)",
        parents=[
            "cyp2d6-phenotype",
            "nat2-phenotype",
            "cyp1a2-phenotype",
            "cyp2c19-phenotype",
        ],
        synonyms=["EM/PM"],
    ),
    Choice(
        sid="extensive-intermediate-metabolizer",
        name="em/im",
        label="extensive/intermediate metabolizer (EM/IM)",
        description="extensive/intermediate metabolizer (EM/IM)",
        parents=[
            "cyp2d6-phenotype",
            "nat2-phenotype",
            "cyp1a2-phenotype",
            "cyp2c19-phenotype",
        ],
        synonyms=["EM/IM"],
    ),
    Choice(
        sid="extensive-metabolizer",
        name="em",
        label="extensive metabolizer (EM)",
        description="extensive metabolizer (EM)",
        parents=[
            "cyp2d6-phenotype",
            "nat2-phenotype",
            "cyp1a2-phenotype",
            "cyp2c19-phenotype",
        ],
        synonyms=["fast metabolizer", "rapid metabolizer", "EM", "EM/EM"],
    ),
    Choice(
        sid="ultra-rapid-metabolizer",
        name="um",
        label="ultra rapid metabolizer (UM)",
        description="ultra rapid metabolizer",
        parents=[
            "cyp2d6-phenotype",
            "nat2-phenotype",
            "cyp1a2-phenotype",
            "cyp2c19-phenotype",
        ],
        synonyms=["very fast metabolizer", "UM", "UM/UM"],
    ),
    MeasurementType(
        sid="cyp2d6-variant",
        name="cyp2d6 variant",
        label="gene variant",
        description="CYP2D6 gene variants. Gene variants are larger variants such as "
        "wildtype gene or gene duplications. For genotypes see the "
        "respective genotype information.",
        parents=["gene-variant"],
        dtype=DType.CATEGORICAL,
    ),
    Choice(
        sid="wildtype-gene",
        name="wildtype gene",
        description="Wildtype gene variant.",
        parents=["cyp2d6-variant"],
    ),
    Choice(
        sid="gene-duplication",
        name="gene duplication",
        description="Gene duplication.",
        parents=["cyp2d6-variant"],
    ),
    # ABC
    MeasurementType(
        sid="abcc2-genotype",
        name="ABCC2 genotype",
        label="ABCC2 genotype",
        description="ABCC2 genotype.",
        synonyms=[
            "CMOAT",
            "DJS",
            "MRP2",
            "cMRP",
        ],
        parents=["genotype"],
        dtype=DType.CATEGORICAL,
    ),
    MeasurementType(
        sid="abcc9-genotype",
        name="ABCC9 genotype",
        label="ABCC9 genotype",
        description="ABCC9 genotype.",
        synonyms=[],
        parents=["genotype"],
        dtype=DType.CATEGORICAL,
    ),
    MeasurementType(
        sid="abcb1-genotype",
        name="ABCB1 genotype",
        label="ABCB1 genotype",
        description="ABCB1 genotype.",
        synonyms=[
            "ABC20",
            "CD243",
            "CLCS",
            "GP170",
            "MDR1",
            "P-gp",
            "PGY1",
        ],
        parents=["genotype"],
        dtype=DType.CATEGORICAL,
    ),
    MeasurementType(
        sid="abcb11-genotype",
        name="ABCB11 genotype",
        label="ABCB11 genotype",
        description="ABCB11 genotype.",
        synonyms=[
            "ABC16",
            "BSEP",
            "PFIC-2",
            "PFIC2",
            "PGY4",
            "SPGP",
        ],
        parents=["genotype"],
        dtype=DType.CATEGORICAL,
    ),
    MeasurementType(
        sid="abcg2-genotype",
        name="ABCG2 genotype",
        label="ABCG2 genotype",
        description="ABCG2 genotype.",
        synonyms=[
            "ABCP",
            "BCRP",
            "CD338",
            "EST157481",
            "MXR",
        ],
        parents=["genotype"],
        dtype=DType.CATEGORICAL,
    ),
    # Cytochrome P450
    MeasurementType(
        sid="cyp1a2-genotype",
        name="cyp1a2 genotype",
        label="CYP1A2 genotype",
        description="CYP1A2 genotype.",
        parents=["genotype"],
        dtype=DType.CATEGORICAL,
    ),
    MeasurementType(
        sid="cyp2b6-genotype",
        name="cyp2b6 genotype",
        label="CYP2B6 genotype",
        description="CYP2B6 genotype.",
        parents=["genotype"],
        dtype=DType.CATEGORICAL,
    ),
    MeasurementType(
        sid="cyp2c8-genotype",
        name="cyp2c8 genotype",
        label="CYP2C8 genotype",
        description="CYP2C8 genotype.",
        parents=["genotype"],
        dtype=DType.CATEGORICAL,
    ),
    MeasurementType(
        sid="cyp2c9-genotype",
        name="cyp2c9 genotype",
        label="CYP2C9 genotype",
        description="CYP2C9 genotype.",
        parents=["genotype"],
        dtype=DType.CATEGORICAL,
    ),
    MeasurementType(
        sid="cyp2c19-genotype",
        name="cyp2c19 genotype",
        label="CYP2C19 genotype",
        description="CYP2C19 genotype.",
        parents=["genotype"],
        dtype=DType.CATEGORICAL,
    ),
    MeasurementType(
        sid="cyp2d6 genotype",
        label="CYP2D6 genotype",
        description="CYP2D6 genotype.",
        parents=["genotype"],
        dtype=DType.CATEGORICAL,
    ),
    MeasurementType(
        sid="cyp3a4-genotype",
        name="cyp3a4 genotype",
        label="CYP3A4 genotype",
        description="CYP3A4 genotype",
        parents=["genotype"],
        dtype=DType.CATEGORICAL,
    ),
    MeasurementType(
        sid="cyp3a5-genotype",
        name="cyp3a5 genotype",
        label="CYP3A5 genotype",
        description="CYP3A5 genotype.",
        parents=["genotype"],
        dtype=DType.CATEGORICAL,
    ),
    MeasurementType(
        sid="cyp2e1-genotype",
        name="cyp2e1 genotype",
        label="CYP2E1 genotype",
        description="CYP2E1 genotype.",
        parents=["genotype"],
        dtype=DType.CATEGORICAL,
    ),
    # SLCO
    MeasurementType(
        sid="slco1a2-genotype",
        name="SLCO1A2 genotype",
        label="SLCO1A2 genotype",
        description="SLCO1A2 genotype",
        synonyms=[
            "OATP1A2 genotype",
            "OATP-1 genotype",
            "OATP1 genotype",
            "SLC21A3 genotype",
            "OATP genotype",
            "OATP-A genotype",
        ],
        parents=["genotype"],
        dtype=DType.CATEGORICAL,
    ),
    MeasurementType(
        sid="slco1b1-genotype",
        name="SLCO1B1 genotype",
        label="SLCO1B1 genotype",
        description="SLCO1B1 genotype",
        synonyms=[
            "LST1 genotype",
            "OATP1B1 genotype",
            "OATP2 genotype",
            "OATPC genotype",
            "SLC21A6 genotype",
            "LST-1 genotype",
            "OATP-C genotype",
        ],
        parents=["genotype"],
        dtype=DType.CATEGORICAL,
    ),
    MeasurementType(
        sid="slco2b1-genotype",
        name="SLCO2B1 genotype",
        label="SLCO2B1 genotype",
        description="SLCO2B1 genotype",
        synonyms=[
            "OATP2B1 genotype",
            "OATP-B genotype",
            "OATPB genotype",
            "OATP-RP2 genotype",
            "OATPRP2 genotype",
            "KIAA0880 genotype",
            "SLC21A9 genotype",
        ],
        parents=["genotype"],
        dtype=DType.CATEGORICAL,
    ),
    # UGT
    MeasurementType(
        sid="ugt1a3-genotype",
        name="ugt1a3 genotype",
        label="UGT1A3 genotype",
        description="UGT1A3 genotype.",
        parents=["genotype"],
        dtype=DType.CATEGORICAL,
    ),
]


ABCB1_GENOTYPES = [
    # exon 12
    "C1236T C/C",  # rs1128503, C1236T C/C (wildtype)
    "C1236T C/T",  # rs1128503, C1236T T/C
    "C1236T T/T",  # rs1128503, C1236T T/T
    "C1236T C/T + T/T",
    "C1236T C/C + C/T",
    # exon 21
    "G2677T/A G/G",  # rs2032582, G2677T/A G/G (wildtype)
    "G2677T/A G/A",  # rs2032582, G2677T/A G/A
    "G2677T/A G/T",  # rs2032582, G2677T/A G/T
    "G2677T/A T/T",  # rs2032582, G2677T/A T/T
    "G2677T/A A/A",  # rs2032582, G2677T/A A/A
    "G2677T/A T/A",  # rs2032582, G2677T/A A/T
    "G2677T/A G/A + G/T",
    "G2677T/A A/T + G/T",
    "G2677T/A A/T + G/A",
    # exon 26
    "C3435T C/C",  # rs1045642, C3435T C/C (wildtype)
    "C3435T C/T",  # rs1045642, C3435T C/T
    "C3435T T/T",  # rs1045642, C3435T T/T
    "C3435T C/T + T/T",
    "C3435T C/C + C/T",
    # Keskitalo2008 and Zhou2013 (complex AND combinations of the variants above,
    # no simple way to encode these for now.
    "TTT",  # C3435T T/? & G2677T/A T/? & T1236C T/?   # e.g., C3435T T/C & G2677T/A G/T & T1236C T/T => 2 * 3 * 2 = 12 combinations
    "CGC",  # 2 * 3 * 2 = 12 combinations
    "Non-TTT",  # 1 * 3 * 1 = 3 combinations
]
for key in ABCB1_GENOTYPES:
    GENETICS_NODES.append(
        Choice(
            sid=f"ABCB1{key}",
            name=key,
            label=f"ABCB1 {key}",
            description=f"ABCB1 {key} genotype.",
            parents=["abcb1-genotype"],
            synonyms=[
                f"ABC20 {key} genotype",
                f"CD243 {key} genotype",
                f"CLCS {key} genotype",
                f"GP170 {key} genotype",
                f"MDR1 {key} genotype",
                f"P-gp {key} genotype",
                f"PGY1 {key} genotype",
            ],
        )
    )


ABCC2_GENOTYPES = [
    "CC/GA",
    "CC/GG",
    "CC/AA",
    "CT/GG",
    "CT/GA",
    "TT/GG",
    "G1249A G/G",
    "G1249A G/A",
    "G1249A A/A",
    "C1446G C/C",
    "C1446G C/G",
    "C1446G G/G",
    "T3563A T/T",
    "T3563A T/A",
    "T3563A A/A",
    "G4544A G/G",
    "G4544A G/A",
    "G4544A A/A",
    "rs717620 C/C",  # C-24T polymorphism
    "rs717620 C/T",  # C-24T polymorphism
    "rs717620 T/T",  # C-24T polymorphism
    "-24 C/C",
    "-24 C/T",
    "-24 T/T",
]
for key in ABCC2_GENOTYPES:
    GENETICS_NODES.append(
        Choice(
            sid=f"abcc2-{key}",
            name=key,
            label=f"ABCC2 {key}",
            description=f"ABCC2 {key} genotype.",
            parents=["abcc2-genotype"],
            synonyms=[
                f"CMOAT {key} genotype",
                f"DJS {key} genotype",
                f"MRP2 {key} genotype",
                f"cMRP {key} genotype",
            ],
        )
    )

ABCC9_GENOTYPES = [
    "rs704212 G/G",  # rs704212 (c.1802+2622G>A)
    "rs704212 G/A",  # rs704212 (c.1802+2622G>A)
    "rs704212 A/A",  # rs704212 (c.1802+2622G>A)
]
for key in ABCC9_GENOTYPES:
    GENETICS_NODES.append(
        Choice(
            sid=f"abcc9-{key}",
            name=key,
            label=f"ABCC9 {key}",
            description=f"ABCC9 {key} genotype.",
            parents=["abcc9-genotype"],
            synonyms=[],
        )
    )


ABCG2_GENOTYPES = [
    "c.34 A/A",
    "c.34 A/G",
    "c.34 G/G",
    "c.421 C/C",
    "c.421 C/A",
    "c.421 A/A",
]
for key in ABCG2_GENOTYPES:
    GENETICS_NODES.append(
        Choice(
            sid=f"abcg2-{key}",
            name=key,
            label=f"ABCG2 {key}",
            description=f"ABCG2 {key} genotype.",
            parents=["abcg2-genotype"],
            synonyms=[
                f"ABCP {key} genotype",
                f"BCRP {key} genotype",
                f"CD338 {key} genotype",
                f"EST157481 {key} genotype",
                f"MXR {key} genotype",
            ],
        )
    )


# Pharmvar information

# (1) legacy information
# https://www.pharmvar.org/gene/CYP1A2
# sid=CYP1A2*1A
# description= rest of information + special pharmvar fields ?
# annotations = [ (BQB.IS, pubmed/Ikeya et al, 1989), Quattrochi and Tukey, 1989]
# add link to https://www.pharmvar.org/gene/CYP1A2

# (2) REST information


CYP1A2_ALLELES: list[str] = []  # see https://www.pharmvar.org/gene/CYP1A2

CYP1A2_GENOTYPES = [
    "*1/*1",
    "*1/*1f",
    "*1a/*1a",
    "*1a/*1f",
    "*1c/*1f",
    "*1f/*1f",
    "*1c*1f/*1c*1f",
    "-163C>A c/c",
    "-163C>A c/a",
    "-163C>A a/a",
    "rs2470893 G>A (zero A allele)",  # genetic variant of rs2470893 (promoter localized in the intergenic region between CYP1A1 and CYP1A2)
    "rs2470893 (one A allele)",  # genetic variant of rs2470893 (promoter localized in the intergenic region between CYP1A1 and CYP1A2)
    "rs2470893 (two A allele)",  # genetic variant of rs2470893 (promoter localized in the intergenic region between CYP1A1 and CYP1A2)
    "*1F,*1F",
    "*1B,*1F and *6",
    "*1B,*1F and *1F",
    "*1B,*1F and *1B",
    "*1B,*1F",
    "*1B,*1D,*1E,*1F and *1K",
    "*1B,*1D,*1F and *1F, C(-730)T",
    "*1B,*1D,*1F and *1F",
    "*1B,*1D,*1F and *1B,*1D,*1F",
    "*1B,*1D,*1F and *1B,*1D,*1E, *1F",
    "*1B,*1D,*1F and *1B,*1C,*1D, *1F",
    "*1B,*1D,*1F and *1B",
    "*1B,*1D,*1E,*1F and *1F",
    "*1B,*1D,*1E,*1F and *1B,*1D,*1E,*1F",
    "*1B,*1D,*1E,*1F and *1B",
    "*1B,*1C,*1D,*1F and *1B",
    "*1B,*1C,*1D,*1F and *1F",
    "*1B,*1C,*1D,*1F and *1B,*1D,*1E,*1F",
    "*1B,*1C,*1D,*1F and *1B,*1C,*1D,*1F",
    "*1B,*1B",
]
for key in CYP1A2_GENOTYPES:
    GENETICS_NODES.append(
        Choice(
            sid=f"cyp1a2-{key}",
            name=key,
            label=f"CYP1A2 {key}",
            description=f"CYP1A2 {key} genotype.",
            parents=["cyp1a2-genotype"],
        )
    )

CYP2B6_GENOTYPES = [
    "*1/*1",
    "*1/*6",
]
for key in CYP2B6_GENOTYPES:
    GENETICS_NODES.append(
        Choice(
            sid=f"cyp2b6-{key}",
            name=key,
            label=f"CYP2C6 {key}",
            description=f"CYP2C6 {key} genotype.",
            parents=["cyp2b6-genotype"],
        )
    )

CYP2C8_GENOTYPES = [
    "*1/*1",
    "*1/*2",
    "*1/*3",
    "*1/*4",
]
for key in CYP2C8_GENOTYPES:
    GENETICS_NODES.append(
        Choice(
            sid=f"cyp2c8-{key}",
            name=key,
            label=f"CYP2C8 {key}",
            description=f"CYP2C8 {key} genotype.",
            parents=["cyp2c8-genotype"],
        )
    )

# todo: add as synonyms
# https://www.pharmvar.org/gene/CYP2D6
CYP2D6_GENOTYPES = [
    "*1/*1",  # C/C_188 # em
    "*1/*1x2",
    "*1/*2",  # em
    "*1/*2x2",
    "*1/*3",
    "*1/*4",
    "*1/*4x2",
    "*1/*5",  # em
    "*1/*6",
    "*1/*7",
    "*1/*9",
    "*1/*10",  # C/T_188 # em
    "*1/*10x2",
    "*1/*17",
    "*1/*21",
    "*1/*29",
    "*1/*36",
    "*1/*41",
    "*1/*42",
    "*1/*45 or 46",  # todo: how to encode this
    "*1x2/*1",
    "*1x2/*2",
    "*1x2/*4",
    "*1x2/*5",
    "*1x2/*10",
    "*1x2/*17",
    "*1/*35",
    "*1x2/*41",
    "*1/*1xN",  # collection of subjects with N > 1
    "*1xN/*17",  # collection of subjects with N > 1
    "*1xN/*35",  # collection of subjects with N > 1
    "*1/*2xN",  # collection of subjects with N > 1
    "*2/*1x2",
    "*2/*2",
    "*2/*2x2",
    "*2/*3",
    "*2/*4",
    "*2/*4x2",
    "*2/*5",
    "*2/*6",
    "*2/*9",
    "*2/*10",
    "*2/*14",
    "*2/*17",
    "*2/*21",
    "*2/*29",
    "*2/*36+*10x2",  # todo: Janek: Better understand what this is and if to keep it.
    "*2/*41",
    "*2x2/*1",
    "*2x2/*3",
    "*2x2/*4",
    "*2x2/*5",
    "*2x2/*17",
    "*3/*2",  # em
    "*3/*2x2",
    "*3/*3",
    "*3/*4",
    "*3/*5",  # pm
    "*4/*4",  # pm
    "*4/*5",  # pm
    "*4/*6",
    "*4/*9",
    "*4/*10",
    "*4/*17",
    "*4x2/*17",
    "*4/*36",
    "*4/*41",
    "*5/*5",
    "*5/*10",
    "*5/*14",
    "*5/*16",
    "*5/*17",
    "*5/*29",
    "*6/*6",
    "*6/*35",
    "*6/*41",
    "*7/*41",
    "*10/*10",  # T/T_188
    "*10/*10x2",
    "*10/*14",
    "*10/*17",
    "*10/*36",
    "*10/*41",
    "*10/*41x2",
    "*13+*1/*4",  # todo: Janek: Better understand what this is and if to keep it.
    "*17/*35",
    "*17/*17",
    "*17/*29",
    "*17/*41",
    "*17/*42",
    "*29/*29",
    "*29/*41",
    "*29/*45 or 46",  # todo: Janek: Better understand what this is and if to keep it.
    "*35/*35",
    "*41/*41",
    "*41/null",
    "*x/*4",
    "*other/*other",  # todo: other probably the same as x -> rename
    "*other/*17",  # todo: other probably the same as x -> rename
    "*other/*29",  # todo: other probably the same as x -> rename
    "*other/*41",  # todo: other probably the same as x -> renames
]

for key in CYP2D6_GENOTYPES:
    GENETICS_NODES.append(
        Choice(
            sid=f"cyp2d6-{key}",
            name=key,
            label=f"CYP2D6 {key}",
            description=f"CYP2D6 {key} genotype.",
            parents=["cyp2d6-genotype"],
        )
    )

CYP2C9_GENOTYPES = [
    "C/A",
    "A/A",
    "*1/*1",
    "*1/*2",
    "*1/*3",
    "*1/*12",
    "*1/*13",
    "*2/*2",
    "*2/*3",
    "*3/*3",
]
for key in CYP2C9_GENOTYPES:
    GENETICS_NODES.append(
        Choice(
            sid=f"cyp2c9-{key}",
            name=key,
            label=f"CYP2C9 {key}",
            description=f"CYP2C9 {key} genotype.",
            parents=["cyp2c9-genotype"],
        )
    )

CYP2C19_GENOTYPES = [
    "*1/*1",
    "*1/*2",
    "*1/*2A",
    "*1/*2B",
    "*1/*3",
    "*1/*17",
    "*2/*2",
    "*2/*3",
    "*2/*17",
    "*3/*3",
    "*3/*17",
    "*17/*17",
    "*17",
]
for key in CYP2C19_GENOTYPES:
    GENETICS_NODES.append(
        Choice(
            sid=f"cyp2c19-{key}",
            name=key,
            label=f"CYP2C19 {key}",
            description=f"CYP2C19 {key} genotype.",
            parents=["cyp2c19-genotype"],
        )
    )

CYP3A4_GENOTYPES = [
    "wildtype/wildtype",
    "other/*1B",
    "*1/*1",
    "*1/*1b",
    "*1/*2",
    "*1/*22",
    "*1/*1G",  # rs2242480, 20230 C>T
    "*1G/*1G",  # rs2242480, 20230 C>T
]
for key in CYP3A4_GENOTYPES:
    GENETICS_NODES.append(
        Choice(
            sid=f"cyp3a4-{key}",
            name=key,
            label=f"CYP3A4 {key}",
            description=f"CYP3A4 {key} genotype.",
            parents=["cyp3a4-genotype"],
        )
    )

CYP3A5_GENOTYPES = [
    "*1/*1",
    "*1/*3",
    "*3/*3",
    "*3/*1",
    "other/*1C",
    "other/*3",
    "G/G",
    "A/G",
    "A/A",
]
for key in CYP3A5_GENOTYPES:
    GENETICS_NODES.append(
        Choice(
            sid=f"cyp3a5-{key}",
            name=key,
            label=f"CYP3A5 {key}",
            description=f"CYP3A5 {key} genotype.",
            parents=["cyp3a5-genotype"],
        )
    )

# see https://www.pharmvar.org/gene/CYP2E1
# Unfortunately two different nomenclature systems were developed for the CYP2E1
# alleles simultaneously. The authors of both nomenclature systems have agreed in
# July 2000 that the nomenclature system given in this homepage should be the
# recommended one, see Ingelman-Sundberg et al. 2001.
CYP2E1_GENOTYPES = [
    "*1A/*1A",
    "*1A/*5",
    "*5/*5",
]
for key in CYP2E1_GENOTYPES:
    GENETICS_NODES.append(
        Choice(
            sid=f"cyp2e1-{key}",
            name=key,
            label=f"CYP2E1 {key}",
            description=f"CYP2E1 {key} genotype.",
            parents=["cyp2e1-genotype"],
        )
    )

NAT2_GENOTYPES = [
    "*4/*4",
    "*4/*5",
    "*4/*6",
    "*4/*5A",
    "*5/*6",
    "*5/*5",
    "*6/*6",
]
for key in NAT2_GENOTYPES:
    GENETICS_NODES.append(
        Choice(
            sid=f"nat-{key}",
            name=key,
            label=f"NAT2 {key}",
            description=f"NAT2 {key} genotype.",
            parents=["nat2-genotype"],
        )
    )

# OATP1A2
SLCO1A2_GENOTYPES = [
    "T38C T/T",  # c.38T>C
    "T38C T/C",  # c.38T>C
    "A516C A/A",  # c.516A>C, rs11568563, https://www.pharmgkb.org/variant/PA166154639
    "A516C A/C",  # c.516A>C, rs11568563, https://www.pharmgkb.org/variant/PA166154639
]
for key in SLCO1A2_GENOTYPES:
    GENETICS_NODES.append(
        Choice(
            sid=f"slco1a2-{key}",
            name=key,
            label=f"SLCO1A2 {key}",
            description=f"SLCO1A2 {key} genotype.",
            parents=["slco1a2-genotype"],
            synonyms=[
                f"OATP1A2 {key} genotype",
                f"OATP-1 {key} genotype",
                f"OATP1 {key} genotype",
                f"SLC21A3 {key} genotype",
                f"OATP {key} genotype",
                f"OATP-A {key} genotype",
            ],
        ),
    )

# OATP1B1 (e.g. pravastatin or simvastatin)
# rs numbers describe the SNP (single nucleotide polymorphisms)
# TODO: map on rs annotation; see https://www.ncbi.nlm.nih.gov/snp/?term=SLCO1B1%5BGene%20Name%5D
SLCO1B1_GENOTYPES = [
    # FIXME: https://www.ncbi.nlm.nih.gov/snp/
    # star syntax: *1a: c.521 T, c.388 A, c.571 T, c.597 C
    "*1/*1",
    "*1/*16",
    "*1b/*16",
    "*1a/*1a",
    "*1a/*1b",
    "*1b/*1b",
    "*1a/*5",
    "*1a/*15",
    "*1b/*15",
    "*1b/*5",
    "*15/*15",
    "*5/*15",
    "no *15b",  # non-carriers of *15B: (c.388A/c388A) & (c.521T/c521T)
    "no *17",  # non-carriers of *17: (c.388A/c388A) & (c.521T/c521T) & (g.11187G/g.11187G)
    "*x/*15b",  # heterozygous carriers of *15B (c.388A/c388A>G) & (c.521T/c521T>C)
    "*x/*17",  # heterozygous carriers of *17 (c.388A/c388A>G) & (c.521T/c521T>C) & (g.11187G/g.11187G>A)
    # T521C (rs4149056)
    "c.521 T/T",  # (1*/1*), c.521T/c.521T synonym 521TT genotype
    "c.521 T/C",  # (1*/rs4149056) 521 T>C, rs4149056 (haplotypes with variant alleles: *5, *15, *17, *40, *46, *47)
    "c.521 C/C",  # (rs4149056/rs4149056); c.521T>C/c.521T>C
    # A388G (rs2306283)
    "c.388 A/A",
    "c.388 A/G",
    "c.388 G/G",
    # c.571T>C
    "c.571 T/T",
    "c.571 C/T",
    "c.571 C/C",
    # c.597C>T
    "c.597 C/C",
    "c.597 C/T",
    "c.597 T/T",
    # g.11187G>A, -11187G>A
    "g.11187 G/G",
    "g.11187 A/G",
    "g.11187 G/A",
    "AG/TC",
    "c.1457CC",
    "c.1457CT",
    "c.1457TT",
    "c.935GG",
    "c.935GA",
    "c.935AA",
    "c.601GG",
    "c.601GA",
    "c.601AA",
    "g.-282GG",
    "g.-282GA",
    "g.-282AA",
]
for key in SLCO1B1_GENOTYPES:
    GENETICS_NODES.append(
        Choice(
            sid=f"slco1b1-{key}",
            name=key,
            label=f"SLCO1B1 {key}",
            description=f"SLCO1B1 {key} genotype.",
            parents=["slco1b1-genotype"],
            synonyms=[
                f"LST1 {key} genotype",
                f"OATP1B1 {key} genotype",
                f"OATP2 {key} genotype",
                f"OATPC {key} genotype",
                f"SLC21A6 {key} genotype",
                f"LST-1 {key} genotype",
                f"OATP-C {key} genotype",
            ],
        ),
    )

# OATP2B1 (e.g. pravastatin or simvastatin)
SLCO2B1_GENOTYPES = [
    "G935A G/G",  # c.935G>A
    "G935A G/A",  # c.935G>A
    "C1457T C/C",  # c.1457C>T
    "C1457T T/T",  # c.1457C>T
]
for key in SLCO2B1_GENOTYPES:
    GENETICS_NODES.append(
        Choice(
            sid=f"slco2b1-{key}",
            name=key,
            label=f"SLCO2B1 {key}",
            description=f"SLCO2B1 {key} genotype.",
            parents=["slco2b1-genotype"],
            synonyms=[
                f"OATP2B1 {key} genotype",
                f"OATP-B {key} genotype",
                f"OATPB {key} genotype",
                f"OATP-RP2 {key} genotype",
                f"OATPRP2 {key} genotype",
                f"KIAA0880 {key} genotype",
                f"SLC21A9 {key} genotype",
            ],
        ),
    )

UGT1A3_GENOTYPES = ["*2 carrier", "*2 non-carrier", "*2 heterozygote", "*2/*2"]
for key in UGT1A3_GENOTYPES:
    GENETICS_NODES.append(
        Choice(
            sid=f"ugt1a3-{key}",
            name=key,
            label=f"UGT1A3 {key}",
            description=f"UGT1A3 {key} genotype.",
            parents=["ugt1a3-genotype"],
        )
    )
