<template>
    <xref v-if="pmid" name="pubmed" :accession="pmid" :url="'https://pubmed.ncbi.nlm.nih.gov/' + pmid"></xref>
</template>

<script>

import Xref from "./Xref";

export default {
  name: "Pubmed",
  components: {
    Xref,
  },
  props: {
    pmid: {
      type: String,
      required: true,
    },
  }
}
</script>

<style scoped>

</style>