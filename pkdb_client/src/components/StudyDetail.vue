<template>
    <div class="page-container">
        <md-app>
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
                Lorem ipsum dolor sit amet, consectetur adipisicing elit. Error quibusdam, non molestias et! Earum magnam, similique, quo recusandae placeat dicta asperiores modi sint ea repudiandae maxime? Quae non explicabo, neque.
            </md-app-content>
        </md-app>
    </div>
</template>

<script>
    import axios from 'axios'
    import {id_from_url} from "./utils";

    export default {
        name: "StudyDetail",
        props: {
            api: String,
            id: String,
        },

        data() {
            return {
                study: {},
                resource_url: this.api + '/studies_read/' + this.id + '/?format=json',
                menuVisible: false,
            }
        },
        // Fetches posts when the component is created.
        created() {
            axios.get(this.resource_url)
                .then(response => {
                    // JSON responses are automatically parsed.
                    this.study = response.data
                })
                .catch(e => {
                    this.errors.push(e)
                })

        },
        methods:{
            id_from_url(url){
                return id_from_url(url);
            },
            toggleMenu () {
                this.menuVisible = !this.menuVisible
            }
        }

    }
</script>

<style scoped>

    .md-app {
        min-height: 350px;
        border: 1px solid rgba(#000, .12);
    }


</style>