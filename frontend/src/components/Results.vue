<template>
  <v-row>
    <v-col>
     <search-navigation />
    </v-col>
    <v-col>
      <table-tabs/>
    </v-col>
  </v-row>
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
