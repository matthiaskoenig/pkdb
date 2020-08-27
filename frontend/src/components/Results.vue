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
  name: "Results",
  components: {
    SearchNavigation,
    TableTabs
  },
  computed: {}
}
</script>

<style scoped>
</style>
