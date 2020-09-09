<template>
  <v-container fluid>
    <search-navigation />
    <table-tabs/>
  </v-container>
</template>

<script>
import TableTabs from './tables/TableTabs';
import SearchNavigation from './search/SearchNavigation'

export default {
  name: "Data",
  components: {
    SearchNavigation,
    TableTabs
  },
  computed: {
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
    if(this.$route.params.sid){
      this.load_study(this.$route.params.sid)
      this.hide_search = false
    }
  },
  methods: {
    load_study(sid) {
      let study = {
          "query_type": "queries",
          "key": "studies__sid__in",
          "value": [{"sid": sid,"name":"Seng2009"}]}
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
  },}
</script>

<style scoped>
</style>
