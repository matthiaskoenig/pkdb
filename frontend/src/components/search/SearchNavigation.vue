<template>
    <v-navigation-drawer
        v-model="drawer"
        :mini-variant.sync="mini"
        clipped
        permanent
        app
        width="400"
    >
      <v-list-item class="px-2">
        <v-list-item-avatar>
          <v-icon> {{faIcon('search')}}</v-icon>
        </v-list-item-avatar>

        <v-list-item-title>Search</v-list-item-title>
          <v-progress-circular
              indeterminate
              color="primary"
              v-if="loading"
          ></v-progress-circular>

        <v-btn v-if="results.studies.count>0"
               fab
               x-small
               text
               @click="downloadData"
               :loading="loadingDownload"
               :disabled="loadingDownload"
               title="Download current results"
        >
          <v-icon small>{{ faIcon('download') }}</v-icon>

        </v-btn>
        <v-btn
              x-small
              fab text
              title="Clear search"
              v-on:click="reset"
          >
            <v-icon small>fas fa fa-trash-alt</v-icon>
          </v-btn>
          <v-btn
              x-small
              fab text
              title="Search help with examples"
              @click.stop="show_help"
          >
            <v-icon small>fas fa fa-question</v-icon>
          </v-btn>

          <v-btn
              icon
              @click.stop="mini = !mini"
          >
            <v-icon>{{faIcon("left_arrow")}}</v-icon>
          </v-btn>


      </v-list-item>

      <v-divider></v-divider>


      <v-list >

        <v-list-item>
          <v-list-item-icon>
              <v-icon>{{faIcon("studies")}}
              </v-icon>
          </v-list-item-icon>

          <v-list-item-content>
            <v-list-item-title>Studies</v-list-item-title>
            <study-search-form/>
          </v-list-item-content>
        </v-list-item>

        <v-list-item >
          <v-list-item-icon>
              <v-icon>{{faIcon("groups")}}
              </v-icon>
          </v-list-item-icon>

          <v-list-item-content>
            <v-list-item-title>Subjects</v-list-item-title>
            <subjects-form
                @subjects__type="update_search_query"
                @subject_queries="update_subject_query"
            />          </v-list-item-content>
        </v-list-item>
        <v-list-item >
          <v-list-item-icon>
              <v-icon>{{faIcon("interventions")}}
              </v-icon>
          </v-list-item-icon>

          <v-list-item-content>
            <v-list-item-title>Interventions</v-list-item-title>
            <intervention-form/>
          </v-list-item-content>
        </v-list-item>
        <v-list-item >
          <v-list-item-icon>
            <v-icon>{{faIcon("outputs")}}
            </v-icon>
          </v-list-item-icon>

          <v-list-item-content>
            <v-list-item-title>Outputs</v-list-item-title>
            <output-form/>
          </v-list-item-content>
        </v-list-item>
      </v-list>
    </v-navigation-drawer>
</template>


<script>
import axios from 'axios'

import CountBadge from "../lib/CountBadge";
import StudySearchForm from "../search/StudySearchForm";
import InterventionForm from "../search/InterventionSearchForm";
import SubjectsForm from "../search/SubjectSearchForm";
import OutputForm from "../search/OutputSearchForm";

import InfoNode from "../deprecated/InfoNode";
import InfoNodeDetail from "../detail/InfoNodeDetail";
import SearchHelp from "../search/SearchHelp";
import StudyOverview from "../detail/StudyOverview";
import {searchTableMixin} from "../tables/mixins";
import {SearchMixin} from "../../search";



export default {
  mixins: [searchTableMixin, SearchMixin],
  name: "SearchNavigation",
  components: {
    CountBadge,
    StudyOverview,
    SearchHelp,
    InfoNodeDetail,
    InfoNode,
    StudySearchForm,
    InterventionForm,
    SubjectsForm,
    OutputForm,
  },
  computed: {
    display_detail() {
      return this.$store.state.detail_display
    },
    detail_info() {
      return this.$store.state.detail_info
    },
    show_type() {
      return this.$store.state.show_type
    }
  },
  methods: {
    reset() {
      this.$store.commit('resetQuery');
    },
    update_subject_query(emitted_object) {
      this.subject_queries = emitted_object;
    },
    show_help() {
      this.$store.state.show_type = 'help'
      this.$store.state.detail_display = true
    },
    update_search_query(emitted_object) {
      for (const [key, value] of Object.entries(emitted_object)) {
        this.queries[key] = value
      }
    },
    getData() {
      this.loading = true
      let headers = {};
      if (localStorage.getItem('token')) {
        headers = {Authorization: 'Token ' + localStorage.getItem('token')}
      }
      axios.get(this.url, {headers: headers})
          .then(res => {
            this.results = res.data
            // store results in store
            this.$store.state.results = this.results
          })
          .catch(err => {
            console.log(err.response.data);
            this.loading = false
          })
          .finally(() => this.loading = false);
    },
  },
  data() {
    return {
      drawer: true,
      items: [
        { title: 'Studies', icon:this.faIcon('studies'),},
        { title: 'Subjects', icon:this.faIcon('groups') },
        { title: 'Interventions', icon:this.faIcon('interventions') },
      ],
      mini: true,
      loadingDownload: false,
      results: {
        studies: {"hash": "", "count": 0},
        interventions: {"hash": "", "count": 0},
        groups: {"hash": "", "count": 0},
        individuals: {"hash": "", "count": 0},
        outputs: {"hash": "", "count": 0},
        timecourses: {"hash": "", "count": 0},
      },
      otype: "pkdata",
      otype_single: "pkdata",
    }
  }
}


</script>

<style>
.v-list-item__content{
  overflow:visible !important;
}
</style>