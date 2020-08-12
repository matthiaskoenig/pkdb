<template>
  <div id="info-node-detail">
    <!--{{ data }}<br />-->
    sid: {{ data.sid }}<br />
    name: {{ data.name }}<br />
    label: {{ data.label }}<br />
    deprecated: {{ data.deprecated }}<br />
    node type: {{ data.ntype }}<br />
    data type: {{ data.dtype }}<br />
    description: {{ data.description }}<br />
    synonyms: {{ data.synonyms }}<br />
    parents: {{ data.parents }}<br />
    annotations: {{ data.annotations }}<br />
    xrefs: {{ data.xrefs }}<br />
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
    getData() {
      axios.get(this.url())
          .then(res => {
            this.data = res.data;
          })
          .catch(err => {
            console.log(err.response.data);
          })
          .finally(() => this.loading = false);
    },
  },
  mounted() {
    this.getData()
  },
}
</script>
<style>
</style>