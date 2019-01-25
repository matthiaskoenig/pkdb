<template>
    <div id="study-detail">
        <v-layout wrap>
            <!-- Side menu for navigation. -->
            <v-flex xs4 md2 class="study-navigation">
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
                                    <v-list-tile-title v-if="item.id == 'general'">{{ item.title }}</v-list-tile-title>
                                    <v-list-tile-title v-else>
                                        {{ item.title }} ({{counts[item.id]}})
                                    </v-list-tile-title>
                                </v-list-tile-content>

                            </v-list-tile>
                        </v-list>
                    </v-navigation-drawer>
                </v-card>
            </v-flex>


            <v-flex class="study-content" xs8 offset-xs4 md10 offset-md2>
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
                        <annotations  v-if="study.groupset" :item="study.groupset"/>
                        <groups-table v-if="counts['groups']>0" :ids="study.groupset.groups" :autofocus="false"/>
                    </v-flex>

                    <!-- Individuals -->
                    <v-flex xs12 v-show="visible.individuals">
                        <annotations   v-if="study.individualset" :item="study.individualset"/>
                        <individuals-table v-if="counts['individuals']>0" :ids="study.individualset.individuals" :autofocus="false"/>
                    </v-flex>

                    <!-- Interventions -->
                    <v-flex xs12 v-show="visible.interventions">
                        <annotations v-if="study.interventionset" :item="study.interventionset"/>
                        <interventions-table v-if="counts['interventions']>0" :ids="study.interventionset.interventions" :autofocus="false"/>
                    </v-flex>

                    <!-- Outputs -->
                    <v-flex xs12 v-show="visible.outputs || visible.timecourses">
                        <annotations  v-if="study.outputset" :item="study.outputset"/>
                        <outputs-table v-if="counts['outputs']>0" v-show="visible.outputs" :ids="study.outputset.outputs" :autofocus="false"/>
                        <br />
                        <timecourses-table  v-if="counts['timecourses']>0" v-show="visible.timecourses" :ids="study.outputset.timecourses" :autofocus="false"/>

                    </v-flex>
                </v-layout>


            </v-flex>
        </v-layout>
    </div>
</template>

<script>
    import {isEmpty} from "@/utils"
    import {lookup_icon} from "@/icons"

    import {UrlMixin} from "../tables/mixins";
    import StudyInfo from "./StudyInfo";
    import IndividualsTable from '../tables/IndividualsTable';
    import InterventionsTable from "../tables/InterventionsTable";
    import OutputsTable from "../tables/OutputsTable";
    import TimecoursesTable from "../tables/TimecoursesTable";
    import GroupsTable from "../tables/GroupsTable";


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
        mixins :[UrlMixin],
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
                    timecourses: true,
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
            counts() {
                return {
                    general: 1,
                    groups: this.study.group_count,
                    individuals: this.study.individual_count,
                    interventions: this.study.intervention_count,
                    outputs: this.study.output_count,
                    timecourses: this.study.timecourse_count,

                }

            }

        },
        methods:{
            icon: function (key) {
                return lookup_icon(key)
            },

            toggleVisibility(item_id){
                // only items with counts can be made visible
                if (this.counts[item_id]>0){
                    this.visible[item_id] = !this.visible[item_id];
                }
            },

            resetVisibility(){
                var keys = Object.keys(this.counts);
                for (var k=0; k<keys.length; k++){
                    var key = keys[k];
                    if (this.counts[key] > 0){
                        this.visible[key] = true
                    } else {
                        this.visible[key] = false
                    }
                }
            },
            resource(data){
                return {entries:data, count:data.length}
            },
        },
        created: function() {
            this.resetVisibility();
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