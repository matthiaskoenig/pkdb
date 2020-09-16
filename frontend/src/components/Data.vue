<template>
  <v-container v-if="!loading" fluid>
    <search-navigation />
    <table-tabs/>
  </v-container>
</template>

<script>
import TableTabs from './tables/TableTabs';
import SearchNavigation from './search/SearchNavigation'
import {ApiInteractionMixin} from "../apiInteraction";

export default {
  name: "Data",
  mixins: [ApiInteractionMixin],
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
  }
</script>

<style scoped>
</style>
