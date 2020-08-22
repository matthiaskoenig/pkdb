<template>
  <v-card flat outlined>
    <v-card-title>
      How to search data in PK-DB?
    </v-card-title>
    <v-card-text>
    <p>
    Data in PK-DB is represented as entries, with every single <code>Entry</code> having information
    on the
      <ul>
        <li>Study in which it was recorded,</li>
        <li>Individual or Group it was measured on,</li>
        <li>Intervention or Interventions which were applied,</li>
        <li>and the Output or Timecourse which was measured.</li>
      </ul>
    </p>
    <p>
    The resulting data entry has the form<br />
      <code>Entry(study, group/individual, intervention(s), output/timecourse)</code>
    </p>
    <p>
    To filter database entries filters can be applied individually or in combination on Studies, Groups/Individuals,
      Interventions, Outputs/Timecourses. To apply a filter on one of the categories select the search form and start
      typing. The available options for the query are displayed. When moving the mouse over an option the
      description of the respective information is shown.
      The search examples below show some typical filter queries.
    </p>
    </v-card-text>

    <v-card-title>
      Search examples
    </v-card-title>
    <v-card-text>
      <v-btn text
             small
             v-on:click="query(example2)"
      >
        <v-icon left small color="#41b883">{{ faIcon('search') }}</v-icon>  Example 1
      </v-btn>
      shows a filter on the data for:
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
import {IconsMixin} from "../../icons";

export default {
  name: "SearchHelp",
  mixins: [IconsMixin],
  data() {
    return {
      example1: [
        {"query_type": "subjects_boolean", "key": "groups_query", "value": false},
        {"query_type": "subjects_queries", "key": "choice_sid__in", "value": [{"sid":"healthy-yes", "label"	:"healthy"}]},
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