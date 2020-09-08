<template>
 <div>
    <study-search/>
    <user-search on="creator"/>
    <user-search on="curators" />

    <v-row>
      <v-checkbox class="pl-4" v-model="licence_open" label="Open" hide-details></v-checkbox>
      <v-checkbox class="pl-4" v-model="licence_closed" label="Closed" hide-details></v-checkbox>
    </v-row>
 </div>
</template>

<script>
import StudySearch from "./StudySearch";
import UserSearch from "./UserSearch";

export default {
  name: "StudySearchForm",
  components: {
    StudySearch,
    UserSearch,
  },
  computed: {
    licence_open: {
      get(){
        return this.$store.state.licence_boolean.open
      },
      set (value) {
        this.$store.dispatch('updateQueryAction', {
          query_type: "licence_boolean",
          key: "open",
          value: value,      })
      }
    },
    licence_closed: {
      get(){
        return this.$store.state.licence_boolean.closed
      },
      set (value) {
        this.$store.dispatch('updateQueryAction', {
          query_type: "licence_boolean",
          key: "closed",
          value: value,      })
      },
    },
  },
}

</script>