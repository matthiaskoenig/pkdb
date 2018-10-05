<template>
    <div id="study-detail">
    <v-card>
        <Heading :title="'Study: '+study.pk" :icon="icon('study')" :resource_url="resource_url"/>
    </v-card>

    <!-- General Overview -->
    <span v-if="GeneralVisible">
        <StudyInfo :study="study"/>
    </span>

    <!-- Groups -->
    <GetData v-if="study.data.groupset" :resource_url="study.data.groupset">
        <template slot-scope="groupset" >
            <div v-if="groupset.loaded">

                <Descriptions :descriptions="groupset.data.descriptions"/>
                <Comments :comments="groupset.data.comments"/>

                {{ checkhasGroups(groupset.data.groups) }}
                <GroupsTable v-if="GroupsVisible" :groups="resource(groupset.data.groups)" />
            </div>
        </template>
    </GetData>

    <!-- Individuals -->
    <GetData v-if="study.data.individualset" :resource_url="study.data.individualset">
        <template slot-scope="individualset" >
            <div v-if="individualset.loaded">

                <Descriptions :descriptions="individualset.data.descriptions"/>
                <Comments :comments="individualset.data.comments"/>
                {{ checkhasIndividuals(individualset.data.individuals) }}
                <IndividualsTable  v-if="IndividualsVisible" :individuals="resource(individualset.data.individuals)"/>
            </div>
        </template>
    </GetData>

    <!-- Interventions -->
    <GetData v-if="study.data.interventionset" :resource_url="study.data.interventionset">
        <template slot-scope="interventionset" >
            <div v-if="interventionset.loaded">
                {{ checkhasInterventions(interventionset.data.interventions) }}
                <Descriptions :descriptions="interventionset.data.descriptions"/>
                <Comments :comments="interventionset.data.comments"/>
                <InterventionsTable v-if="InterventionsVisible" :interventions="resource(interventionset.data.interventions)"/>
            </div>
        </template>
    </GetData>

    <!-- Outputs -->
    <GetData v-if="study.data.outputset" :resource_url="study.data.outputset">
        <template slot-scope="outputset">
            <div v-if="outputset.loaded">
                {{ checkhasOutputs(outputset.data.outputs) }}
                {{ checkhasTimecourses(outputset.data.timecourses) }}
                <Descriptions :descriptions="outputset.data.descriptions"/>
                <Comments :comments="outputset.data.comments"/>
                <OutputsTable v-if="OutputsVisible" :outputs="resource(outputset.data.outputs)"/>
                <TimecoursesTable v-if="TimecoursesVisible" :timecourses="resource(outputset.data.timecourses)"/>
            </div>
        </template>
    </GetData>

    </div>
</template>

<script>
    import {isEmpty} from "@/utils"
    import {lookup_icon} from "@/icons"

    import GroupsTable from "@/components/tables/GroupsTable";
    import IndividualsTable from '@/components/tables/IndividualsTable';
    import InterventionsTable from "@/components/tables/InterventionsTable";
    import OutputsTable from "@/components/tables/OutputsTable";
    import TimecoursesTable from "@/components/tables/TimecoursesTable";

    export default {
        name: "StudyDetail",
        components: {
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
                IndividualsVisible: false,
                GroupsVisible: false,
                InterventionsVisible: false,
                OutputsVisible: false,
                TimecoursesVisible: false,
                GeneralVisible: true,

                hasOutputs:false,
                hasTimecourses:false,
                hasInterventions:false,
                hasIndividuals:false,
                hasGroups:false,
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
            checkhasOutputs (array ) {
                if (array.length !== 0){
                    this.hasOutputs = true
                }
            },
            checkhasTimecourses (array) {
                if (array.length !== 0){
                    this.hasTimecourses = true
                }
            },
            checkhasInterventions (array) {
                if (array.length !== 0){
                    this.hasInterventions = true
                }
            },
            checkhasIndividuals (array) {
                if (array.length !== 0){
                    this.hasIndividuals = true
                }
            },
            checkhasGroups (array) {
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
</style>