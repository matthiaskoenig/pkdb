<template>
  <div id="reference-detail">
    <v-card flat>
      <p>
        <span class="font-weight-black">{{ reference.title }}</span><br/>
        <span class="font-weight-light" v-for="(author, index) in reference.authors" :key="index">
                    {{ author.first_name }} {{ author.last_name }},
        </span>
        <br/>
        <span class="font-italic">{{ reference.journal }}, {{ reference.date }}</span> <pubmed :pmid="reference.pmid"/>
      </p>

      <p align="justify">{{ reference.abstract }}</p>

    </v-card>
  </div>
</template>

<script>

import Pubmed from "../info_node/Pubmed";

export default {
  name: "ReferenceDetail",
  components: {
    Pubmed,
  },
  props: {
    reference: {
      type: Object,
    },
    resource_url: {
      type: String
    }
  },
  data() {
    return {
      abstractHidden: true
    }
  },
  computed: {},
  methods: {}
}
</script>

<style scoped>
.v-card {
  padding: 10px;
}
</style>