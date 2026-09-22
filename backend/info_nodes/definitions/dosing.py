"""Definition of administration routes, method and form."""

from pymetadata.core.miriam import BQB

from ..node import Application, DType, Form, InfoNode, MeasurementType, Route
from ..units import DOSING_UNITS, NO_UNIT, RESTRICTED_DOSING_UNITS

DOSING_NODES: list[InfoNode] = [
    MeasurementType(
        sid="dosing-intervention",
        name="dosing intervention",
        description="Dosing intervention.",
        parents=["intervention"],
        dtype=DType.ABSTRACT,
    ),
    MeasurementType(
        sid="dosing",
        description="Dosing.",
        parents=["dosing intervention"],
        dtype=DType.NUMERIC,
        units=DOSING_UNITS,
    ),
    MeasurementType(
        sid="restricted-dosing",
        name="restricted dosing",
        description="Subset of dosing which can be used to calculate pharmacokinetics.",
        parents=["dosing intervention"],
        dtype=DType.NUMERIC,
        units=RESTRICTED_DOSING_UNITS,
    ),
    MeasurementType(
        sid="qualitative-dosing",
        name="qualitative dosing",
        description="Qualitative dosing.",
        parents=["dosing intervention"],
        dtype=DType.NUMERIC,
        units=[*DOSING_UNITS, NO_UNIT],
    ),
]

