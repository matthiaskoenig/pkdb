<template>
  <v-container fluid>
    <search-navigation />
    <table-tabs/>
  </v-container>
</template>

<script>
import TableTabs from './tables/TableTabs';
import SearchNavigation from './search/SearchNavigation'
import axios from 'axios'

export default {
  name: "Data",
  components: {
    SearchNavigation,
    TableTabs
  },
  computed: {
    sid(){
      return this.$route.params.sid
    },
    hide_search:  {
      get() {
        return this.$store.state.hide_search
      },
      set(value) {
        this.$store.dispatch('updateAction', {
          key: "hide_search",
          value: value,
        })
      }
    },
  },
  created() {
    if(this.sid){
      this.getStudy(this.sid)
      this.hide_search = false
    }
  },
  methods: {
    getStudy(sid) {
      // object is an InfoNode
      let url = `${this.$store.state.endpoints.api}studies/${sid}/?format=json`;

      // get data (FIXME: caching of InfoNodes in store)
      axios.get(url)
          .then(response => {
            this.updateSearch(response.data)
            this.$store.state.show_type = "study";
            this.$store.state.detail_info =  response.data;
            this.$store.state.display_detail = true;
          })
          .catch(err => {
            this.exists = false;
            console.log(err)
          })
          .finally(() => this.loading = false);
    },
    updateSearch(study_info) {
      let study = {
          "query_type": "queries",
          "key": "studies__sid__in",
          "value": [study_info]}
      this.reset()
      this.update_store(study)
    },
    reset() {
      this.$store.commit('resetQuery');
    },
    update_store(q) {
      this.$store.dispatch('updateQueryAction', {
        query_type: q.query_type,
        key: q.key,
        value: q.value,
      })
    }
  }}
</script>

<style scoped>
</style>
