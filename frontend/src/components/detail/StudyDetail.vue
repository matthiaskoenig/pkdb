<template>
    <div id="study-detail">
        <div class="fixed-nav-bar2">

            <Heading :title="study.sid + ' (' + study.name + ')'" :icon="icon('study')" :resource_url="resource_url"/>
            <a href="#general">
                <v-chip color="w" disable=false>
                    <v-icon small title="General study information">{{icon("about")}}</v-icon>
                </v-chip>
            </a>
            <a href="#groups_anchor">
                <count-chip :count=study.group_count icon="group"></count-chip>
            </a>
            <a href="#individuals_anchor">
                <count-chip :count=study.individual_count icon="individual"></count-chip>
            </a>
            <a href="#interventions_anchor">
                <count-chip :count=study.intervention_count icon="intervention"></count-chip>
            </a>
            <a href="#outputs_anchor">
                <count-chip :count=study.output_count icon="output"></count-chip>
            </a>
            <a href="#timecourses_anchor">
                <count-chip :count=study.timecourse_count icon="timecourse"></count-chip>
            </a>

        </div>
        <div>
            <v-layout row wrap>

                <!-- previous & next study
                <v-btn color="white" icon :to="'/studies/' + previous_study" title="previous Study"><v-icon>{{ icon('previous') }}</v-icon></v-btn>
                <v-btn color="white" icon :to="'/studies/'+ next_study" title="next Study"><v-icon>{{ icon('next') }}</v-icon></v-btn>
                -->


                <!-- General Overview -->
                <v-flex id="general" xs12 v-show="visible.general">
                    <v-card>
                    <study-info :study="study"/>
                </v-card>
                </v-flex>

                <!-- Groups -->
                <a class="anchor" id="groups_anchor"></a>
                <v-flex xs12 v-show="visible.groups">
                    <annotations  v-if="study.groupset" :item="study.groupset"/>
                    <groups-table v-if="counts['groups']>0" :ids="study.groupset.groups" :autofocus="false"/>
                </v-flex>

                <!-- Individuals -->
                <a class="anchor" id="individuals_anchor"></a>
                <v-flex xs12 v-show="visible.individuals">
                    <annotations   v-if="study.individualset" :item="study.individualset"/>
                    <individuals-table v-if="counts['individuals']>0" :ids="study.individualset.individuals" :autofocus="false"/>
                </v-flex>

                <!-- Interventions -->
                <a class="anchor" id="interventions_anchor"></a>
                <v-flex xs12 v-show="visible.interventions">
                    <annotations v-if="study.interventionset" :item="study.interventionset"/>
                    <interventions-table v-if="counts['interventions']>0" :ids="study.interventionset.interventions" :autofocus="false"/>
                </v-flex>

                <!-- Outputs -->

                <v-flex xs12 v-show="visible.outputs || visible.timecourses">
                    <annotations  v-if="study.outputset" :item="study.outputset"/>
                    <a class="anchor" id="outputs_anchor"></a>
                    <outputs-table v-if="counts['outputs']>0" v-show="visible.outputs" :ids="study.outputset.outputs" :autofocus="false"/>
                    <br />
                    <a class="anchor" id="timecourses_anchor"></a>
                    <timecourses-table  v-if="counts['timecourses']>0" v-show="visible.timecourses" :ids="study.outputset.timecourses" :autofocus="false"/>

                </v-flex>
            </v-layout>
        </div>
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
    import CountChip from "../detail/CountChip";


    export default {
        name: "StudyDetail",
        components: {
            StudyInfo: StudyInfo,
            GroupsTable: GroupsTable,
            IndividualsTable: IndividualsTable,
            InterventionsTable: InterventionsTable,
            OutputsTable: OutputsTable,
            TimecoursesTable: TimecoursesTable,
            CountChip: CountChip

        },
        mixins :[UrlMixin],
        props: {
            study_pks:{
                type:Array,
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
                    general: true,
                    groups: true,
                    individuals: true,
                    interventions: true,
                    outputs: true,
                    timecourses: true,
                }
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
                    study_pks: this.study_pks
                }

            },
            study_index(){
                return this.study_pks.indexOf(this.study.sid)
            },

            next_study(){
                var studies_number  = this.study_pks.length;
                if (studies_number - 1 > this.study_index + 1)
                {
                    return this.study_pks[this.study_index + 1]
                }
                else
                    {
                    return this.study_pks[0]
                    }
                },
            previous_study(){

                var studies_number  = this.study_pks.length;
                if (this.study_index - 1 > 0 )
                {
                    return this.study_pks[this.study_index - 1]
                }
                else
                    {
                    return this.study_pks[studies_number-1]
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
    .fixed-nav-bar2 {
        position: fixed;
        top: 50px;
        left: 0;
        z-index: 9999;
        width: 100%;
        height: 50px;
        background-color: #00a087;
    }
    a.anchor {
        //display: block;
        //position: relative;
        top: 0px;
        visibility: hidden;
    }
</style>