ADMINISTRATION_ROUTE_NODES: list[InfoNode] = [
    Route(
        sid="administration-route",
        name="administration route",
        description="Route of administration of drug or substance. Designation of the "
        "part of the body through which or into which, or the way in which, "
        "the medicinal product is intended to be introduced. "
        "In some cases a medicinal product "
        "can be intended for more than one route and/or method of "
        "administration.",
        parents=[],
        dtype=DType.ABSTRACT,
        annotations=[
            (BQB.IS, "NCIT:C38114"),
        ],
        synonyms=[
            "ROUTE",
            "route of administration (ROA)",
            "Route of Administration",
            "Drug Route of Administration",
            "ROUTE OF ADMINISTRATION",
            "Route of Drug Administration",
        ],
    ),
    Route(
        sid="intraperitoneal-route",
        name="intraperitoneal route",
        description="Intraperitoneal route of administration. Administration of a "
        "drug via injection or infusion of a substance into the peritoneum, "
        "where it is absorbed by the lining.",
        parents=["administration route"],
        annotations=[
            (BQB.IS, "NCIT:C38258"),
        ],
        synonyms=[
            "Intraperitoneal Route of Administration",
            "Intraperitoneal",
            "IP",
            "I-PERITON",
        ],
    ),
    Route(
        sid="intravascular-route",
        name="intravascular route",
        description="Intravascular route of administration. The administration of an agent "
        "within a vessel or vessels.",
        parents=["administration route"],
        annotations=[
            (BQB.IS, "NCIT:C38273"),
        ],
        synonyms=[
            "Intravascular Route of Administration",
            "Intravascular",
            "INTRAVASCULAR",
            "I-VASC",
        ],
    ),
    Route(
        sid="iv",
        name="iv",
        label="intravenous (iv)",
        description="Intravascular intra-venous administration. Administration of a drug "
        "within or into a vein or veins. Introduction of the drug directly "
        "into venous circulation results in 100% bioavailability due to an "
        "absence of the absorption phase, provides a precise and continuous "
        "mode of drug therapy, especially for drugs with a narrow therapeutic "
        "index.",
        parents=["intravascular route"],
        annotations=[
            (BQB.IS, "NCIT:C38276"),
        ],
        synonyms=[
            "Intravenous",
            "Intravenous use",
            "Intravenous Route of Administration",
            "IV",
            "INTRAVENOUS",
        ],
    ),
    Route(
        sid="intraarterial",
        description="Intravascular intra-arterial administration. Intraarterial drug "
        "injection or infusion is a method of delivering a drug directly into "
        "artery or arteries to localize its effect to a particular organ/body "
        "region, while minimizing the exposure of the body to potentially "
        "toxic effects of the agent. The method is considered more dangerous "
        "than intravenous administration and should be reserved to experts. "
        "The first-pass and cleansing effects of the lung are not available "
        "when the agent is given by this route.",
        parents=["intravascular route"],
        annotations=[
            (BQB.IS, "NCIT:C38222"),
        ],
        synonyms=[
            "I-arter",
            "Intraarterial Infusion",
            "Intraarterial use",
            "Intraarterial Route of Administration",
            "Intra-Arterial",
            "I-ARTER",
            "Intra-Arterial Route of Administration",
            "IA",
            "INTRA-ARTERIAL",
            "Intraarterial Injection",
        ],
    ),
    Route(
        sid="transluminal",
        description="Transluminal route of administration. The route of drug "
        "administration involving the passage of an inflatable catheter "
        "along the lumen of a blood vessel.",
        parents=["intravascular route"],
        annotations=[
            (BQB.IS, "NCIT:C38306"),
        ],
        synonyms=[
            "Transluminal Route of Administration",
            "T-LUMIN",
        ],
    ),
    Route(
        sid="intramuscular",
        description="Extravascular administration in the muscle. Intramuscular injection "
        "is a route of drug administration via injection into muscle tissue. "
        "Aqueous or oleaginous solutions and emulsions or suspensions may be "
        "administered. Absorption rates, delay in availability of the drug "
        "to the systemic circulation, and duration of effect are "
        "perfusion-limited, depend on molecular size of the agent, volume, "
        "and osmolarity of the drug solution, fat content of the injection "
        "site, and patient physical activity.",
        parents=["administration route"],
        annotations=[(BQB.IS, "NCIT:C28161")],
        synonyms=[
            "IM",
            "intramuscular injection",
            "Intramuscular Injection",
            "INTRAMUSCULAR",
            "Intramuscular",
            "Intramuscular use",
            "Intramuscular Route of Administration",
        ],
    ),
    Route(
        sid="oral",
        name="oral",
        label="oral (po)",
        description="Extravascular oral route of administration of substance. "
        "The introduction of a substance to the mouth or into the "
        "gastrointestinal tract by the way of the mouth, usually for "
        "systemic action. It is the most common, convenient, and usually "
        "the safest and least expensive route of drug administration, "
        "but it uses the most complicated pathway to the tissues and "
        "bioavailability varies. The disadvantages of method are hepatic "
        "first pass metabolism and enzymatic degradation of the drug "
        "within the gastrointestinal tract. This prohibits oral "
        "administration of certain classes of drugs especially "
        "peptides and proteins.",
        parents=["administration route"],
        annotations=[(BQB.IS, "NCIT:C38288")],
        synonyms=[
            "Per Os",
            "Intraoral Route of Administration",
            "Oral Route of Administration",
            "Orally",
            "Oral",
            "ORAL",
            "Oral use",
            "PO",
        ],
    ),
    Route(
        sid="rectal",
        description="Extravascular rectal administration of substance. "
        "The introduction of a substance into the gastrointestinal tract by "
        "the way of the rectum, usually for systemic action. Depending on "
        "the molecular structure, drugs cross the rectal wall via either "
        "intercellular or tight junctions interconnecting the mucosal "
        "cells. Drug absorption is usually around 50% of normal oral dose. "
        "Due to the drainage pattern of the rectal veins, the hepatic "
        "first-pass effect tends to increase as the dosage form is placed "
        "deeper into the rectum. Solid suppositories represent greater than "
        "98% of all rectal dosage forms.",
        parents=["administration route"],
        annotations=[
            (BQB.IS, "NCIT:C38295"),
        ],
        synonyms=[
            "Rectal use",
            "Rectal",
            "Per Rectum",
            "RECTAL",
            "Rectal Route of Administration",
        ],
    ),
    Route(
        sid="inhalation",
        description="Extravascular pulmonary application via inhalation of substance. "
        "Administration of a substance in the form of a gas, aerosol, "
        "or fine powder via the respiratory tract, usually by oral or "
        "nasal inhalation, for local or systemic effect.",
        parents=["administration route"],
        annotations=[
            (BQB.IS, "NCIT:C38216"),
        ],
        synonyms=[
            "inhalation",
            "Inhalation Route of Administration",
            "INH",
            "Inhalation use",
            "RESPIRATORY (INHALATION)",
            "RESPIR",
            "Respiratory (Inhalation)",
            "Inhalation",
        ],
    ),
    Route(
        sid="buccal",
        description="Extravascular administration between the cheek and the gum. "
        "Administration of a substance through the mucosal membrane on the "
        "inside of the cheek or the back of the mouth. Buccal route "
        "bypasses first pass metabolism and avoids pre-systemic elimination "
        "in the gastrointestinal tract. The buccal environment is well "
        "supplied with both vascular and lymphatic drainage and is well "
        "suited for a retentive device. This is a feasible alternative for "
        "systemic delivery of orally inefficient drugs, such as peptide and "
        "protein drug molecules.",
        parents=["administration route"],
        annotations=[
            (BQB.IS, "NCIT:C38216"),
        ],
        synonyms=[
            "Buccal",
            "BUCCAL",
            "Buccal Route of Administration",
            "BUCC",
            "Buccal use",
        ],
    ),
    Route(
        sid="intradermal",
        description="Extravascular administration in skin. Intradermal injection is a "
        "method of drug administration within the substance of the skin, "
        "particularly the dermis.",
        parents=["administration route"],
        annotations=[
            (BQB.IS, "NCIT:C38238"),
        ],
        synonyms=[
            "I-DERMAL",
            "Intradermal Injection",
            "Intradermal Route of Administration",
            "Intracutaneous",
            "Intradermal",
            "INTRADERMAL",
            "DL",
            "Intradermal use",
            "IC",
            "ID",
            "I-dermal",
        ],
    ),
    Route(
        sid="cutaneous",
        description="Administration to the skin. Cutaneous Drug Delivery: This refers "
        "to medications applied directly onto the skin's surface, "
        "targeting local conditions without significant systemic "
        "absorption. The primary aim is to treat localized issues "
        "like skin infections or rashes. Also see 'transdermal'.",
        parents=["administration route"],
        annotations=[
            (BQB.IS, "NCIT:C13309"),
            (BQB.IS, "omit/0001709"),
        ],
        synonyms=["dermal"],
    ),
    Route(
        sid="transdermal",
        description="Transdermal Drug Delivery: This method involves the "
        "administration of active ingredients through the skin to "
        "achieve systemic effects. Transdermal systems, such as patches, "
        "are designed to penetrate the skin barrier, allowing drugs to "
        "enter the bloodstream and exert effects throughout the body. "
        "Also see 'cutaneous'.",
        parents=["administration route"],
        annotations=[],
        synonyms=[],
    ),
    Route(
        sid="vaginal",
        description="Administration to the vagina.",
        parents=["administration route"],
        annotations=[
            (BQB.IS, "NCIT:C13309"),
            (BQB.IS, "omit/0001709"),
        ],
        synonyms=[],
    ),
    Route(
        sid="topical",
        description="The application of drug preparations to the surfaces of the body, especially the skin or mucous membranes. This method of treatment is used to avoid systemic side effects when high doses are required at a localized area or as an alternative systemic administration route, to avoid hepatic processing for example.",
        parents=["administration route"],
        annotations=[
            (BQB.IS, "NCIT:C13344"),
        ],
        synonyms=[],
    ),
    Route(
        sid="ocular",
        description="Administration to the eye.",
        parents=["topical"],
        annotations=[
            (BQB.IS, "NCIT:C87163"),
        ],
        synonyms=[],
    ),
    Route(
        sid="intraduodenal",
        description="Administration of a drug within the duodenum.",
        parents=["administration route"],
        annotations=[
            (BQB.IS, "NCIT:C38241"),
        ],
        synonyms=[
            "Intraduodenal Route of Administration",
            "INTRADUODENAL",
            "Intraduodenal",
            "I-DUOD",
        ],
    ),
    Route(
        sid="subcutaneous",
        description="Extravascular administration into fat under the skin. Drug "
        "administration beneath the skin. It provides for relatively slow, "
        "sustained release of the drug. The rate of absorption into the "
        "blood is perfusion-limited, proportional to the amount of drug at "
        "the site and can be enhanced by chemical or physical stimulation of "
        "blood flow. Subcutaneous administration minimizes the risks "
        "associated with intravascular injection: for subcutaneous infusions, "
        "external and implantable pumps are used.",
        parents=["administration route"],
        annotations=[
            (BQB.IS, "NCIT:C38238"),
        ],
        synonyms=[
            "SC",
            "Subcutaneous Route of Administration",
            "SUBCUTANEOUS",
            "Subcutaneous",
            "Subcutaneous use",
            "Subdermal Route of Administration",
        ],
    ),
    Route(
        sid="sublingual",
        description="Administration of a drug beneath the tongue. The route provides "
        "rapid absorption, the drug immediately enters the bloodstream "
        "without first passing through the intestinal wall and liver. "
        "However, most drugs cannot be taken this way because they may "
        "be absorbed incompletely or erratically.",
        parents=["administration route"],
        annotations=[
            (BQB.IS, "NCIT:C38300"),
        ],
        synonyms=[
            "SUBLINGUAL",
            "Sublingual Route of Administration",
            "SL",
            "Sublingual use",
            "Sublingual",
        ],
    ),
    Route(
        sid="nr-route",
        name="NR",
        label="Not reported (route)",
        description="Route not reported.",
        parents=["administration route"],
        annotations=[],
    ),
]

