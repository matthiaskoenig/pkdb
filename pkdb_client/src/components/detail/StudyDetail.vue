<template>
    <div id="study-detail">
        <v-layout>
            <!-- Side menu for navigation. -->
            <v-flex xs2 class="study-navigation">
                <v-card class="d-inline-block elevation-12">
                    <v-navigation-drawer
                            floating
                            permanent
                            stateless
                            value="true"
                    >
                        <v-list>
                        <v-list-tile>

                            <v-list-tile-content>
                                <heading :title="study.name" :icon="icon('study')" :resource_url="resource_url"/>
                            </v-list-tile-content>
                        </v-list-tile>
                        </v-list>
                        <v-divider></v-divider>

                        <v-list dense>
                            <v-list-tile
                                    v-for="item in navigation"
                                    :key="item.title"
                                    @click="toggleVisibility(item.id)"
                            >
                                <v-list-tile-action>
                                    <span v-if="visible[item.id]" :title="'Hide ' + item.title">
                                        <v-icon color="primary" >{{ icon(item.icon) }}</v-icon>
                                    </span>
                                    <span v-else :title="'Hide ' + item.title">
                                        <v-icon>{{ icon(item.icon) }}</v-icon>
                                    </span>
                                </v-list-tile-action>

                                <v-list-tile-content>
                                    <v-list-tile-title>{{ item.title }}</v-list-tile-title>
                                </v-list-tile-content>

                            </v-list-tile>
                        </v-list>
                    </v-navigation-drawer>
                </v-card>
            </v-flex>

            <v-flex class="study-content" xs2>&nbsp;</v-flex>
            <v-flex class="study-content" xs10>
                <!-- Study content -->

                <v-layout row wrap>

                    <!-- General Overview -->
                    <v-flex xs12 v-show="visible.general">
                        <v-card>
                            <heading-toolbar :title="'Study: '+study.name" :icon="icon('study')" :resource_url="resource_url"/>
                            <study-info :study="study"/>
                        </v-card>
                    </v-flex>

                    <!-- Groups -->
                    <v-flex xs12 v-show="visible.groups">
                        <get-data v-if="study.groupset" :resource_url="study.groupset">
                            <template slot-scope="groupset">
                                <div v-if="groupset.loaded">
                                    <annotations :item="groupset.data"/>
                                    <groups-table :data="resource(groupset.data.groups)"/>
                                </div>
                            </template>
                        </get-data>
                    </v-flex>

                    <!-- Individuals -->
                    <v-flex xs12 v-show="visible.individuals">
                        <get-data v-if="study.individualset" :resource_url="study.individualset">
                            <template slot-scope="individualset">
                                <div v-if="individualset.loaded">
                                    <annotations :item="individualset.data"/>
                                    <individuals-table :data="resource(individualset.data.individuals)"/>
                                </div>
                            </template>
                        </get-data>
                    </v-flex>

                    <!-- Interventions -->
                    <v-flex xs12 v-show="visible.interventions">
                        <get-data v-if="study.interventionset" :resource_url="study.interventionset">
                            <template slot-scope="interventionset">
                                <div v-if="interventionset.loaded">
                                    <annotations :item="interventionset.data"/>
                                    <interventions-table :data="resource(interventionset.data.interventions)"/>
                                </div>
                            </template>
                        </get-data>
                    </v-flex>

                    <!-- Outputs -->
                    <v-flex xs12>
                        <get-data v-if="study.outputset" :resource_url="study.outputset">
                            <template slot-scope="outputset">
                                <div v-if="outputset.loaded">
                                    <!--
                                    {{ checkhasOutputs(outputset.outputs) }}
                                    {{ checkhasTimecourses(outputset.timecourses) }}
                                    -->
                                    <annotations :item="outputset.data"/>
                                    <OutputsTable v-show="visible.outputs" :data="resource(outputset.data.outputs)"/>
                                    <br />
                                    <TimecoursesTable v-show="visible.timecourses" :data="resource(outputset.data.timecourses)"/>
                                </div>
                            </template>
                        </get-data>
                    </v-flex>
                </v-layout>


            </v-flex>
        </v-layout>
    </div>
</template>

<script>
    import {isEmpty} from "@/utils"
    import {lookup_icon} from "@/icons"

    import StudyInfo from "./StudyInfo";
    import GroupsTable from "../tables/GroupsTable";
    import IndividualsTable from '../tables/IndividualsTable';
    import InterventionsTable from "../tables/InterventionsTable";
    import OutputsTable from "../tables/OutputsTable";
    import TimecoursesTable from "../tables/TimecoursesTable";


    export default {
        name: "StudyDetail",
        components: {
            StudyInfo: StudyInfo,
            GroupsTable: GroupsTable,
            IndividualsTable: IndividualsTable,
            InterventionsTable: InterventionsTable,
            OutputsTable: OutputsTable,
            TimecoursesTable: TimecoursesTable,
        },

        props: {
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
                    general: true,
                    groups: true,
                    individuals: true,
                    interventions: true,
                    outputs: true,
                    timecourses: true
                },
                navigation : [
                    {
                        id: 'general',
                        icon: 'about',
                        title: 'Overview'
                    },
                    {
                        id: 'groups',
                        icon: 'groups',
                        title: 'Groups'
                    },
                    {
                        id: 'individuals',
                        icon: 'individuals',
                        title: 'Individuals'
                    },
                    {
                        id: 'interventions',
                        icon: 'interventions',
                        title: 'Interventions'
                    },
                    {
                        id: 'outputs',
                        icon: 'outputs',
                        title: 'Outputs'
                    },
                    {
                        id: 'timecourses',
                        icon: 'timecourses',
                        title: 'Timecourses'
                    },
                ]
            }
        },
        computed: {
            // vuex store
            api() {
                return this.$store.state.endpoints.api;
            },
        },
        // Fetches posts when the component is created.
        methods:{
            icon: function (key) {
                return lookup_icon(key)
            },

            toggleVisibility(item_id){
                this.visible[item_id] = !this.visible[item_id];
            },


            checkhasOutputs(array) {
                if (array.length !== 0){
                    this.hasOutputs = true
                }
            },
            checkhasTimecourses(array) {
                if (array.length !== 0){
                    this.hasTimecourses = true
                }
            },
            checkhasInterventions(array) {
                if (array.length !== 0){
                    this.hasInterventions = true
                }
            },
            checkhasIndividuals(array) {
                if (array.length !== 0){
                    this.hasIndividuals = true
                }
            },
            checkhasGroups(array) {
                if (array.length !== 0){
                    this.hasGroups = true
                }
            },
            resource(data){
                return {entries:data, count:data.length}
            },
            isEmpty(string){
                return isEmpty(string);
            },
            isActive(bool){
                if(bool){
                    return " md-raised md-primary";}
                else{return "";}
            }
        }
    }
</script>

<style scoped>
    .study-navigation {

        height: 100%; /* 100% Full-height */
        position: fixed; /* Stay in place */
        z-index: 1; /* Stay on top */
        top: 50px; /* Stay at the top */
        left: 0;
        #background-color: #111; /* Black*/
        overflow-x: hidden; /* Disable horizontal scroll */
    }


</style>