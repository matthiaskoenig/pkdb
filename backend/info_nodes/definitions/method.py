"""Definition of methods and assays."""

from pymetadata.core.miriam import BQB

from ..node import DType, InfoNode, Method

METHOD_NODES: list[InfoNode] = [
    Method(
        sid="assay",
        description="A qualitative or quantitative analysis performed to determine the "
        "amount of a particular constituent in a sample or the biological "
        "or pharmacological properties of a drug.",
        parents=[],
        dtype=DType.ABSTRACT,
        annotations=[
            (BQB.IS, "NCIT:C60819"),
            (BQB.IS, "obi/OBI_0000070"),
            (BQB.IS, "sio/SIO_001007"),
        ],
        synonyms=[],
    ),
    Method(
        sid="nr-method",
        name="NR",
        label="Not reported (method)",
        description="Method not reported.",
        parents=["assay"],
    ),
    Method(
        sid="enzymatic-assay",
        name="enzymatic assay",
        label="enzymatic assay",
        description="A method used to measure the relative activity of a specific "
        "enzyme or its concentration in solution. Typically an enzyme "
        "substrate is added to a buffer solution containing enzyme and "
        "the rate of conversion of substrate to product is measured under "
        "controlled conditions. Many classical enzymatic assay methods "
        "involve the use of synthetic colorimetric substrates and "
        "measuring the reaction rates using a spectrophotometer.",
        annotations=[
            (BQB.IS, "https://bioregistry.io/SCDO:0000436"),
        ],
        parents=["assay"],
    ),
    Method(
        sid="colorimetric-assay",
        name="colorimetric assay",
        label="colorimetric assay",
        description="The determination of the spectral absorbance of a solution. "
        "This method is often used to determine the concentration of a "
        "chemical in a solution.",
        annotations=[
            (BQB.IS, "chmo/https://bioregistry.io/CHMO:0000001"),
        ],
        parents=["assay"],
        synonyms=[
            "colorimetric method",
            "automated colorimetric method",
            "colorimetry",
        ],
    ),
    Method(
        sid="elisa",
        name="ELISA",
        label="enzyme-linked immunosorbent assay (ELISA)",
        description="A highly sensitive technique for detecting and measuring antigens "
        "or antibodies in a solution; the solution is run over a surface "
        "to which immobilized antibodies specific to the substance have "
        "been attached, and if the substance is present, it will bind to the "
        "antibody layer, and its presence is verified and visualized with "
        "an application of antibodies that have been tagged in some way.",
        annotations=[
            (BQB.IS, "NCIT:C16553"),
        ],
        parents=["enzymatic-assay"],
    ),
    Method(
        sid="immunofluorescence",
        name="immunofluorescence",
        description="Microscopic analysis of amount, structure and/or localization of "
        "specific proteins in cells or tissues by staining with "
        "fluorescently-labeled primary or secondary antibodies.",
        parents=["assay"],
        annotations=[
            (BQB.IS, "https://bioregistry.io/MMO:0000662"),
        ],
        synonyms=[],
    ),
    Method(
        sid="plasma-binding-measurement",
        name="plasma binding measurement",
        description="plasma binding measurement",
        parents=["assay"],
        dtype=DType.ABSTRACT,
        annotations=[
            (BQB.IS, "NCIT:C60819"),
        ],
        synonyms=[],
    ),
    Method(
        sid="competition-dialysis",
        name="competition dialysis",
        description="The separation of molecules in solution by the difference in their rates of diffusion "
        "through a semipermeable membrane. In competition dialysis an array of nucleic acid structures and "
        "sequences is dialysed against a common test ligand solution. After equilibration, "
        "the amount of ligand bound to each structure or sequence is determined by absorbance or "
        "fluorescence measurements. Since all structures and sequences are in equilibrium with the same "
        "free ligand concentration, the amount bound is directly proportional to the ligand binding affinity.",
        parents=["plasma binding measurement"],
        annotations=[
            (BQB.IS, "chmo/https://bioregistry.io/CHMO:0002405"),
        ],
        synonyms=["equilibrium-dialysis"],
    ),
    Method(
        sid="ultra-filtration",
        name="ultra-filtration",
        description="A separation process whereby a solution containing a solute of molecular size significantly "
        "greater than that of the solvent molecule is removed from the solvent by the application of "
        "hydraulic pressure which forces only the solvent to flow through a suitable membrane",
        parents=["plasma binding measurement"],
        annotations=[
            (BQB.IS, "chmo/https://bioregistry.io/CHMO:0001645"),
        ],
        synonyms=[],
    ),
    Method(
        sid="chromatography",
        description="A technique for the separation of complex mixtures that relies on the differential "
        "affinities of substances for a gas or liquid mobile medium and for a stationary "
        "adsorbing medium through which they pass. ",
        parents=["assay"],
        dtype=DType.ABSTRACT,
        annotations=[
            (BQB.IS, "NCIT:C60819"),
        ],
        synonyms=[],
    ),
    Method(
        sid="emit",
        name="EMIT",
        label="Enzyme Multiplied Immunoassay Technique (EMIT)",
        description="A type of homogenous immunoassay in which sample is applied to a reagent mixture of enzyme-labeled "
        "ligand, antibody, and substrate. Substrate binding to enzyme leads to inactivation and "
        "unlabeled-ligand in the sample can be quantified by colorimetric analysis.",
        parents=["assay"],
        annotations=[
            (BQB.IS, "NCIT:C111196"),
        ],
    ),
    Method(
        sid="spectrophotometry",
        name="Spectrophotometry",
        label="spectrophotometry",
        description="A laboratory test that produces a quantitative measurement of the reflection or "
        "transmission properties of a material as a function of wavelength.",
        parents=["assay"],
        annotations=[
            (BQB.IS, "NCIT:C116701"),
        ],
    ),
    Method(
        sid="radioenzymatic-assay",
        name="radioenzymatic assay",
        label="radioenzymatic assay",
        description="An assay in which a radioactive substrate is used to quantitate "
        "enzyme activity in a sample or in which a radioactive cofactor "
        "or substrate with an added enzyme is used to quantitate the "
        "level of another substrate in a sample.",
        annotations=[
            (BQB.IS, "https://bioregistry.io/MMO:0000303"),
        ],
        parents=["enzymatic-assay"],
    ),
    Method(
        sid="ria",
        name="RIA",
        label="radioimmunoassay (RIA)",
        description="Radioimmunoassay (RIA) is an immunological technique, "
        "which quantitatively determines antigen and antibody concentrations, "
        "using a radioactively labeled substance (radioligand), either directly or indirectly.",
        parents=["assay"],
        annotations=[
            (BQB.IS, "NCIT:C17057"),
        ],
    ),
    Method(
        sid="radiochromatography-MS-MS",
        name="radiochromatography/MS/MS",
        description="Radiochromatography/MS/MS technique, combining LC MS/MS with radiodetection.",
        parents=["assay"],
        annotations=[],
    ),
    Method(
        sid="cc",
        name="CC",
        label="column chromatography (CC)",
        description="Column chromatography (CC). A process used for separating mixtures by virtue of differences in absorbency. "
        "It involves stationary and mobile phases. The stationary phase was packed in a "
        "column with materials that can be of any partitioning capability, adsorption, "
        "ion exchange, or affinity. The mobile phase (either liquid or gas) "
        "is the mixture that required to be separated.",
        parents=["chromatography"],
        annotations=[
            (BQB.IS, "NCIT:C18242"),
        ],
    ),
    Method(
        sid="tlc",
        name="TLC",
        label="thin-layer chromatography (TLC)",
        description="Thin layer chromatography (TLC). A method of separating and "
        "identifying the components of a complex mixture by differential "
        "movement through a two-phase system, in which the movement is "
        "effected by a flow of a liquid, mobile phase over a stationary "
        "phase composed of a thin layer of adsorbent such as silica gel, "
        "alumina, or cellulose on a flat, inert substrate.",
        parents=["chromatography"],
        annotations=[
            (BQB.IS, "https://bioregistry.io/MMO:0000289"),
            (BQB.IS, "omit/0004175"),
        ],
    ),
    Method(
        sid="hplc",
        name="HPLC",
        label="High-performance liquid chromatography (HPLC)",
        description="High-performance liquid chromatography (HPLC) is a column chromatography where the mobile phase is a liquid, "
        "the stationary phase consists of very small particles and "
        "the inlet pressure is relatively high.",
        parents=["cc"],
        annotations=[
            (BQB.IS, "chmo/https://bioregistry.io/CHMO:0001009"),
        ],
    ),
    Method(
        sid="hplc-ecd",
        name="HPLC/ECD",
        label="High-performance liquid chromatography (HPLC) with electrochemical detector (ECD) ",
        description="Combination of HPLC with electrochemical detection.",
        parents=["hplc"],
        annotations=[],
    ),
    Method(
        sid="hplc-fs",
        name="HPLC/FS",
        label="High-performance liquid chromatography (HPLC) with fluorescence spectrometer (FS) ",
        description="Combination of HPLC with fluorescence spectrometer detection.",
        parents=["hplc"],
        annotations=[
            (BQB.IS, "NCIT:C120692"),
        ],
    ),
    Method(
        sid="hplc-fs-mbb",
        name="HPLC/FS MBB",
        label="High-performance liquid chromatography (HPLC) with fluorescence spectrometer (FS) and with monobromobimane (MBB). ",
        description="Combination of HPLC with fluorescence spectrometer detection and with monobromobimane (MBB) as a marker.",
        parents=["hplc-fs"],
        annotations=[],
    ),
    Method(
        sid="hplc-fs-opa",
        name="HPLC/FS OPA",
        label="High-performance liquid chromatography (HPLC) with fluorescence spectrometer (FS) and with o-phthaldialdehyde (OPA). ",
        description="Combination of HPLC with fluorescence spectrometer detection and with o-phthaldialdehyde (OPA) as a marker.",
        parents=["hplc-fs"],
        annotations=[],
    ),
    Method(
        sid="rp-hplc",
        name="RP-HPLC",
        label="Reversed-phase high-performance liquid chromatography (RP-HPLC)",
        description="Reversed-phase high-performance liquid chromatography (RP-HPLC), reversed-phase high pressure "
        "liquid chromatography, reversed phase high-performance liquid chromatography, "
        "gradient reverse HPLC, RHPLC, reversed-phase high-pressure liquid chromatography, "
        "reverse phase high performance liquid chromatography, gradient reverse high-performance "
        "liquid chromatography, reversed-phase HPLC ",
        parents=["hplc"],
        annotations=[
            (BQB.IS, "chmo/https://bioregistry.io/CHMO:0001259"),
        ],
    ),
    Method(
        sid="hplc-ms",
        name="HPLC MS",
        label="High-performance liquid chromatography-mass spectrometry (HPLC MS)",
        description="An analytical technique in that combines the physical separation "
        "capabilities of high pressure liquid chromatography (HPLC) with "
        "the mass analysis capabilities of mass spectrometry (MS). "
        "Molecular mixtures are initially separated into components by "
        "HPLC. As these components exit the column, they are subjected "
        "to mass spectrometry for identification based on their "
        "mass-to-charge ratio and behavior in a magnetic field.",
        parents=["hplc"],
        annotations=[
            (BQB.IS, "https://bioregistry.io/MMO:0000537"),
            (BQB.IS, "chmo/https://bioregistry.io/CHMO:0000796"),
        ],
        synonyms=["HPLC-MS"],
    ),
    Method(
        sid="hplc-ms-ms",
        name="HPLC MS/MS",
        label="High performance liquid chromatography-tandem mass spectrometry (HPLC MS/MS)",
        description="High performance liquid chromatography-tandem mass spectrometry (HPLC MS/MS) is an analytical "
        "technique wherein high performance liquid chromatography is coupled to tandem mass spectrometry "
        "in order to separate, identify, and quantify substances in a sample. ",
        parents=["hplc"],
        annotations=[
            (BQB.IS, "chmo/https://bioregistry.io/CHMO:0002876"),
            (BQB.IS, "NCIT:C120691"),
        ],
        synonyms=["HPLC-MS/MS"],
    ),
    Method(
        sid="lc-esi-ms",
        name="LC ESI MS",
        label="Liquid chromatography–electrospray ionization mass spectrometry (LC–ESI-MS)",
        description="Mass spectrometry where a sample mixture is first separated by liquid "
        "chromatography before being ionised by forcing the solution (usually in an "
        "organic solvent) through a small heated capillary "
        "(at a flow rate of 1–10 L min-1) into an electric field to produce a very "
        "fine mist of charged droplets.",
        parents=["chromatography"],
        synonyms=["LC-ESI-MS"],
        annotations=[(BQB.IS, "chmo/https://bioregistry.io/CHMO:0000751")],
    ),
    Method(
        sid="rplc-esi-ms",
        name="RPLC ESI MS",
        label="Reversed‐phase liquid chromatography coupled to electrospray ionization and mass spectrometry",
        description="Reversed‐phase liquid chromatography coupled to electrospray ionization and mass spectrometry.",
        parents=["lc-esi-ms"],
        annotations=[],
    ),
    Method(
        sid="ms",
        name="MS",
        label="Mass Spectrometry (MS)",
        description="Mass Spectrometry (MS) is an analytical technique wherein ions are separated according to their ratio "
        "of charge to mass. From the mass spectrum produced, the atomic weight of the particle can be deduced.",
        parents=["assay"],
        dtype=DType.ABSTRACT,
        annotations=[
            (BQB.IS, "NCIT:C17156"),
        ],
    ),
    Method(
        sid="cf-irms",
        name="CF-IRMS",
        label="Continuous-flow isotope ratio mass spectrometry (CFIRMS)",
        description="Continuous-flow isotope ratio mass spectrometry (CFIRMS). Mass spectrometry where the relative "
        "abundance of isotopes in a sample is determined. Measurements are taken immediately after sample "
        "preparation and separately to the standard gas.",
        parents=["ms"],
        annotations=[
            (BQB.IS, "chmo/https://bioregistry.io/CHMO:0000887"),
        ],
    ),
    Method(
        sid="lc-ms",
        name="LC/MS",
        label="Liquid chromatography mass spectrometry (LC/MS)",
        description="Liquid chromatography mass spectrometry (LC/MS) is a hyphenated technique, combining the "
        "separation molecules dissolved in a solvent, with the detection power of mass spectrometry(MS), "
        "a technique to separate gas phase ions according their m/z (mass to charge ratio) value. "
        "Used for drug screening, pharmacology studies, environmental analyses and forensics.",
        parents=["chromatography", "MS"],
        annotations=[
            (BQB.IS, "NCIT:C18475"),
        ],
    ),
    Method(
        sid="lc-ms-ms",
        name="LC MS/MS",
        label="Liquid chromatography-tandem mass spectrometry (LC MS/MS)",
        description="Liquid chromatography-tandem mass spectrometry (LC MS/MS) is a method where a sample mixture is "
        "first separated by liquid chromatography before being ionised and characterised by mass-to-charge "
        "ratio and relative abundance using two mass spectrometers in series.",
        parents=["lc-ms"],
        annotations=[
            (BQB.IS, "CHMO:0000701"),
        ],
    ),
    Method(
        sid="uplc-ms",
        name="UPLC MS",
        label="Liquid chromatography mass spectrometry (UPLC MS)",
        description="A method where a sample mixture is first separated by ultra-performance liquid chromatography before being converted into ions which are characterised by their mass-to-charge ratio and relative abundance.",
        parents=["lc-ms"],
        annotations=[
            (BQB.IS, "CHMO:0000715"),
        ],
    ),
    Method(
        sid="uplc-ms-ms",
        name="UPLC MS/MS",
        label="Ultra-performance liquid chromatography-tandem mass spectrometry (UPLC MS/MS)",
        description="A method where a sample mixture is first separated by ultra-performance liquid chromatography before tandem mass spectrometry characterises the ions by their mass-to-charge ratio and fragmentation.",
        parents=["uplc-ms"],
        annotations=[],
    ),
    Method(
        sid="es-ms-ms",
        name="ES+ MS/MS",
        label="Positive electrospray ionisation tandem mass spectrometry (ES+ MS/MS)",
        description="Positive electrospray ionisation tandem mass spectrometry (ES+ MS/MS) is a mass spectrometry "
        "involving multiple mass-selection steps, with some form of fragmentation "
        "occurring between each stage. Sample ionisation is achieved by forcing a solution "
        "(usually in an organic solvent) of the sample through a small heated capillary "
        "into an electric field to produce a very fine "
        "mist of positively charged droplets.",
        parents=["ms"],
        annotations=[
            (BQB.IS, "chmo/https://bioregistry.io/CHMO:0001109"),
        ],
    ),
    Method(
        sid="hplc-esi-ms",
        name="HPLC-ESI-MS",
        label="HPLC-ESI-MS",
        description="High-performance liquid chromatography-electrospray ionisation mass spectrometry "
        "(HPLC-ESI-MS) is a method where the sample mixture is first separated by high-performance "
        "liquid chromatography before being ionised by forcing a solution (usually in an organic solvent) "
        "of it through a small heated capillary into an electric field to produce a very fine mist of "
        "charged droplets. The ions are then characterised according to mass-to-charge ratio and relative "
        "abundance by mass spectrometry.",
        parents=["ms"],
        annotations=[
            (BQB.IS_VERSION_OF, "chmo/https://bioregistry.io/CHMO:0000482"),
        ],
    ),
    Method(
        sid="hplc-esi-ms/ms",
        name="HPLC-ESI-MS/MS",
        label="HPLC-ESI-MS/MS",
        description="High-performance liquid chromatography-electrospray ionisation tandem mass spectrometry "
        "(HPLC-ESI-MS/MS) is a method where the sample mixture is first separated by high-performance "
        "liquid chromatography before being ionised by forcing a solution (usually in an organic solvent) "
        "of it through a small heated capillary into an electric field to produce a very fine mist of "
        "charged droplets. The ions are then characterised according to mass-to-charge ratio and relative "
        "abundance by two mass spectrometers in series.",
        parents=["hplc-esi-ms"],
        annotations=[
            (BQB.IS_VERSION_OF, "chmo/https://bioregistry.io/CHMO:0000578"),
        ],
    ),
    Method(
        sid="gc-ms-sim",
        name="GC/MS SIM",
        label="GC/MS SIM",
        description="Mass spectrometry where the intensities of one "
        "or more specific ion beams are recorded rather "
        "than the entire mass spectrum.",
        parents=["ms"],
        annotations=[
            (BQB.IS_VERSION_OF, "chmo/https://bioregistry.io/CHMO:0000571"),
        ],
    ),
    Method(
        sid="glc-ms",
        name="GLC/MS",
        label="GC/MS",
        description="Gas-liquid chromatographic/mass spectrometric technique.",
        parents=["ms"],
        annotations=[],
    ),
    Method(
        sid="uv-spectrophotometry",
        name="UV spectrophotometry",
        description="Spectroscopy where the sample absorbs radiation from the "
        "ultraviolet region (190–400 nm) resulting in electronic "
        "transitions within the sample.",
        parents=["assay"],
        annotations=[(BQB.IS, "chmo/https://bioregistry.io/CHMO:0001253")],
    ),
    Method(
        sid="lc-uv",
        name="LC/UV",
        label="LC/UV",
        description="A LC-UV system is a device system that has a liquid chromatograph and an ultra-violet "
        "detector component.",
        parents=["uv-spectrophotometry"],
        annotations=[],
    ),
    Method(
        sid="hplc-uv",
        name="HPLC/UV",
        description="A HPLC-UV system is a device system that has a liquid chromatograph and an ultra-violet "
        "detector component.",
        parents=["lc-uv"],
        annotations=[],
    ),
    Method(
        sid="hplc-ms-uv",
        name="HPLC/MS/UV",
        description="A HPLC-MS-UV system is a device system that has a liquid "
        "chromatograph and an mass spectrometry ultra-violet "
        "detector component after gas chromatochraphy",
        parents=["lc-uv"],
        annotations=[],
    ),
    Method(
        sid="gc",
        name="GC",
        label="Gas chromatography",
        description="Gas chromatography. An analytical technique in that combines the physical separation capabilities "
        "of gas chromatography (GC) with the mass analysis capabilities of mass spectrometry (MS). "
        "Molecular mixtures are initially vaporized and separated into components by GC. "
        "As these components exit the column, they are subjected to mass spectrometry for "
        "identification based on their mass-to-charge ratio and behavior in a magnetic field.",
        parents=["chromatography"],
        annotations=[
            (BQB.IS, "omit/0009469"),
            (BQB.IS, "chmo/https://bioregistry.io/CHMO:0000497"),
        ],
    ),
    Method(
        sid="gas-lc",
        name="G-L C",
        label="Gas-liquid chromatography (GLC)",
        description="Gas-liquid chromatography (GLC) is gas chromatography method where the stationary phase is a liquid.",
        parents=["gc"],
        annotations=[(BQB.IS, "chmo/https://bioregistry.io/CHMO:0001016")],
    ),
    Method(
        sid="cgc",
        name="CGC",
        label="Capillary gas chromatography",
        description="Capillary gas chromatography",
        parents=["gc"],
        annotations=[
            (BQB.IS, "https://bioregistry.io/FIX:0000922"),
        ],
    ),
    Method(
        sid="gc-ms",
        name="GC/MS",
        label="Gas chromatography mass spectrometry (GC/MS)",
        description="Gas chromatography mass spectrometry. An analytical technique "
        "wherein gas chromatography is coupled to mass spectrometry in order "
        "to separate, identify, and quantify substances in a sample.",
        parents=["gc", "ms"],
        annotations=[
            (BQB.IS, "NCIT:C111203"),
        ],
    ),
    Method(
        sid="scintillation-counting",
        name="scintillation counting",
        description="It involves the incorporation of radiolabeled precursors into "
        "uniform distribution with a liquid medium capable of converting "
        "the kinetic energy of nuclear emissions into light energy. "
        "A scintillation counter is used to measure ionizing radiation.",
        parents=["assay"],
        annotations=[
            # (BQB.IS, "bao/0000405"),
            (BQB.IS, "omit/0013490"),
        ],
        synonyms=[
            "liquid scintillation counting",
            "LSC",
        ],
    ),
    Method(
        sid="fpia",
        name="FPIA",
        label="fluorescence polarization immunoassay (FPIA)",
        description="Fluorescence polarization immunoassay (FPIA) is a class of in "
        "vitro biochemical test used for rapid detection of antibody or "
        "antigen in sample.",
        parents=["assay"],
        annotations=[(BQB.IS, "omit/0016769")],
        synonyms=[],
    ),
    Method(
        sid="sphygmomanometer",
        name="sphygmomanometer",
        description="An instrument used for non-invasive determination of arterial "
        "blood pressure, generally consisting of an inflatable cuff and "
        "a pressure readout device, classically, a column of mercury.",
        parents=["assay"],
        annotations=[(BQB.IS, "NCIT:C69317")],
        synonyms=[],
    ),
    Method(
        sid="scale",
        name="scale",
        description="An instrument or machine for weighing.",
        parents=["assay"],
        annotations=[(BQB.IS, "https://bioregistry.io/MMO:0000217")],
        synonyms=[],
    ),
    Method(
        sid="electrocardiography",
        name="electrocardiography",
        description="A procedure that displays the electrical activity of the heart.",
        parents=["assay"],
        annotations=[(BQB.IS, "NCIT:C38053")],
        synonyms=["ECG"],
    ),
    Method(
        sid="flame-photometry",
        name="flame photometry",
        description="A photoelectric flame photometer is an instrument used in "
        "inorganic chemical analysis to determine the concentration of "
        "certain metal ions, among them sodium, potassium, lithium, and "
        "calcium.",
        parents=["assay"],
        annotations=[(BQB.IS, "NCIT:C69317")],
        synonyms=[
            "flame photometry",
            "photoelectric flame photometer",
            "flame emission spectroscopy",
            "FES",
        ],
    ),
    Method(
        sid="potentiometry",
        name="potentiometry",
        description="An electroanalytical technique in which the electrical potential "
        "of a solution is measured to determine the composition of the "
        "sample, by comparing the constant potential of the reference "
        "electrode with the actual potential of the indicator electrode.",
        parents=["assay"],
        annotations=[(BQB.IS, "NCIT:C142343")],
        synonyms=[
            "direct potentiometry",
        ],
    ),
    Method(
        sid="photoplethysmography",
        name="photoplethysmography",
        description="A technique for assessing blood flow by placing an infrared emitting diode along with a sensor, "
        "on the surface of the skin over a blood vessel with the amount of light reflected back to the "
        "sensor being inversely proportional to the number of red blood cells flowing through the vessel.",
        parents=["assay"],
        annotations=[
            (BQB.IS, "https://bioregistry.io/MMO:0000008"),
            (BQB.IS, "NCIT:C198843"),
            (BQB.IS, "SNOMEDCT:72075005"),
        ],
        synonyms=[],
    ),
    Method(
        sid="icp-aes",
        name="ICP-AES",
        label="inductively coupled plasma atomic emission spectrometry (ICP-AES)",
        description="Inductively coupled plasma atomic emission spectrometry. Used "
        "for instance for the detection of gadolinium in Gd-EOB-DTPA samples.",
        parents=["assay"],
        annotations=[],
        synonyms=[],
    ),
    Method(
        sid="mri",
        name="MRI",
        label="Magnetic resonance imaging (MRI)",
        description="Techniques that uses magnetic fields and radiowaves to form "
        "images, typically to investigate the anatomy and physiology of "
        "the human body.",
        parents=["assay"],
        annotations=[(BQB.IS, "NCIT:C16809")],
        synonyms=[
            "Magnetic resonance imaging",
            "Magnetic resonance tomography",
            "MRT",
            "NMRI",
            "Nuclear magnetic resonance imaging",
        ],
    ),
    Method(
        sid="mri-se",
        name="MRI-SE",
        label="Magnetic resonance imaging spin echo (MRI-SE)",
        description="MRI based on spin echo technique.",
        parents=["mri"],
        annotations=[],
        synonyms=[],
    ),
    Method(
        sid="mri-gre",
        name="MRI-GRE",
        label="Magnetic resonance imaging gradient echo (MRI-GRE)",
        description="MRI based on gradient technique.",
        parents=["mri"],
        annotations=[],
        synonyms=[],
    ),
    Method(
        sid="ultrasound-imaging",
        name="ultrasound imaging",
        description="The use of high-frequency sound waves to generate images of the body.",
        parents=["assay"],
        annotations=[(BQB.IS, "NCIT:C17230")],
        synonyms=[],
    ),
    Method(
        sid="doppler-ultrasound",
        name="Doppler ultrasound",
        description="Diagnostic imaging that uses sound waves (ultrasound) applying "
        "the Doppler effect, with frequency-shifted ultrasound "
        "reflections produced by moving targets (usually red blood cells) "
        "in the bloodstream along the ultrasound axis in direct "
        "proportion to the velocity of movement of the targets, to "
        "determine both direction and velocity of blood flow.",
        parents=["assay"],
        annotations=[
            (BQB.IS, "NCIT:C62781"),
            (BQB.IS, "https://bioregistry.io/MMO:0000198"),
        ],
        synonyms=[],
    ),
    Method(
        sid="calculated",
        name="calculated",
        description="Calculated from other measured variables. State formula in "
        "comments if available.",
        parents=["assay"],
        annotations=[],
        synonyms=[],
    ),
    Method(
        sid="coagulation-assay",
        name="coagulation assay",
        description="Coagulation assays are blood tests that evaluate the blood's ability to "
        "clot and measure how long this process takes, helping diagnose bleeding "
        "disorders or monitor anticoagulant therapy. These tests assess various "
        "components of the clotting cascade—such as clotting factors and pathways—to "
        "identify abnormalities that could lead to excessive bleeding or unwanted clot "
        "formation. E.g. measurement of prothrombin time (PT).",
        annotations=[
            (BQB.IS, "SNOMEDCT:103800002"),  # Coagulation factor assay (procedure)
        ],
        parents=["assay"],
    ),
    Method(
        sid="breath-test-assay",
        name="breath test assay",
        description="A technique to assess the presence and/or amount of analyte(s) in breath exhaled into a device.",
        parents=["assay"],
        annotations=[
            (BQB.IS, "SNOMEDCT:164790002"),
            (BQB.IS, "NCIT:C116515"),
        ],
    ),
]