APPLICATION_NODES: list[InfoNode] = [
    Application(
        sid="administration-method",
        name="administration method",
        description="Method of applying the given substance or drug.",
        parents=[],
        dtype=DType.ABSTRACT,
        annotations=[],
    ),
    Application(
        sid="constant-infusion",
        name="constant infusion",
        description="Constant infusion of substance. Introduction of a drug directly into "
        "circulation at a constant rate.",
        parents=["administration method"],
        annotations=[
            (BQB.IS_VERSION_OF, "NCIT:C38275"),
        ],
    ),
    Application(
        sid="variable-infusion",
        name="variable infusion",
        description="Variable infusion of substance. Substance is infused with a variable rate.",
        parents=["administration method"],
        annotations=[],
    ),
    Application(
        sid="clamp-infusion",
        name="clamp infusion",
        description="Variable infusion of a substance to clamp substance to certain value. "
        "For instance hyperglycemic clamps to clamp plasma glucose. See also "
        "'variable infusion'.",
        parents=["variable-infusion"],
        annotations=[],
    ),
    Application(
        sid="single-dose",
        name="single dose",
        description="Single dose of substance. In case of iv route this corresponds to "
        "a bolus injection. In case of oral route this is a single dose "
        "taken orally (often as tablet or solution).",
        parents=["administration method"],
        annotations=[],
    ),
    Application(
        sid="multiple-dose",
        name="multiple dose",
        description="Multiple dosing of substance. More then one dose is applied at "
        "multiple time points.",
        parents=["administration method"],
        annotations=[],
    ),
    Application(
        sid="nr-application",
        name="NR",
        label="Not reported (application)",
        description="Application not reported.",
        parents=["administration method"],
        annotations=[],
    ),
]

