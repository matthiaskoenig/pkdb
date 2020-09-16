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
import {StoreInteractionMixin} from "../storeInteraction";

export default {
  name: "Data",
  mixins: [StoreInteractionMixin],
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
              this.show_type = "study";
              this.detail_info = response.data;
              this.display_detail = true;
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

  }}
</script>

<style scoped>
</style>
