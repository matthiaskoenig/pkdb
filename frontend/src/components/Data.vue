<template>
  <v-container v-if="!loading" fluid>

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
  data () {
    return {
    loading:true,
  }},
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
      this.hide_search=false
    }else{
      this.loading = false
    }
  },
  methods: {
    getStudy(sid) {
      // object is an InfoNode
      let url = `${this.$store.state.endpoints.api}studies/${sid}/?format=json`;
      let headers = {};
      if (localStorage.getItem('token')) {
        headers = {Authorization: 'Token ' + localStorage.getItem('token')}
      }
      // get data (FIXME: caching of InfoNodes in store)
      axios.get(url, {headers: headers})
          .then(response => {
            if(response.data.sid) {
              this.updateSearch(response.data)
              this.$store.state.show_type = "study";
              this.$store.state.detail_info = response.data;
              this.$store.state.display_detail = true;
            }else{
              this.$route.push('/404')
            }
          })
          .catch(err => {
            this.exists = false;
            this.$router.push('/404')
            console.log(err)
          })
          .finally(() => this.loading = false);
    },
    updateSearch(study_info) {
      let study = {
          "query_type": "queries",
          "key": "studies__sid__in",
          "value": [study_info]}
      this.update_store(study)

      this.$store.dispatch('updateAction', {
        "key": "concise",
        "value": false})
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