ADMINISTRATION_FORM_NODES: list[InfoNode] = [
    Form(
        sid="administration-form",
        name="administration form",
        description="Form of the given administration. The form in which active and/or "
        "inert ingredient(s) are physically presented.",
        parents=[],
        dtype=DType.ABSTRACT,
        annotations=[(BQB.IS, "NCIT:C42636")],
        synonyms=[
            "DOSFRM",
            "dosage form",
            "Pharmaceutical Formulation",
            "Pharmaceutical Dose Form",
            "Drug Dose Form",
            "Pharmaceutical Dosage Form",
            "Dosage Form",
            "Dose form",
        ],
    ),
    Form(
        sid="nr-form",
        name="NR",
        label="Not reported (administration form)",
        description="Administration form not reported.",
        parents=["administration form"],
        annotations=[],
    ),
    Form(
        sid="capsule",
        description="Administration of substance as capsule. A drug packaging type usually "
        "in a cylindrical shape with rounded ends. Capsule shells may be made "
        "from gelatin, starch, or cellulose, or other suitable materials, "
        "may be soft or hard, and are filled with solid or liquid drug "
        "products.",
        parents=["administration form"],
        annotations=[
            (BQB.IS, "NCIT:C92708"),
            (BQB.IS, "NCIT:C154433"),
        ],
        synonyms=[
            "Capsule-Container",
            "CAPSULE",
            "Capsule",
            "Capsule Dose Form Category",
        ],
    ),
    Form(
        sid="pill",
        description="A dose of medicine or placebo in the form of a small pellet.",
        parents=["administration form"],
        annotations=[
            (BQB.IS, "NCIT:C122634"),
            (BQB.IS, "NCIT:C25394"),
        ],
        synonyms=[
            "PILL",
            "Pill Dose Form Category",
            "Pill Dosage Form",
        ],
    ),
    Form(
        sid="granules",
        description="Administration of substance as granules. Small particles gathered "
        "into a larger, permanent aggregate in which the original "
        "particles can still be identified",
        parents=["administration form"],
        annotations=[
            (BQB.IS_VERSION_OF, "NCIT:C149557"),
        ],
        synonyms=[
            "Granules Dose Form",
        ],
    ),
    Form(
        sid="tablet",
        description="Administration of substance as tablet. A solid composed of a mixture "
        "of that active and/or inert ingredient(s) are pressed or "
        "compacted together, usually in the form of a relatively flat and "
        "round, square or oval shape.",
        parents=["administration form"],
        annotations=[
            (BQB.IS, "NCIT:C42998"),
        ],
        synonyms=[
            "Tablet Dose Form",
            "TAB",
            "tab",
            "Tab",
            "Tablet",
            "TABLET",
            "Tablet Dosage Form",
        ],
    ),
    Form(
        sid="chewable-tablet",
        name="chewable tablet",
        description="Administration of substance as chewable tablet.",
        parents=["tablet"],
        annotations=[
            (BQB.IS_VERSION_OF, "NCIT:C42998"),
        ],
        synonyms=[],
    ),
    Form(
        sid="inhaler",
        name="inhaler",
        description="A device by means of which a medicinal product can be administered by inspiration through the nose or the mouth.",
        parents=["administration form"],
        annotations=[
            (BQB.IS, "NCIT:C16738"),
            (BQB.IS, "SNOMEDCT:334980009"),
        ],
        synonyms=[],
    ),
    Form(
        sid="film",
        name="film",
        description="A film application form is a drug dosage form in which the active compound is incorporated into a thin film that is applied to a body surface, such as the oral mucosa or skin, where the drug is released and absorbed locally or systemically.",
        parents=["administration form"],
        annotations=[],
        synonyms=[],
    ),
    Form(
        sid="transdermal-film",
        name="transdermal film",
        description="A transdermal film is a thin drug-containing layer applied to the skin that releases the active compound for absorption through the skin into the systemic circulation.",
        parents=["film"],
        annotations=[],
        synonyms=[],
    ),
    Form(
        sid="oral-soluble-film",
        name="oral soluble film",
        description="An oral soluble film is a thin drug-containing film placed in the mouth that rapidly dissolves or disintegrates in saliva, releasing the active compound for local or systemic absorption.",
        parents=["film"],
        annotations=[],
        synonyms=[],
    ),
    Form(
        sid="solution",
        description="Administration of substance as solution. A type of liquid "
        "pharmaceutical dose form consisting of one or more substances "
        "dissolved in, or miscible with, an appropriate solvent, "
        "forming a single-phase liquid.",
        parents=["administration form"],
        annotations=[
            (BQB.IS, "NCIT:C154598"),
        ],
        synonyms=[
            "Solution Dosage Form Category",
            "Solution",
        ],
    ),
    Form(
        sid="eye-drops",
        name="eye drops",
        description="Drops applied to the eye.",
        parents=["administration form"],
        annotations=[],
        synonyms=[],
    ),
    Form(
        sid="elixir",
        description="A solution composed of a clear, sweetened hydroalcoholic liquid in which active and/or inert "
        "ingredient(s) are dissolved.",
        parents=["administration form"],
        annotations=[
            (BQB.IS, "NCIT:C42912"),
        ],
        synonyms=[
            "Elixir Dosage Form Category",
            "Elixir",
        ],
    ),
    Form(
        sid="suspension",
        description="Administration of substance as suspension. Insoluble solid "
        "particles composed of active and/or inert ingredient(s) that "
        "are dispersed in a liquid.",
        parents=["administration form"],
        annotations=[
            (BQB.IS, "NCIT:C42994"),
        ],
        synonyms=[
            "Suspension Dosage Form Category",
            "Suspension",
        ],
    ),
    Form(
        sid="suppository",
        description="Administration of substance as suppository. A type of solid "
        "pharmaceutical dose form consisting of a material that is "
        "usually formed by moulding, of a suitable shape, volume and "
        "consistency for insertion into the rectum where it dissolves, "
        "disperses or melts.",
        parents=["administration form"],
        annotations=[
            (BQB.IS, "NCIT:C154601"),
        ],
        synonyms=[
            "Suppository Dosage Form Category",
            "Suppository",
        ],
    ),
    Form(
        sid="syrup",
        description="Administration of substance as syrup. A solution or suspension "
        "composed of a viscid vehicle that contains a high concentration of "
        "sucrose or other sugars and active and/or inert ingredient(s).",
        parents=["administration form"],
        annotations=[
            (BQB.IS, "NCIT:C42996"),
        ],
        synonyms=[
            "Syrup Dosage Form",
            "Syrup Dose Form",
            "SYRUP",
            "Syrup",
        ],
    ),
    Form(
        sid="patch",
        description="Administration of substance via patch. A solid composed of an "
        "impermeable occlusive backing and a formulation matrix in which "
        "the active and/or inert ingredient(s) are dissolved or dispersed; "
        "possibly includes an adhesive layer.",
        parents=["administration form"],
        annotations=[
            (BQB.IS, "NCIT:C42968"),
        ],
        synonyms=[
            "Patch Dosage Form",
            "Patch Dose Form",
            "PATCH",
            "Patch",
        ],
    ),
    Form(
        sid="vaginal_ring",
        name="vaginal ring",
        description="Administration of substance via vaginal ring, e.g. contraceptives. "
        "A hollow ring that is inserted into the vagina in order to "
        "facilitate delivery of vaginal intracavitary radiation therapy.",
        parents=["administration form"],
        annotations=[
            (BQB.IS, "NCIT:C192577"),
            (BQB.IS, "gsso/GSSO:003371"),
        ],
        synonyms=[
            "Vaginal Ring Dosage Form",
            "Vaginal Ring Dose Form",
            "VAGINAL RING",
            "Vaginal Ring",
        ],
    ),
    Form(
        sid="chewing-gum",
        label="chewing gum",
        description="A semi-solid composed of synthetic, polymerized polysaccharide and flavorings, "
        "intended to be chewed to release active and/or inert ingredient(s).",
        parents=["administration form"],
        annotations=[
            (BQB.IS, "NCIT:C42894"),
        ],
        synonyms=[
            "Chewing Gum Dosage Form",
            "Chewing Gum Dose Form",
            "GUM CHEWING",
            "Gum, chewing",
            "GUM, CHEWING",
            "Gum, Chewing",
            "Medicated chewing-gum",
        ],
    ),
    Form(
        sid="powder",
        label="powder",
        description="A solid composed of a mixture of dry, finely divided active "
        "and/or inert ingredient(s)",
        parents=["administration form"],
        annotations=[
            (BQB.IS, "NCIT:C42972"),
        ],
        synonyms=[],
    ),
    Form(
        sid="food",
        label="food",
        description="As part of food or a meal.",
        parents=["administration form"],
        annotations=[],
        synonyms=[],
    ),
]
