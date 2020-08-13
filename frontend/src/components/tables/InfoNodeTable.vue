<template>

  <v-card v-if="exists"
          class="mx-auto"
          max-width="1000"
          outlined
  >
    <v-list-item three-line>
      <v-list-item-content>
        <div class="overline mb-4">
          <json-button :resource_url="url()"></json-button> {{ data.ntype.toUpperCase() }} <span v-if="data.dtype != 'undefined'">({{ data.dtype.toUpperCase() }})</span></div>
        <v-list-item-title class="headline mb-1">{{ data.label }}</v-list-item-title>
        <v-list-item-subtitle>Parents: {{ data.parents.length>0 ? data.parents.join(', ') : "-" }}</v-list-item-subtitle>
      </v-list-item-content>


    </v-list-item>

    {{ data.description }}<br />

    <v-chip v-for="annotation in data.annotations" :key="annotation.term">
      class="ma-1"
      color="black"
      dark
      pill
      small
      >
      {{annotation.relation}}|<strong>{{annotation.collection}}</strong>|{{ annotation.term }}
    </v-chip>
    <span v-if="annotation.label"><strong>{{annotation.label}}</strong></span> {{annotation.description ? annotation.description: ""}}<br />


    <span class="label">Database links</span><br />
    <span v-for="xref in data.xrefs" :key="xref.url">
      <v-chip
          class="ma-1"
          color="black"
          outlined
          pill
          small
          :href="xref.url"
      >
      <strong>{{ xref.name }}</strong>|{{ xref.accession}}
      </v-chip>
    </span>
    <br />
    <span class="label">Synonyms</span><br />
    <ul>
      <li v-for="synonym in data.synonyms" :key="synonym">
        {{ synonym }}
      </li>
    </ul>
  </v-card>

</template>

<script>
import axios from 'axios'

export default {
  name: 'InfoNode',
  components: {},
  data() {
    return {

      data: null,
      ntype:"all",
      exists: false,
    }
  },
  computed: {},
  methods: {
    url() {
      return `${this.$store.state.endpoints.api}info_nodes/?format=json`;
    },
  },
  mounted() {
    axios.get(this.url())
        .then(response => {
          this.data = response.data;
          this.exists = true;
        })
        .catch(err => {
          console.log(err.response.data);
          this.exists = false;
        })
        .finally(() => this.loading = false);
  },
}
</script>
<style>
.label {
  font-weight: bold;
  padding: 5px;
}
</style>