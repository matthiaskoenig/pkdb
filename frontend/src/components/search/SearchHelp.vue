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
        The resulting data entry has the form<br/>
        <code>Entry(study, group/individual, intervention(s), output/timecourse)</code>
      </p>
      <p>
        To filter database entries filters can be applied individually or in combination on Studies, Groups/Individuals,
        Interventions, Outputs/Timecourses. To apply a filter on one of the categories select the search form and start
        typing. The available options for the query are displayed. When moving the mouse over an option the
        description of the respective information is shown.
        The search examples below show some typical filter queries.
      </p>
      <p>
        By clicking on results after searching the results detail view is shown which allows exploration of the results.
        Results can be downloaded by clicking on the download button.
      </p>


    </v-card-text>

    <v-card-title>
      Search examples
    </v-card-title>

    <v-card-text v-for="example in examples" :key="example.title">
      <v-btn text
             small
             v-on:click="query(example.query)"
      >
        <v-icon left small color="#41b883">{{ faIcon('search') }}</v-icon>
        {{ example.title }}
      </v-btn>
      <div v-html="example.description"></div>

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
              "value": [{"sid": "Abernethy1982"}]
            },
          ]
        },
        {
          title: "Half-life after midazolam in healthy Human subjects.",
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
        },
        {
          title: "Complex query",
          description: "shows a filter on the data for:\n" +
              "      <ul>\n" +
              "        <li> only individuals (no groups) </li>\n" +
              "        <li> (and) all subjects under investigation are potentially healthy. Either they are healthy or they belong to a\n" +
              "          group which contains healthy subjects. </li>\n" +
              "        <li> (and) curators are mkoenig or janekg </li>\n" +
              "        <li> (and) substance used in any of the interventions is caffeine </li>\n" +
              "        <li> (and) outputs measurement types are auc_inf or auc_end </li>\n" +
              "      </ul>",
          query: [
            {"query_type": "subjects_boolean", "key": "groups_query", "value": false},
            {
              "query_type": "subjects_queries",
              "key": "choice_sid__in",
              "value": [{"sid": "healthy-yes", "label": "healthy"}]
            },
            {
              "query_type": "queries_users", "key": "studies__curators__in", "value": [
                {"username": "mkoenig", "first_name": "Matthias", "last_name": "König"},
                {"username": "janekg", "first_name": "Jan", "last_name": "Grzegorzewski"}]
            },
            {
              "query_type": "queries",
              "key": "interventions__substance_sid__in",
              "value": [{"sid": "caf", "label": "caffeine"}]
            },
            {
              "query_type": "queries",
              "key": "outputs__measurement_type_sid__in",
              "value": [{"sid": "auc-inf", "label": "area under curve (AUC) infinity"}, {
                "sid": "auc-end",
                "label": "area under curve (AUC) end"
              }]
            },
          ],
        }
      ]
    }
  },
  methods: {
    query(example) {
      for (let q of example) {
        this.update_store(q)
      }
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