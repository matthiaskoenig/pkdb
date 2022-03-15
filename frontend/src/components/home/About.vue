<template>
  <div id="about" class="main">
    <h2>About</h2>
    <h3>Team</h3>
    <p>
      PK-DB is developed from the <a href="https://livermetabolism.com">Systems Medicine of the Liver Group</a> at the Humboldt-University Berlin.
    </p>
    <p>
      <user-avatar username="mkoenig"/>
      <user-avatar username="janekg"/>
      <user-avatar username="kgreen"/>
      <user-avatar username="dimitra"/>
      <user-avatar username="jbrandhorst"/>
      <user-avatar username="deepa"/>
      <user-avatar username="yduport"/>
      <user-avatar username="FlorBar"/>
      <user-avatar username="adriankl"/>
      <user-avatar username="dannythekey"/>
      <user-avatar username="SaraD-hub"/>
      <user-avatar username="balcisue"/>
      <user-avatar username="paula-ogata"/>
      <user-avatar username="lepujolh"/>
      <user-avatar username="stemllb"/>
      <user-avatar username="jonaspk98"/>

    </p>
    <p>If you have questions or feedback please contact
      <a href="mailto:koenigmx@hu-berlin.de" title="koenigmx@hu-berlin.de">
        <v-icon color="black"
                small>fas fa-envelope
        </v-icon>
      </a>&nbsp;
      <a href="mailto:koenigmx@hu-berlin.de" title="koenigmx@hu-berlin.de">koenigmx@hu-berlin.de</a>
      <br/>
      To report an issue use
      <a href="https://github.com/matthiaskoenig/pkdb/issues/new" title="Report an issue" target="_blank">
        <v-icon color="black" small>fas fa-fire</v-icon>
      </a> <a href="https://github.com/matthiaskoenig/pkdb/issues/new" title="Report an issue" target="_blank">https://github.com/matthiaskoenig/pkdb/issues/new</a>
    </p>

    <h3>How to cite</h3>
    <p>

      <b>PK-DB: pharmacokinetics database for individualized and stratified computational modeling</b><br/>
      <i>Grzegorzewski J, Brandhorst J, Green K, Eleftheriadou D, Duport Y, Bartsch F, Köller A, Ke DYJ, De Angelis S, König M.</i><br />
      Nucleic Acids Res. 2021 Jan 8;49(D1):D1358-D1364. doi: <a href="https://doi.org/10.1093/nar/gkaa990">10.1093/nar/gkaa990</a>. PMID: <a href="https://pubmed.ncbi.nlm.nih.gov/33151297/">33151297</a>

    </p>

    <h3>Licensing</h3>
    <p>
      All data is governed by the PK-DB's <a
        href="https://github.com/matthiaskoenig/pkdb/blob/develop/TERMS_OF_USE.md">Terms of use</a>
    </p>

    <h3>Funding</h3>
    <p>
      <a href="https://www.bmbf.de/" target="_blank"><img src="/assets/images/bmbf.png" height="50"/></a>&nbsp;&nbsp;
      <a href="https://www.dfg.de/" target="_blank"><img src="/assets/images/dfg.jpeg" height="50"/></a>&nbsp;&nbsp;
      <a href="https://www.denbi.de/" target="_blank"><img src="/assets/images/denbi.png" height="50"/></a>&nbsp;&nbsp;
      <a href="http://www.lisym.org" target="_blank"><img src="/assets/images/lisym.png" height="50"/></a>&nbsp;&nbsp;
    </p>
    <p>
      This project is supported by the Federal Ministry of Education and Research (BMBF, Germany) within the research
      network Systems Medicine of the Liver (LiSyM, grant number 031L0054).
      This work was supported by the German Research Foundation (DFG) within the Research Unit Programme FOR 5151
      QuaLIPerF by grant number 436883643.  The infrastructure is provided by the BMBF-funded de.NBI Cloud within the German Network for
      Bioinformatics Infrastructure (de.NBI)[031A537B, 031A533A, 031A538A, 031A533B, 031A535A,031A537C, 031A534A, 031A532B].

      <br/><br/>

    </p>
  </div>
</template>

<script>
export default {
  name: 'About',
}
</script>

<style scoped>
</style>
