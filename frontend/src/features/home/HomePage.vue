<script setup lang="ts">
import HomeStatistics from "./HomeStatistics.vue";
defineOptions({ name: "HomePage" });
</script>
<template>
  <div class="home-page">
    <section class="home-hero">
      <p class="eyebrow">Evidence for computational modeling</p>
      <h1>Pharmacokinetic data,<br />with its scientific context.</h1>
      <p class="hero-intro">
        Explore curated clinical and pre-clinical studies. Connect measurements
        to subjects, interventions and the evidence behind them.
      </p>
      <v-btn to="/data" color="primary" size="large">
        Explore pharmacokinetic data </v-btn
      ><v-btn to="/curation" variant="outlined" size="large" class="ml-3">
        Browse vocabulary
      </v-btn>
    </section>
    <HomeStatistics />
    <section class="content-page">
      <h2>From studies to reusable data</h2>
      <p>
        PK-DB provides high-quality pharmacokinetic data enriched with the
        metadata needed for computational modeling and data integration. Groups
        and individuals describe subjects and their characteristics;
        interventions describe dosing; measurements include concentration
        profiles, AUC, clearance and half-lives.
      </p>
      <h2>Example study</h2>
      <p>
        See how a publication connects to structured subjects, interventions and
        measurements.
      </p>
      <img
        src="/assets/images/pkexample2.png"
        alt="Example of extracting pharmacokinetic study information into PK-DB"
        class="example-study"
      />
      <p>
        RV Patwardhan, P V Desmond, R F Johnson, S Schenker. The Journal of
        Laboratory and Clinical Medicine, 1980.
      </p>
      <v-btn to="/data/PKDB00057" variant="outlined">Open example study</v-btn>
      <h2>About</h2>
      <p>
        PK-DB is developed by the
        <a href="https://livermetabolism.com"
          >Systems Medicine of the Liver Group</a
        >
        at Humboldt University Berlin.
      </p>
      <p>
        Questions and feedback:
        <a href="mailto:koenigmx@hu-berlin.de">koenigmx@hu-berlin.de</a>.
        <a href="https://github.com/matthiaskoenig/pkdb/issues/new"
          >Report an issue</a
        >.
      </p>
      <h3>How to cite</h3>
      <p>
        <b
          >PK-DB: pharmacokinetics database for individualized and stratified
          computational modeling</b
        ><br />
        <i
          >Grzegorzewski J, Brandhorst J, Green K, Eleftheriadou D, Duport Y,
          Bartsch F, Köller A, Ke DYJ, De Angelis S, König M.</i
        ><br />
        Nucleic Acids Res. 2021 Jan 8;49(D1):D1358-D1364. doi:
        <a href="https://doi.org/10.1093/nar/gkaa990">10.1093/nar/gkaa990</a>.
        PMID: <a href="https://pubmed.ncbi.nlm.nih.gov/33151297/">33151297</a>
      </p>

      <h3>Licensing</h3>
      <p>
        All data is governed by the PK-DB's
        <a
          href="https://github.com/matthiaskoenig/pkdb/blob/develop/TERMS_OF_USE.md"
          >Terms of use</a
        >
      </p>

      <h3>Funding</h3>
      <p>
        <a href="https://www.bmbf.de/"
          ><img
            src="/assets/images/bmbf.png"
            height="50"
            alt="Research funder logo" /></a
        >&nbsp;&nbsp;
        <a href="https://www.dfg.de/"
          ><img
            src="/assets/images/dfg.jpeg"
            height="50"
            alt="Research funder logo" /></a
        >&nbsp;&nbsp;
        <a href="https://www.denbi.de/"
          ><img
            src="/assets/images/denbi.png"
            height="50"
            alt="Research funder logo" /></a
        >&nbsp;&nbsp;
        <a href="http://www.lisym.org"
          ><img
            src="/assets/images/lisym.png"
            height="50"
            alt="Research funder logo" /></a
        >&nbsp;&nbsp;
      </p>
      <p>
        This project is supported by the Federal Ministry of Education and
        Research (BMBF, Germany) within the research network Systems Medicine of
        the Liver (LiSyM, grant number 031L0054). This work was supported by the
        German Research Foundation (DFG) within the Research Unit Programme FOR
        5151 QuaLIPerF by grant number 436883643. The infrastructure is provided
        by the BMBF-funded de.NBI Cloud within the German Network for
        Bioinformatics Infrastructure (de.NBI)[031A537B, 031A533A, 031A538A,
        031A533B, 031A535A,031A537C, 031A534A, 031A532B].

        <br /><br />
      </p>
    </section>
  </div>
</template>
