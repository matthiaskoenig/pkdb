<template>
    <div id="study-detail">

        <!-- navigation bar -->
        <div class="study-navbar">
            <a @click="scrollMeTo('overview')">
              <count-chip :count="study.study_count ? study.study_count: 1" icon="study" name="study"></count-chip>
            </a>

            <a @click="scrollMeTo('groups')">
                <count-chip :count="study.group_count" icon="group" name="group"></count-chip>
            </a>
            <a @click="scrollMeTo('individuals')">
                <count-chip :count="study.individual_count" icon="individual" name="individual"></count-chip>
            </a>
            <a @click="scrollMeTo('interventions')">
                <count-chip :count="study.intervention_count" icon="intervention" name="intervention"></count-chip>
            </a>
            <a @click="scrollMeTo('outputs')">
                <count-chip :count="study.output_count" icon="output" name="output"></count-chip>
            </a>
            <a @click="scrollMeTo('timecourses')">
                <count-chip :count="study.timecourse_count" icon="timecourse" name="timecourse"></count-chip>
            </a>

        </div>

        <!-- study content -->
        <div class="study-content">
            <v-layout row wrap>
                 <!-- Overview -->
                <v-flex ref="overview" xs12 v-show="visible.overview">
                    <v-card>
                        <study-overview :study="study"/>
                    </v-card>
                </v-flex>

                <!-- Groups -->
                <v-flex ref="groups" xs12 v-show="visible.groups">
                    <count-chip :count="study.group_count" icon="group" name="group"></count-chip>
                    <annotations  v-if="study.groupset" :item="study.groupset"/>
                    <groups-table  v-if="study.group_count>0" :search_ids="true" :ids="study.groupset.groups" :autofocus="false"/>
                </v-flex>

                <!-- Individuals -->
                <v-flex  ref="individuals" xs12 v-show="visible.individuals">
                    <count-chip :count="study.individual_count" icon="individual" name="individual"></count-chip>
                    <annotations v-if="study.individualset" :item="study.individualset"/>
                    <individuals-table v-if="study.individual_count>0" :search_ids="true" :ids="study.individualset.individuals" :autofocus="false"/>
                </v-flex>

                <!-- Interventions -->
                <v-flex  ref="interventions" xs12 v-show="visible.interventions">
                    <count-chip :count="study.intervention_count" icon="intervention" name="intervention"></count-chip>
                    <annotations v-if="study.interventionset" :item="study.interventionset"/>
                    <interventions-table v-if="study.intervention_count>0"  :search_ids="true" :ids="study.interventionset.interventions" :autofocus="false"/>
                </v-flex>

                <!-- Outputs -->
                <v-flex xs12 v-show="visible.outputs || visible.timecourses">
                    <annotations  v-if="study.outputset" :item="study.outputset"/>
                    <span ref="outputs"></span>
                    <count-chip :count="study.output_count" icon="output" name="output"></count-chip>
                    <outputs-table v-if="study.output_count>0" v-show="visible.outputs"  :search_ids="true" :ids="study.outputset.outputs" :autofocus="false"/>
                    <br />
                    <span ref="timecourses"></span>
                    <count-chip :count="study.timecourse_count" icon="timecourse" name="timecourse"></count-chip>
                    <timecourses-table v-if="study.timecourse_count>0" v-show="visible.timecourses" :search_ids="true" :ids="study.dataset.subsets" :autofocus="false"/>
                </v-flex>
            </v-layout>
        </div>

    </div>
</template>

<script>
    import {lookupIcon} from "@/icons"

    import {UrlMixin} from "../tables/mixins";
    import StudyOverview from "./StudyOverview";
    import IndividualsTable from '../tables/IndividualsTable';
    import InterventionsTable from "../tables/InterventionsTable";
    import OutputsTable from "../tables/OutputsTable";
    import TimecoursesTable from "../tables/TimecoursesTable";
    import GroupsTable from "../tables/GroupsTable";


    export default {
        name: "StudyDetail",
        components: {
            StudyOverview: StudyOverview,
            GroupsTable: GroupsTable,
            IndividualsTable: IndividualsTable,
            InterventionsTable: InterventionsTable,
            OutputsTable: OutputsTable,
            TimecoursesTable: TimecoursesTable,

        },
        mixins :[UrlMixin],
        props: {
            study_pks: {
                type: Array,
            },
            study: {
                type: Object,
            },
            resource_url: {
                type: String
            }
        },
        data() {
            return {
                visible: {
                    overview: true,
                    groups: true,
                    individuals: true,
                    interventions: true,
                    outputs: true,
                    timecourses: true,
                }
            }
        },
        computed: {},
        methods:{
            scrollMeTo(refName) {
                let element = this.$refs[refName];
                let top = element.offsetTop - 100;
                window.scrollTo(0, top);
            },
            faIcon: function (key) {
                return lookupIcon(key)
            },
            resource(data){
                return {entries:data, count:data.length}
            },
        }
    }
</script>

<style scoped>
    .study-navbar {
        position: fixed;
        top: 48px;
        left: 0;
        z-index: 9999;
        width: 100%;
        height: 32px;
        background-color: #CCCCCC;
    }
    .study-content {
        margin-top: 50px;
    }

</style>
