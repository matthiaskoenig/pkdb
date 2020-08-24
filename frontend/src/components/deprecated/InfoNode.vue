<template>
  <info-node-detail v-if="exists" :data="data" />
</template>

<script>
import axios from 'axios'
import InfoNodeDetail from '../detail/InfoNodeDetail'

export default {
  components: {
    InfoNodeDetail
  },
  data() {
    return {
      data: null,
      exists: false,
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
</style>
