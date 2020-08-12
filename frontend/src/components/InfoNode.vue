<template>

  <div v-if="data" id="info-node-detail">
    <json-button :resource_url="url()" />
    <!--{{ data }}<br />-->
    <span class="label">sid</span>: {{ data.sid }}<br />
    <span class="label">name</span> {{ data.name }}<br />
    <span class="label">label</span> {{ data.label }}<br />
    <span class="label">deprecated</span> {{ data.deprecated }}<br />
    <span class="label">node type</span> {{ data.ntype }}<br />
    <span class="label">data type</span> {{ data.dtype }}<br />
    <span class="label">description</span> {{ data.description }}<br />
    <span class="label">synonyms</span> {{ data.synonyms }}<br />
    <span class="label">parents</span> {{ data.parents }}<br />
    <span class="label">annotations</span> {{ data.annotations }}<br />
    <span class="label">xrefs</span> {{ data.xrefs }}<br />
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'InfoNode',
  components: {},
  data() {
    return {
      data: null,
    }
  },
  computed: {},
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
        })
        .catch(err => {
          console.log(err.response.data);
        })
        .finally(() => this.loading = false);
  },
}
</script>
<style>
  .label {
    font-weight: bold;
    background-color: yellow;
    padding: 5px;
  }
</style>