<template>
  <div style="color: white">

      <div class="overline">
        <h2> How to search in PK-DB? </h2>
      </div>


     <p align="justify">
        Data in PK-DB is represented as entries, with every single <code>Entry</code> having information
        on the
      </p>
      <ul>
          <li>Study in which it was recorded,</li>
          <li>Individual or Group it was measured on,</li>
          <li>Intervention(s) which were applied,</li>
          <li>and the Output(s), Timecourse(s) or Scatter(s) which were measured.</li>
      </ul>
      <p align="justify">
        To filter database entries filters can be applied individually or in combination on Studies, Groups/Individuals,
        Interventions, Outputs/Timecourses. To apply a filter on one of the categories select the search form and start
        typing. The available options for the query are displayed. When moving the mouse over an option the
        description of the respective information is shown.
        The search examples below show some typical filter queries.
      </p>
      <p align="justify">
        By clicking on results after searching the results detail view is shown which allows exploration of the results.
        Results can be downloaded by clicking on the download button.
      </p>

    <div class="overline">
      <h3> Search examples</h3>
    </div>
      <div class="mt-4 pt-0" flat v-for="example in examples" :key="example.title">
          <v-btn
              class="pt-2"
              width="100%"
              small
              v-on:click="query(example.query)"
          >
            <v-icon left small >{{ faIcon('search') }}</v-icon>
            <div  class="pa-1" v-html="example.title"></div>
          </v-btn>
        <div class="pt-2" align="justify" v-html="example.description" />
      </div>
  </div>

</template>

<script>
import {IconsMixin} from "../../icons";

export default {
  name: "SearchHelp",
  mixins: [IconsMixin],
  data() {
    return {
      examples: [
        {
          title: "Select single study",
          description: "In this example all entries which belong to the study <code>Abernethy1982</code> are selected. " +
              "By selecting a study in a filter all entries from the\n" +
              "study are added to the search results.",
          query: [
            {
              "query_type": "queries",
              "key": "studies__sid__in",
              "value": [{"name": "Abernethy1982", "sid": "PKDB00198",}]
            },
          ]
        },
        {
          title: "Half-life after midazolam <br/>  in healthy Human subjects",
          description: "In this example we are interested in available half-lifes after administration" +
              "of midazolam. Herefor, we select <code>midazolam</code> in the intervention substance and <code>half-life</code> " +
              "in the output measurement type. Furthermore we filter the subjects by species <code>Homo sapiens</code> " +
              "and <code>healthy</code>.",
          query: [
            {
              "query_type": "queries",
              "key": "interventions__substance_sid__in",
              "value": [{"sid": "midazolam", "label": "midazolam"}]
            },
            {
              "query_type": "queries",
              "key": "outputs__measurement_type_sid__in",
              "value": [{"sid": "thalf", "label": "elimination half-life"}]
            },
            {
              "query_type": "subjects_queries",
              "key": "choice_sid__in",
              "value": [{"sid": "homo-sapiens", "label": "Homo sapiens"},{"sid": "healthy-yes", "label": "healthy"}]
            },
          ]
        }
      ]
    }
  },
  methods: {
    query(example) {
      this.reset()
      for (let q of example) {
        this.update_store(q)
      }
      this.$store.dispatch('updateAction', {
        key: "hide_search",
        value: false,
      })
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
  },
}

</script>

<style scoped>

</style>