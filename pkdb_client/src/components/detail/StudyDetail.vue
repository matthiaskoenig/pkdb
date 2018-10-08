<template>
    <div id="study-detail">

        <v-layout row>
            <v-flex xs2 v-if="false">
                <!-- Side menu for navigation. -->
                <div class="study-navigation">
                <v-card height="350px">
                    <v-navigation-drawer
                            v-model="drawer"
                            permanent
                            absolute
                    >
                        <v-toolbar flat class="transparent">
                            <v-list class="pa-0">
                                <v-list-tile avatar>
                                    <v-list-tile-avatar>
                                        Icon
                                    </v-list-tile-avatar>

                                    <v-list-tile-content>
                                        <v-list-tile-title>Study</v-list-tile-title>
                                    </v-list-tile-content>
                                </v-list-tile>
                            </v-list>
                        </v-toolbar>

                        <v-list class="pt-0" dense>
                            <v-divider></v-divider>

                            <v-list-tile
                                    v-for="item in items"
                                    :key="item.title"
                                    @click=""
                            >
                                <v-list-tile-action>
                                    <v-icon>{{ item.icon }}</v-icon>
                                </v-list-tile-action>

                                <v-list-tile-content>
                                    <v-list-tile-title>{{ item.title }}</v-list-tile-title>
                                </v-list-tile-content>
                            </v-list-tile>
                        </v-list>
                    </v-navigation-drawer>
                </v-card>
                </div>

            </v-flex>
            <v-flex xs12>
                <!-- Study content -->

                <v-layout row wrap>
                    <v-flex xs12>
                        <!-- General Overview -->
                        <v-card v-if="generalVisible">
                            <heading-toolbar :title="'Study: '+study.name" :icon="icon('study')" :resource_url="resource_url"/>
                            <study-info :study="study"/>
                            <!-- <Annotations :item="study"/>-->
                        </v-card>
                    </v-flex>


                    <v-flex xs12>
                        <!-- Groups -->
                        <GetData v-if="study.groupset" :resource_url="study.groupset">
                            <template slot-scope="groupset">
                                <div v-if="groupset.loaded">
                                    <!--
                                    <Annotations :item="groupset.data"/>
                                    -->
                                    <GroupsTable v-if="groupsVisible" :data="resource(groupset.data.groups)"/>
                                </div>
                            </template>
                        </GetData>
                    </v-flex>

                    <v-flex xs12>
                        <!-- Individuals -->
                        <GetData v-if="study.individualset" :resource_url="study.individualset">
                            <template slot-scope="individualset">
                                <div v-if="individualset.loaded">
                                    <!--
                                    <Annotations :item="individualset.data"/>
                                    -->
                                    <IndividualsTable v-if="individualsVisible"
                                                      :data="resource(individualset.data.individuals)"/>
                                </div>
                            </template>
                        </GetData>
                    </v-flex>

                    <v-flex xs12>
                        <!-- Interventions -->
                        <GetData v-if="study.interventionset" :resource_url="study.interventionset">
                            <template slot-scope="interventionset">
                                <div v-if="interventionset.loaded">
                                    <InterventionsTable v-if="interventionsVisible"
                                                        :data="resource(interventionset.data.interventions)"/>
                                </div>
                            </template>
                        </GetData>
                    </v-flex>

                    <v-flex xs12>
                        <!-- Outputs -->
                        <GetData v-if="study.outputset" :resource_url="study.outputset">
                            <template slot-scope="outputset">
                                <div v-if="outputset.loaded">
                                    <!--
                                    {{ checkhasOutputs(outputset.outputs) }}
                                    {{ checkhasTimecourses(outputset.timecourses) }}
                                    -->

                                    <OutputsTable v-if="outputsVisible" :data="resource(outputset.data.outputs)"/>
                                    <br />
                                    <TimecoursesTable v-if="timecoursesVisible" :data="resource(outputset.data.timecourses)"/>
                                </div>
                            </template>
                        </GetData>
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
                menuVisible: false,

                generalVisible: true,
                groupsVisible: true,
                individualsVisible: true,
                interventionsVisible: true,
                outputsVisible: true,
                timecoursesVisible: true,

                hasOutputs: false,
                hasTimecourses: false,
                hasInterventions: false,
                hasIndividuals: false,
                hasGroups: false,
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
            toggleMenu () {
                this.menuVisible = !this.menuVisible
            },
            toggleGeneral () {
                this.GeneralVisible = !this.GeneralVisible
            },
            toggleIndividuals () {
                this.IndividualsVisible = !this.IndividualsVisible
            },
            toggleGroups () {
                this.GroupsVisible = !this.GroupsVisible
            },
            toggleInterventions () {
                this.InterventionsVisible = !this.InterventionsVisible
            },
            toggleOutputs () {
                this.OutputsVisible = !this.OutputsVisible
            },
            toggleTimecourses () {

                this.TimecoursesVisible = !this.TimecoursesVisible
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
        fixed: true;
    }
</style>