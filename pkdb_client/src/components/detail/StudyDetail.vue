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


            <v-flex class="study-content" xs10 offset-xs2>
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
                        <annotations :item="study.groupset"/>
                        <groups-table3 :ids="study.groupset.groups"/>
                    </v-flex>

                    <!-- Individuals -->
                    <v-flex xs12 v-show="visible.individuals">
                        <annotations :item="study.individualset"/>
                        <individuals-table3 :ids="study.individualset.individuals"/>
                    </v-flex>

                    <!-- Interventions -->
                    <v-flex xs12 v-show="visible.interventions">
                        <annotations :item="study.interventionset"/>
                        <interventions-table3 :ids="study.interventionset.interventions"/>
                    </v-flex>

                    <!-- Outputs -->
                    <v-flex xs12 v-show="visible.outputs || visible.timecourses">
                        <annotations :item="study.outputset"/>
                        <outputs-table3 v-show="visible.outputs" :ids="study.outputset.outputs"/>
                        <br />
                        <timecourses-table3 v-show="visible.timecourses" :ids="study.outputset.timecourses"/>

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
    import IndividualsTable3 from '../tables/IndividualsTable3';
    import InterventionsTable3 from "../tables/InterventionsTable3";
    import OutputsTable3 from "../tables/OutputsTable3";
    import TimecoursesTable3 from "../tables/TimecoursesTable3";
    import {UrlMixin} from "../tables/mixins";
    import GroupsTable3 from "../tables/GroupsTable3";


    export default {
        name: "StudyDetail",
        components: {
            StudyInfo: StudyInfo,
            GroupsTable3: GroupsTable3,
            IndividualsTable3: IndividualsTable3,
            InterventionsTable3: InterventionsTable3,
            OutputsTable3: OutputsTable3,
            TimecoursesTable3: TimecoursesTable3,

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
                    groups: this.study.groupset.count,
                    individuals: this.study.individualset.count,
                    interventions: this.study.interventionset.count,
                    outputs: this.study.outputset.count_outputs,
                    timecourses: this.study.outputset.count_timecourses
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