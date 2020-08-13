<template>

  <v-card v-if="exists"
      class="mx-auto"
      max-width="1000"
      outlined
  >
    <v-list-item three-line>
      <v-list-item-content>
        <div class="overline mb-4"><json-button :resource_url="url()"></json-button> {{ data.ntype.toUpperCase() }} <span v-if="data.dtype != 'undefined'">({{ data.dtype.toUpperCase() }})</span></div>
        <v-list-item-title class="headline mb-1">{{ data.label }}</v-list-item-title>
        <v-list-item-subtitle>Parents: {{ parents_labels.length>0 ? parents_labels.join(', ') : "-" }}</v-list-item-subtitle>
      </v-list-item-content>
    </v-list-item>

    <div v-if="data.description & data.description.length>0">
      {{ data.description }}<br />
    </div>

    <div v-if="data.annotations && data.annotations.length>0">
      <span  v-for="annotation in data.annotations" :key="annotation.term">
      <v-chip
          class="ma-1"
          color="black"
          dark
          pill
          small
      >
        {{annotation.relation}}|<strong>{{annotation.collection}}</strong>|{{ annotation.term }}
      </v-chip>

      <span v-if="annotation.label"><strong>{{annotation.label}}</strong></span> {{annotation.description ? annotation.description: ""}}<br />
      </span>
    </div>

    <div v-if="data.xrefs && data.xrefs.length>0">
      <span class="label">Database links</span><br />
        <v-chip  v-for="xref in data.xrefs" :key="xref.url"
            class="ma-1"
            color="black"
            outlined
            pill
            small
            :href="xref.url"
        >
        <strong>{{ xref.name }}</strong>|{{ xref.accession}}
        </v-chip>
      <br />
    </div>

    <div v-if="data.synonyms && data.synonyms.length>0">
      <span class="label">Synonyms</span><br />
      <ul>
        <li v-for="synonym in data.synonyms" :key="synonym">
          {{ synonym }}
        </li>
      </ul>
    </div>
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
      exists: false,
    }
  },
  computed: {
    parents_labels: function () {
      let labels = []
      let parents = this.data.parents
      if (parents){
        for (let i=0; i<parents.length; i++ ){
          labels.push(parents[i].label)
        }
      }
      return labels
    }
  },
  methods: {
    url() {
      let entry_id = (this.$route.path).split('/').slice(-1)[0];
      return `${this.$store.state.endpoints.api}info_nodes/${entry_id}/?format=json`;
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