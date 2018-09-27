<template>
    <div class="page-container">
        <GetData :api_url="resource_url">
            <template slot-scope="study">
                {{study.loaded}}
                <md-app v-if="study.loaded">
                    <md-app-toolbar class="md-primary" md-elevation="0">
                        <md-button class="md-icon-button" @click="toggleMenu" v-if="!menuVisible">
                            <md-icon>menu</md-icon>
                        </md-button>
                        <span class="md-title">{{study.name}}</span>
                    </md-app-toolbar>

                    <md-app-drawer :md-active.sync="menuVisible" md-persistent="mini">

                        <md-toolbar class="md-transparent" md-elevation="0">
                            <span>Navigation</span>

                            <div class="md-toolbar-section-end">
                                <md-button class="md-icon-button md-dense" @click="toggleMenu">
                                    <md-icon>keyboard_arrow_left</md-icon>
                                </md-button>
                            </div>
                        </md-toolbar>

                        <md-list>
                            <md-list-item>
                                <font-awesome-icon class="md-icon" icon="users" />
                                <span class="md-list-item-text">Groups</span>
                            </md-list-item>

                            <md-list-item>
                                <font-awesome-icon class="md-icon"  icon="user" />
                                <span class="md-list-item-text">Individuals</span>
                            </md-list-item>

                            <md-list-item>
                                <font-awesome-icon class="md-icon" icon="capsules"/>
                                <span class="md-list-item-text">Interventions</span>
                            </md-list-item>

                            <md-list-item>
                                <font-awesome-icon class="md-icon" icon="chart-bar" />
                                <span class="md-list-item-text">Outputs</span>
                            </md-list-item>

                            <md-list-item>
                                <font-awesome-icon class="md-icon" icon="chart-line" />
                                <span class="md-list-item-text">Timecourses</span>
                            </md-list-item>
                        </md-list>
                    </md-app-drawer>

                    <md-app-content>
                        <GetData :api_url="study.data.individualset">

                            <template slot-scope="individualset" >
                                {{individualset.loaded}}
                                <div v-if="individualset.loaded">
                                    <IndividualsTable :resource="resource(individualset.data.individuals)" :api="api" />
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
    import IndividualsTable from './IndividualsTable';
    import GetData from "./GetData";

    export default {
        name: "StudyDetail",
        components: {
            IndividualsTable: IndividualsTable,
            GetData:GetData,
        },
        props: {
            api: String,
            id: String,
        },

        data() {
            return {
                resource_url: this.api + '/studies_read/' + this.id + '/?format=json',
                menuVisible: false,
            }
        },
        // Fetches posts when the component is created.
        methods:{
            toggleMenu () {
                this.menuVisible = !this.menuVisible
            },
            resource(data){
                return {entries:data, count:data.length}
            }

        }


    }
</script>

<style scoped>

    .md-app {
        min-height: 350px;
    }


</style>