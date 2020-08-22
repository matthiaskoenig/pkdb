<template>
  <v-card
      outlined
  >
    <v-card-title>
      How to Search in PKDB
    </v-card-title>
    <v-card-text>
      <v-btn text small v-on:click="query(example1)">Example 1</v-btn> shows a filter on the data for:
      <ul>
        <li> only individuals (no groups) </li>
        <li> (and) all subjects under investigation are potentially healthy. Either they are healthy or they belong to a
          group which contains healthy subjects. </li>
        <li> (and) curators are mkoenig or janekg </li>
        <li> (and) substance used in any of the interventions is caffeine </li>
        <li> (and) outputs measurement types are auc_inf or auc_end </li>
      </ul>


    </v-card-text>
  </v-card>
</template>

<script>
export default {
  name: "SearchHelp",
  data() {
    return {
      example1: [
        {"query_type": "subjects_boolean", "key": "groups_query", "value": false},
        {"query_type": "subjects_queries", "key": "choice_sid__in", "value": [{"sid":"healthy", "label"	:"healthy"}]},

        {"query_type": "queries_users", "key": "studies__curators__in", "value": [
            {"username": "mkoenig", "first_name": "Matthias", "last_name": "König"},
            {"username": "janekg", "first_name": "Jan", "last_name": "Grzegorzewski"}]},
        {"query_type": "queries", "key": "interventions__substance_sid__in", "value": [{"sid":"caf", "label"	:"caffeine"}]},
        {"query_type": "queries", "key": "outputs__measurement_type_sid__in", "value": [{"sid":"auc-inf", "label"	:"area under curve (AUC) infinity"},{"sid":"auc-end", "label"	:"area under curve (AUC) end"}]},
      ],
    }
  },
  methods:{
    query(example){
      for (var q of example){
        console.log(q)
        this.update_store(q)
      }
    },
    update_store(q){
      this.$store.dispatch('updateQueryAction', {
        query_type:q.query_type,
        key: q.key,
        value: q.value,
      })
    }
    },

}

</script>

<style scoped>

</style>