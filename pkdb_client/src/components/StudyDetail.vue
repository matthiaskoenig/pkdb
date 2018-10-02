<template>
    <div class="page-container">
        <GetData :api_url="resource_url">
            <template slot-scope="study">
                <md-app v-if="study.loaded">

                    <md-app-toolbar class="md-primary" md-elevation="0">
                        <md-button class="md-icon-button" @click="toggleMenu" v-if="!menuVisible">
                            <md-icon>menu</md-icon>
                        </md-button>
                        <span class="md-title">{{study.data.name}}</span>
                    </md-app-toolbar>

                    <md-app-drawer :md-active.sync="menuVisible" md-persistent="mini">

                        <md-toolbar class="md-transparent" md-elevation="0">
                            <span>Navigation</span>

                            <div class="md-toolbar-section-end">
                                <md-button class="md-icon-button" @click="toggleMenu" >
                                    <md-icon>keyboard_arrow_left</md-icon>
                                </md-button>
                            </div>
                        </md-toolbar>

                        <md-list>
                            <md-list-item>
                                <md-button  :class="'md-icon-button md-fixed' + isActive(GeneralVisible)" @click="toggleGeneral">
                                    <font-awesome-icon  icon="procedures" />
                                </md-button>

                                <span class="md-list-item-text">General</span>
                            </md-list-item>

                            <md-list-item>
                                     <md-button  :class="'md-icon-button md-fixed' + isActive(GroupsVisible)" @click="toggleGroups" :disabled="!hasGroups" >
                                    <font-awesome-icon icon="users" />
                                </md-button>


                                <span class="md-list-item-text">Groups</span>
                            </md-list-item>

                            <md-list-item>
                                <md-button  :class="'md-icon-button md-fixed' + isActive(IndividualsVisible)" @click="toggleIndividuals" :disabled="!hasIndividuals" >
                                    <font-awesome-icon icon="user" />
                                </md-button>
                                <span class="md-list-item-text">Individuals</span>
                            </md-list-item>

                            <md-list-item>
                                <md-button  :class="'md-icon-button md-fixed' + isActive(InterventionsVisible)" @click="toggleInterventions" :disabled="!hasInterventions" >
                                    <font-awesome-icon icon="capsules" />
                                </md-button>
                                <span class="md-list-item-text">Interventions</span>
                            </md-list-item>

                            <md-list-item>
                                <md-button  :class="'md-icon-button md-fixed' + isActive(OutputsVisible)" @click="toggleOutputs" :disabled="!hasOutputs" >
                                    <font-awesome-icon icon="chart-bar" />
                                </md-button>
                                <span class="md-list-item-text">Outputs</span>
                            </md-list-item>

                            <md-list-item>
                                <md-button  :class="'md-icon-button md-fixed' + isActive(TimecoursesVisible)" @click="toggleTimecourses" :disabled="!hasTimecourses">
                                    <font-awesome-icon icon="chart-line" />
                                </md-button>
                                <span class="md-list-item-text">Timecourses</span>
                            </md-list-item>
                        </md-list>
                    </md-app-drawer>

                    <md-app-content>

                        <template v-if="GeneralVisible">
                            {{study.sid}}

                        </template>

                        <GetData v-if="study.data.groupset" :api_url="study.data.groupset">
                            <template slot-scope="groupset" >
                                <div v-if="groupset.loaded">
                                    {{checkhasGroups(groupset.data.groups)}}
                                    <GroupsTable v-if="GroupsVisible" :resource="resource(groupset.data.groups)" :api="api" :descriptions="groupset.data.descriptions" :comments="groupset.data.comments"/>
                                </div>
                            </template>
                        </GetData>

                        <GetData v-if="study.data.individualset" :api_url="study.data.individualset">
                            <template slot-scope="individualset" >
                                <div v-if="individualset.loaded">
                                    {{checkhasIndividuals(individualset.data.individuals)}}

                                    <IndividualsTable  v-if="IndividualsVisible"  :resource="resource(individualset.data.individuals)" :api="api"  :descriptions="individualset.data.descriptions" :comments="individualset.data.comments"/>
                                </div>
                            </template>
                        </GetData>

                        <GetData v-if="study.data.interventionset" :api_url="study.data.interventionset">
                            <template slot-scope="interventionset" >
                                <div v-if="interventionset.loaded">
                                    {{checkhasInterventions(interventionset.data.interventions)}}
                                    <InterventionsTable v-if="InterventionsVisible" :resource="resource(interventionset.data.interventions)" :api="api"  :descriptions="interventionset.data.descriptions" :comments="interventionset.data.comments"/>
                                </div>
                            </template>
                        </GetData>

                        <GetData v-if="study.data.outputset" :api_url="study.data.outputset">
                            <template slot-scope="outputset">
                                <div v-if="outputset.loaded">

                                    {{checkhasOutputs(outputset.data.outputs)}}
                                    {{checkhasTimecourses(outputset.data.timecourses)}}

                                    <OutputsTable v-if="OutputsVisible" :resource="resource(outputset.data.outputs)" :api="api"  :descriptions="outputset.data.descriptions" :comments="outputset.data.comments"/>
                                    <TimecoursesTable v-if="TimecoursesVisible" :resource="resource(outputset.data.timecourses)" :api="api"  :descriptions="outputset.data.descriptions" :comments="outputset.data.comments"/>

                                </div>
                            </template>
                        </GetData>




                    </md-app-content>
                </md-app>

            </template>

        </GetData>

    </div>
</template>

<script>
    import GroupsTable from "./GroupsTable";
    import IndividualsTable from './IndividualsTable';
    import InterventionsTable from "./InterventionsTable";
    import OutputsTable from "./OutputsTable";
    import TimecoursesTable from "./TimecoursesTable";


    import GetData from "./GetData";
    import {isEmpty} from "./utils"

    export default {
        name: "StudyDetail",
        components: {
            GroupsTable:GroupsTable,
            IndividualsTable: IndividualsTable,
            GetData: GetData,
            InterventionsTable: InterventionsTable,
            OutputsTable: OutputsTable,
            TimecoursesTable: TimecoursesTable,

        },
        props: {
            api: String,
            id: String,
        },

        data() {
            return {
                resource_url: this.api + '/studies_read/' + this.id + '/?format=json',
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
        // Fetches posts when the component is created.
        methods:{
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

    .md-app {
        min-height: 350px;
    }
    .menu-botton{

    }



</style>