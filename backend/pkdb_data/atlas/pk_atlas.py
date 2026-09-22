"""Pharmacokinetics nodes for ATLAS."""

from pymetadata.core.miriam import BQB

from pkdb_data.atlas.units_atlas import (
    AUC_DIV_UNITS,
    AUC_UNITS,
    CLEARANCE_UNITS,
    CONCENTRATION_UNITS,
    FLOW_UNITS,
    RATE_UNITS,
    RATIO_UNITS,
    SURFACE_UNITS,
    TIME_UNITS,
    V_UNITS,
)
from pkdb_data.info_nodes.node import (
    DType,
    InfoNode,
    MeasurementType,
)

# TODO annotations
# TODO reference values?
# TODO labels
# TODO names?
# TODO synonyms

# SET OF PARAMETERS CAN BE CHANGED

PK_ATLAS_NODES: list[InfoNode] = [
    # pharmacokinetic measurement
    MeasurementType(
        sid="ic50",
        description="The concentration of the inhibitory molecule that results "
        "in a 50% or greater reduction in infectivity, biological or biochemical function. ",
        synonyms=[
            "Fifty percent inhibitory concentration",
            "IC50",
            "50% Inhibitory Concentration",
        ],
        units=CONCENTRATION_UNITS,
        dtype=DType.NUMERIC,
        annotations=[
            (BQB.IS_VERSION_OF, "ncit/C191279"),
        ],
        parents=["pharmacokinetic-measurement"],
    ),
    MeasurementType(
        sid="ec50",
        description="A measure of the potency of a compound, expressed as the concentration of the "
        "compound that induces a response halfway between the baseline and maximum. ",
        synonyms=[
            "Half maximal effective agent concentration",
            "EC50",
            "50% Effective Concentration",
        ],
        units=CONCENTRATION_UNITS,
        dtype=DType.NUMERIC,
        annotations=[
            (BQB.IS_VERSION_OF, "ncit/C199690"),
        ],
        parents=["pharmacokinetic-measurement"],
    ),
    MeasurementType(
        "auc-measurement",
        description="Area under the curve (AUC), all pharmacokinetics parameters "
        "which are an area under the curve. ",
        synonyms=["AUC", "Area Under Curve"],
        dtype=DType.ABSTRACT,
        annotations=[
            (BQB.IS_VERSION_OF, "ncit/C64774"),
        ],
        parents=["pharmacokinetic-measurement"],
    ),
    MeasurementType(
        "auc-inf",
        description="Area under the curve (AUC), extrapolated until infinity. ",
        synonyms=["Area Under the Curve Infinity"],
        dtype=DType.ABSTRACT,
        parents=["auc-measurement"],
    ),
    MeasurementType(
        "observed-auc-inf",
        description="The area under the curve (AUC) extrapolated to infinity "
        "from dosing time, based on the last observed concentration. ",
        synonyms=["Observed Area Under the Curve Infinity"],
        dtype=DType.NUMERIC,
        units=AUC_UNITS,
        annotations=[
            (BQB.IS_VERSION_OF, "ncit/C85761"),
        ],
        parents=["auc-inf"],
    ),
    MeasurementType(
        "predicted-auc-inf",
        description="The area under the curve (AUC) extrapolated to infinity from dosing time, "
        "based on the predicted last concentration. ",
        synonyms=["Predicted Area Under the Curve Infinity"],
        dtype=DType.NUMERIC,
        units=AUC_UNITS,
        annotations=[
            (BQB.IS_VERSION_OF, "ncit/C85785"),
        ],
        parents=["auc-inf"],
    ),
    MeasurementType(
        "auc-end",
        description="Area under the curve (AUC) until last time point. "
        "Area Under the Curve From Dosing to Last Concentration. "
        "Time period is required for calculation. ",
        dtype=DType.ABSTRACT,
        annotations=[
            (BQB.IS_VERSION_OF, "ncit/C85565"),
        ],
        parents=["auc-measurement"],
    ),
    MeasurementType(
        "observed-auc-end",
        description="The area under the curve (AUC) until last time point "
        "from dosing time, based on the last observed concentration. "
        "Time period is required for calculation. ",
        synonyms=["Observed Area Under the Curve Infinity"],
        dtype=DType.NUMERIC,
        units=AUC_UNITS,
        annotations=[
            (BQB.IS_VERSION_OF, "ncit/C85761"),
        ],
        parents=["auc-end"],
    ),
    MeasurementType(
        "predicted-auc-end",
        description="The area under the curve (AUC) until last time point from dosing time, "
        "based on the last predicted last concentration. "
        "Time period is required for calculation. ",
        synonyms=["Predicted Area Under the Curve Infinity"],
        dtype=DType.NUMERIC,
        units=AUC_UNITS,
        annotations=[
            (BQB.IS_VERSION_OF, "ncit/C85785"),
        ],
        parents=["auc-end"],
    ),
    MeasurementType(
        "auc-relative",
        description="Relative area under the curve (AUC), AUC of a substance relative "
        "to other measured metabolites",
        dtype=DType.ABSTRACT,
        parents=["auc-measurement"],
    ),
    MeasurementType(
        "auc-per-dose",
        description="Area under the curve divided by dose (1/clearance). "
        "Dose-normalized area under the curve.",
        dtype=DType.ABSTRACT,
        parents=["auc-relative"],
    ),
    MeasurementType(
        "observed-auc-per-dose",
        description="The area under the curve (AUC) extrapolated to infinity, "
        "calculated using the observed value of the last non-zero "
        "concentration, divided by the dose.",
        synonyms=["AUC Infinity Observed Normalized by Dose"],
        dtype=DType.NUMERIC,
        units=AUC_DIV_UNITS,
        annotations=[
            (BQB.IS_VERSION_OF, "ncit/C96695"),
        ],
        parents=["auc-per-dose", "auc-inf"],
    ),
    MeasurementType(
        "predicted-auc-per-dose",
        description="The area under the curve (AUC) extrapolated to infinity, "
        "calculated using the predicted value of the last non-zero "
        "concentration, divided by the dose.",
        synonyms=["AUC Infinity Predicted Normalized by Dose"],
        dtype=DType.NUMERIC,
        units=AUC_DIV_UNITS,
        parents=["auc-per-dose", "auc-inf"],
    ),
    MeasurementType(
        sid="clearance-measurement",
        description="The rate at which a drug or endogenous substance is removed or cleared from the whole or part of the body. ",
        dtype=DType.ABSTRACT,
        annotations=[
            (BQB.IS_VERSION_OF, "ncit/C199688"),
            (BQB.IS_VERSION_OF, "ncit/C70914"),
        ],
        parents=["pharmacokinetic-measurement"],
    ),
    MeasurementType(
        sid="total-clearance",
        description="Total body clearance. Calculated as sum of renal, hepatic and other clearances. ",
        dtype=DType.NUMERIC,
        units=CLEARANCE_UNITS,
        parents=["clearance-measurement"],
    ),
    MeasurementType(
        sid="observed-total-clearance",
        description="The observed total body clearance. ",
        dtype=DType.NUMERIC,
        units=CLEARANCE_UNITS,
        annotations=[
            (BQB.IS_VERSION_OF, "ncit/C85773"),
            (BQB.IS_VERSION_OF, "ncit/C85772"),
        ],
        parents=["total-clearance"],
    ),
    MeasurementType(
        sid="predicted-total-clearance",
        description="The predicted total body clearance. ",
        dtype=DType.NUMERIC,
        units=CLEARANCE_UNITS,
        annotations=[
            (BQB.IS_VERSION_OF, "ncit/C85796"),
            (BQB.IS_VERSION_OF, "ncit/C85797"),
        ],
        parents=["total-clearance"],
    ),
    MeasurementType(
        sid="total-clearance-unbound",
        description="Total body clearance for unbound substance. ",
        dtype=DType.NUMERIC,
        units=CLEARANCE_UNITS,
        parents=["total-clearance"],
    ),
    MeasurementType(
        sid="observed-total-clearance-unbound",
        description="The observed total body clearance for unbound drug. ",
        dtype=DType.NUMERIC,
        units=CLEARANCE_UNITS,
        annotations=[
            (BQB.IS_VERSION_OF, "ncit/C154842"),
        ],
        parents=["total-clearance-unbound"],
    ),
    MeasurementType(
        sid="predicted-total-clearance-unbound",
        description="The predicted total body clearance for unbound drug. ",
        dtype=DType.NUMERIC,
        units=CLEARANCE_UNITS,
        annotations=[
            (BQB.IS_VERSION_OF, "ncit/C154841"),
        ],
        parents=["total-clearance-unbound"],
    ),
    MeasurementType(
        "clearance-renal",
        description="The rate at which a substance is removed from the blood via the kidneys. ",
        dtype=DType.NUMERIC,
        units=CLEARANCE_UNITS,
        annotations=[
            (BQB.IS_VERSION_OF, "ncit/C75913"),
        ],
        parents=["drug-clearance"],
    ),
    MeasurementType(
        "clearance-renal-unbound",
        description="The unbound fraction of drug within the portion of total clearance attributed to the kidneys. ",
        dtype=DType.NUMERIC,
        units=CLEARANCE_UNITS,
        annotations=[
            (BQB.IS_VERSION_OF, "ncit/C154843"),
        ],
        parents=["clearance-renal"],
    ),
    MeasurementType(
        "clearance-nonrenal",
        description="A measurement of the total clearance rate of a substance from "
        "the blood minus the renal clearance rate of that substance.",
        dtype=DType.NUMERIC,
        units=CLEARANCE_UNITS,
        annotations=[
            (BQB.IS_VERSION_OF, "ncit/C102376"),
        ],
        parents=["drug-clearance"],
    ),
    MeasurementType(
        "clearance-hepatic",
        description="Clearance of substance by the liver based on bile measurements. ",
        dtype=DType.NUMERIC,
        units=CLEARANCE_UNITS,
        parents=["clearance-nonrenal"],
    ),
    MeasurementType(
        "clearance-other",
        description="Clearance of substance not by kidneys and not by a liver. ",
        dtype=DType.NUMERIC,
        units=CLEARANCE_UNITS,
        parents=["clearance-nonrenal"],
    ),
    MeasurementType(
        sid="oral-clearance",
        description="A finding of complete oral clearance after swallowing. ",
        dtype=DType.NUMERIC,
        units=CLEARANCE_UNITS,
        synonyms=["Complete oral clearance"],
        annotations=[
            (BQB.IS, "ncit/C127209"),
        ],
        parents=["drug-clearance"],
    ),
    # MeasurementType(
    #     "clearance-intrinsic",
    #     description="Intrinsic clearance of substance. This is the total clearance minus "
    #     "the clearance by the kidneys "
    #     "(renal clearance). In most cases this is exclusively the liver if no "
    #     "other tissues are involved in the conversion/clearance.",
    #     units=CLEARANCE_UNITS,
    #     dtype=DType.NUMERIC,
    # ),
    # MeasurementType(
    #     "clearance-intrinsic-unbound",
    #     description="Intrinsic clearance of unbound substance (see also "
    #     "`fraction_unbound`).",
    #     units=CLEARANCE_UNITS,
    #     dtype=DType.NUMERIC,
    # ),
    # MeasurementType(
    #     "clearance-partial",
    #     description="Partial clearance of substance. It can occur if "
    #     "several path are present. The pathway is encoded "
    #     "by the substance",
    #     units=CLEARANCE_UNITS,
    #     dtype=DType.NUMERIC,
    # ),
    MeasurementType(
        sid="concentration-measurement",
        description="The quantity of a substance per unit volume or weight. ",
        dtype=DType.ABSTRACT,
        annotations=[
            (BQB.IS, "ncit/C70918"),
        ],
        parents=["pharmacokinetic-measurement"],
    ),
    MeasurementType(
        sid="cmax",
        description="This is a measurement that quantifies the maximum concentration of an experimental "
        "substance or drug in the plasma or a target organ after dose administration. ",
        synonyms=["Cmax", "Cpk", "peak concentration"],
        units=CONCENTRATION_UNITS,
        dtype=DType.NUMERIC,
        annotations=[
            (BQB.IS, "ncit/C70918"),
        ],
        parents=["concentration-measurement"],
    ),
    MeasurementType(
        sid="c0",
        description="The first measured concentration of a compound in a substance. ",
        synonyms=["C0", "c_0", "C_0", "Initial concentration"],
        dtype=DType.NUMERIC,
        units=CONCENTRATION_UNITS,
        annotations=[
            (BQB.IS, "ncit/C85644"),
        ],
        parents=["concentration-measurement"],
    ),
    MeasurementType(
        sid="cmin",
        description="Minimal concentration for given substance. Importantly the "
        "minimum is after the peak concentration, and refers mostly to "
        "the last measured data point. See also 'cthrough' for multiple dosing.",
        synonyms=["Cmin"],
        dtype=DType.NUMERIC,
        units=CONCENTRATION_UNITS,
        annotations=[
            (BQB.IS, "ncit/C85579"),
        ],
        parents=["concentration-measurement"],
    ),
    MeasurementType(
        sid="c-trough",
        description="Concentration at end of dosing interval. ",
        synonyms=[
            "Ctrough",
            "Trough level",
        ],
        dtype=DType.NUMERIC,
        units=CONCENTRATION_UNITS,
        annotations=[
            (BQB.IS, "ncit/C102394"),
        ],
        parents=["concentration-measurement"],
    ),
    MeasurementType(
        sid="c-average",
        description="Calculated as AUC_enc/tau with tau being interval of measurement. ",
        synonyms=["Caverage", "AUC/tau", "AUC/t"],
        dtype=DType.NUMERIC,
        units=CONCENTRATION_UNITS,
        annotations=[(BQB.IS_VERSION_OF, "ncit/C85575")],
        parents=["concentration-measurement"],
    ),
    MeasurementType(
        sid="c-ss",
        description="Concentration at steady-state. ",
        dtype=DType.NUMERIC,
        units=CONCENTRATION_UNITS,
        parents=["concentration-measurement"],
    ),
    MeasurementType(
        sid="c-extracel",
        description="Concentration of a substance in extracellular "
        "(blood + interstitium) space. ",
        synonyms=["Cexc", "cexc", "Extracellular concentration"],
        dtype=DType.NUMERIC,
        units=CONCENTRATION_UNITS,
        parents=["concentration-measurement"],
    ),
    MeasurementType(
        sid="c-cel",
        description="Concentration of a substance in cellular space. ",
        synonyms=["Ccel", "ccel", "Cellular concentration"],
        dtype=DType.NUMERIC,
        units=CONCENTRATION_UNITS,
        parents=["concentration-measurement"],
    ),
    MeasurementType(
        sid="c-in",
        description="Concentration of a substance in 'in flow to the organ'. ",
        synonyms=["Cin", "cin", "In-flow concentration"],
        dtype=DType.NUMERIC,
        units=CONCENTRATION_UNITS,
        parents=["concentration-measurement"],
    ),
    MeasurementType(
        "k",
        description="",
        synonyms=["Rate constant"],
        dtype=DType.ABSTRACT,
        annotations=[
            (BQB.IS, "ncit/C94967"),
        ],
        parents=["pharmacokinetic-measurement"],
    ),
    MeasurementType(
        "kel",
        description="Elimination rate constant for given substance. ",
        synonyms=["Elimination rate constant"],
        dtype=DType.NUMERIC,
        units=RATE_UNITS,
        parents=["k"],
    ),
    MeasurementType(
        sid="kabs",
        description="Absorption rate constant for a given substance. ",
        dtype=DType.NUMERIC,
        units=RATE_UNITS,
        parents=["k"],
    ),
    MeasurementType(
        "t",
        description="",
        dtype=DType.ABSTRACT,
        parents=["pharmacokinetic-measurement"],
    ),
    MeasurementType(
        "thalf",
        description="The time required for half of an exogenous substance be removed from either the plasma or whole or part of the body. ",
        synonyms=["Elimination half life"],
        dtype=DType.NUMERIC,
        units=TIME_UNITS,
        annotations=[
            (BQB.IS, "ncit/C70915"),
        ],
        parents=["t"],
    ),
    MeasurementType(
        "tmax",
        description="The time it takes to reach the maximum concentration (Cmax) of an exogenous compound "
        "or drug in the plasma or a tissue after a dose is administered. ",
        synonyms=["time to maximum", "Tmax", "Tpk", "time of peak concentration"],
        dtype=DType.NUMERIC,
        units=TIME_UNITS,
        annotations=[
            (BQB.IS, "ncit/C70919"),
        ],
        parents=["t"],
    ),
    # MeasurementType(
    #     sid="thalf_absorption",
    #     label="absorption half-life",
    #     description="Absorption half-life for substance.",
    #     parents=["pharmacokinetic measurement"],
    #     dtype=DType.NUMERIC,
    #     units=TIME_UNITS,
    # ),
    MeasurementType(
        sid="bioavailability",
        description="The rate and extent to which the active ingredient or active moiety is absorbed from "
        "a drug product and becomes available at the site of action. This is "
        "often < 1, because only a fraction of the substance is absorbed "
        "(see 'fraction_absorbed'), due to first pass effects. AUC(po)/AUC(iv) or Ae(po)/Ae(iv).",
        dtype=DType.NUMERIC,
        units=RATIO_UNITS,
        annotations=[
            (BQB.IS, "ncit/C70913"),
        ],
        parents=["pharmacokinetic-measurement"],
    ),
    MeasurementType(
        sid="fraction",
        description="A part, a fragment of a whole. ",
        dtype=DType.ABSTRACT,
        annotations=[
            (BQB.IS, "ncit/C25514"),
        ],
        parents=["pharmacokinetic-measurement"],
    ),
    MeasurementType(
        sid="system-availab-fraction",
        description="Extent of dose reaching circulation. ",
        dtype=DType.NUMERIC,
        units=RATIO_UNITS,
        parents=["fraction"],
    ),
    MeasurementType(
        sid="fraction-bound",
        description="The ratio of bound drug concentration to the total concentration. ",
        synonyms=["FB", "fb"],
        dtype=DType.NUMERIC,
        units=RATIO_UNITS,
        annotations=[
            (BQB.IS, "ncit/C154840"),
        ],
        parents=["fraction"],
    ),
    MeasurementType(
        sid="fraction-unbound",
        description="The ratio of free substance concentration to the total concentration. ",
        synonyms=["FU", "fu"],
        dtype=DType.ABSTRACT,
        units=RATIO_UNITS,
        annotations=[
            (BQB.IS, "ncit/C135490"),
        ],
        parents=["fraction"],
    ),
    MeasurementType(
        sid="fraction-unbound-plasma",
        description="The ratio of free substance concentration in "
        "plasma water to the total concentration in plasma. ",
        synonyms=["fuP"],
        dtype=DType.NUMERIC,
        units=RATIO_UNITS,
        annotations=[],
        parents=["fu"],
    ),
    MeasurementType(
        sid="fraction-unbound-cell",
        description="The ratio of free substance concentration in "
        "cell water to the total concentration in cells. ",
        synonyms=["fuC"],
        dtype=DType.NUMERIC,
        units=RATIO_UNITS,
        annotations=[],
        parents=["fu"],
    ),
    MeasurementType(
        sid="partition-coefficient",
        description="A constant symbolizing the ratio of a "
        "dissolved substance in a two-phase system. ",
        dtype=DType.ABSTRACT,
        annotations=[
            (BQB.IS, "ncit/C20610"),
        ],
        parents=["pharmacokinetic-measurement"],
    ),
    MeasurementType(
        sid="fraction-unbound-blood",
        description="The ratio of free substance concentration in "
        "plasma water to the total concentration in blood. ",
        synonyms=["fuB"],
        dtype=DType.NUMERIC,
        units=RATIO_UNITS,
        annotations=[],
        parents=["partition-coefficient"],
    ),
    MeasurementType(
        sid="blood-to-plasma-ratio",
        description="The ratio of concentration of a substance in plasma "
        "to concentration of this substance in blood. ",
        synonyms=["B:P"],
        dtype=DType.NUMERIC,
        units=RATIO_UNITS,
        annotations=[],
        parents=["partition-coefficient"],
    ),
    MeasurementType(
        sid="Kexc",
        description="The ratio of concentration of a substance in extracellular "
        "space to concentration of the substance in blood. ",
        synonyms=["Extracellular partition coefficient"],
        dtype=DType.NUMERIC,
        units=RATIO_UNITS,
        annotations=[],
        parents=["partition-coefficient"],
    ),
    # MeasurementType(
    #     sid="recovery",
    #     description="Fraction recovered of given substance. Use in combination "
    #                 "with the provided tissue to encode recovery for given tissue. "
    #                 "E.g. `recovery` with tissue `urine` codes for the "
    #                 "urinary recovery of given substance over the specified period "
    #                 "of time. Often stored as percent excreted. To store "
    #                 "the amount which was excreted use `cumulative amount` in "
    #                 "combination with the respective tissue.",
    #     units=[DIMENSIONLESS],
    #     dtype=DType.NUMERIC,
    #     annotations=[
    #         (BQB.IS, "ncit/C70827"),
    #     ],
    # ),
    # MeasurementType(
    #     sid="recovery-rate",
    #     description="Fraction recovered of given substance per time. Use in combination "
    #                 "with the provided tissue to encode recovery for given tissue. ",
    #     units=["percent/min"],
    #     dtype=DType.NUMERIC,
    #     annotations=[],
    # ),
    MeasurementType(
        "v",
        description="The amount of three dimensional space occupied "
        "by an object or the capacity of a space or container. ",
        dtype=DType.ABSTRACT,
        annotations=[
            (BQB.IS, "ncit/C25335"),
        ],
        parents=["pharmacokinetic-measurement"],
    ),
    MeasurementType(
        "vd",
        description="The apparent volume occupied by an exogenous compou"
        "nd after it is administered to an organism. "
        "This value assumes that the compound is uniformly distributed in the body of the organism at the "
        "concentration found in its plasma or another tissue.",
        synonyms=["Volume of disribution", "Distribution volume"],
        dtype=DType.NUMERIC,
        units=V_UNITS,
        annotations=[
            (BQB.IS, "ncit/C70917"),
        ],
        parents=["v"],
    ),
    MeasurementType(
        "observed-vd",
        description="The observed volume of distribution based on the terminal phase. ",
        dtype=DType.NUMERIC,
        units=V_UNITS,
        annotations=[
            (BQB.IS, "ncit/C85774"),
        ],
        parents=["vd"],
    ),
    MeasurementType(
        "predicted-vd",
        description="The predicted volume of distribution based on the terminal phase. ",
        dtype=DType.NUMERIC,
        units=V_UNITS,
        annotations=[
            (BQB.IS, "ncit/C85798"),
        ],
        parents=["vd"],
    ),
    MeasurementType(
        "vd-unbound",
        description="Volume of distribution for unbound substance. ",
        dtype=DType.NUMERIC,
        units=V_UNITS,
        parents=["vd"],
    ),
    MeasurementType(
        "observed-vd-unbound",
        description="The volume of distribution associated with the terminal slope "
        "following administration, calculated using the observed value "
        "of the last non-zero concentration and corrected for unbound drug. ",
        dtype=DType.NUMERIC,
        units=V_UNITS,
        annotations=[
            (BQB.IS, "ncit/C158265"),
        ],
        parents=["vd-unbound"],
    ),
    MeasurementType(
        "predicted-vd-unbound",
        description="The volume of distribution associated with the terminal slope "
        "following administration, calculated using the predicted value "
        "of the last non-zero concentration and corrected for unbound drug. ",
        dtype=DType.NUMERIC,
        units=V_UNITS,
        annotations=[
            (BQB.IS, "ncit/C158266"),
        ],
        parents=["vd-unbound"],
    ),
    MeasurementType(
        "vd-ss",
        description="The apparent volume occupied by an exogenous compound during the time point when the plasma concentration "
        "of the compound reaches steady state levels. ",
        synonyms=["Vd_ss", "Steady state volume of distribution"],
        dtype=DType.NUMERIC,
        units=V_UNITS,
        annotations=[
            (BQB.IS, "ncit/C85538"),
        ],
        parents=["v"],
    ),
    MeasurementType(
        "observed-vd-ss",
        description="An estimate of the volume of distribution at steady state, "
        "which is the mean residence time (MRT) extrapolated to infinity "
        "times steady state clearance (MRTINF*Clss), based on the last observed concentration. ",
        dtype=DType.NUMERIC,
        units=V_UNITS,
        annotations=[
            (BQB.IS, "ncit/C85770"),
        ],
        parents=["vd-ss"],
    ),
    MeasurementType(
        "predicted-vd-ss",
        description="An estimate of the volume of distribution at steady state, "
        "which is the mean residence time (MRT) extrapolated to infinity "
        "times steady state clearance (MRTINF*Clss), based on the predicted last concentration. ",
        dtype=DType.NUMERIC,
        units=V_UNITS,
        annotations=[
            (BQB.IS, "ncit/C85794"),
        ],
        parents=["vd-ss"],
    ),
    MeasurementType(
        "vd-ss-unbound",
        description="The apparent volume occupied by an exogenous unbound compound during the time point when the plasma concentration "
        "of the compound reaches steady state levels. ",
        dtype=DType.NUMERIC,
        units=V_UNITS,
        parents=["v-ss"],
    ),
    MeasurementType(
        "observed-vd-ss-unbound",
        description="The volume of distribution at steady state based on the observed CLST "
        "for a substance administered by extravascular dosing, divided by the fraction of unbound drug. ",
        dtype=DType.NUMERIC,
        units=V_UNITS,
        annotations=[
            (BQB.IS, "ncit/C156572"),
        ],
        parents=["vd-ss-unbound"],
    ),
    MeasurementType(
        "predicted-vd-ss-unbound",
        description="The volume of distribution at steady state based on the predicted CLST for "
        "a substance administered by extravascular dosing, divided by the fraction of unbound drug. ",
        dtype=DType.NUMERIC,
        units=V_UNITS,
        annotations=[
            (BQB.IS, "ncit/C156573"),
        ],
        parents=["vd-ss-unbound"],
    ),
    MeasurementType(
        "vd0",
        description="Initial volume of distribution (D/C0) calculated from dose D "
        "and initial concentration C0. ",
        dtype=DType.NUMERIC,
        units=V_UNITS,
        annotations=[
            (BQB.IS, "ncit/C102371"),
        ],
        parents=["v"],
    ),
    MeasurementType(
        "v-exc",
        description="Extracellular volume, calculated as sum of "
        "volume of blood and interstitial volume of an organ. ",
        dtype=DType.NUMERIC,
        units=V_UNITS,
        annotations=[],
        parents=["v"],
    ),
    MeasurementType(
        "v-cel",
        description="Cellular volume of an organ. ",
        synonyms=["Vcel", "vcel", "Cellular volume"],
        dtype=DType.NUMERIC,
        units=V_UNITS,
        annotations=[],
        parents=["v"],
    ),
    MeasurementType(
        "Q-blo",
        description="The volume of blood per unit time passing through a "
        "specified location, such as a point in a blood vessel or an entire organ.  ",
        synonyms=["Qblo"],
        dtype=DType.NUMERIC,
        units=FLOW_UNITS,
        annotations=[
            (BQB.IS, "ncit/C94866"),
        ],
        parents=["pharmacokinetic-measurement"],
    ),
    MeasurementType(
        "P",
        description="A measure of the rate at which a substrate can pass water. ",
        synonyms=["Permeability"],
        dtype=DType.NUMERIC,
        units=RATE_UNITS,
        annotations=[
            (BQB.IS, "ncit/C71611"),
        ],
        parents=["pharmacokinetic-measurement"],
    ),
    MeasurementType(
        "SA",
        description="Surface area of cells. ",
        synonyms=["Surface area"],
        dtype=DType.NUMERIC,
        units=SURFACE_UNITS,
        annotations=[],
        parents=["pharmacokinetic-measurement"],
    ),
]
