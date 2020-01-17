<template>
    <v-toolbar id="navigation" class="fixed-nav-bar" flat dense>

        <v-btn icon="blue" to="/" title="Home"><v-icon color="black">{{ icon('home') }}</v-icon></v-btn>
        <v-btn icon to="/studies" title="Studies"><v-icon color="black">{{ icon('studies') }}</v-icon></v-btn>
        <v-btn icon to="/groups" title="Groups"><v-icon color="black">{{ icon('groups') }}</v-icon></v-btn>
        <v-btn icon to="/individuals" title="Individuals" color="black"><v-icon>{{ icon('individuals') }}</v-icon></v-btn>
        <v-btn icon to="/interventions" title="Interventions" color="black"><v-icon>{{ icon('interventions') }}</v-icon></v-btn>
        <v-btn icon to="/outputs" title="Outputs"><v-icon color="black">{{ icon('outputs') }}</v-icon></v-btn>
        <v-btn icon to="/timecourses" title="Timecourses"><v-icon color="black">{{ icon('timecourses') }}</v-icon></v-btn>
        <v-btn icon to="/references" title="References"><v-icon color="black">{{ icon('references') }}</v-icon></v-btn>

        <v-spacer></v-spacer>

        <!-- account -->
        <v-chip v-if="username" flat title="Logout" @click.stop="dialog=true">
            <user-avatar :username="username"></user-avatar>
            {{ username }}
        </v-chip>
        <v-btn icon v-if="username==null" title="Login" @click.stop="dialog=true">
            <v-icon color="black">{{ icon('account') }}</v-icon>
        </v-btn>
        <v-dialog v-model="dialog" max-width="500">
            <user-login></user-login>
        </v-dialog>

        <!-- links -->
        <v-btn icon to="/curation" title="Curation information"><v-icon color="black">{{ icon('curation') }}</v-icon></v-btn>
        <v-btn icon :href="api_url" title="REST API"><v-icon color="black">{{ icon('api') }}</v-icon></v-btn>
        <v-btn icon :href="admin_url" title="Django admin interface"><v-icon color="black">{{ icon('admin') }}</v-icon></v-btn>
        <v-btn icon href="https://www.github.com/matthiaskoenig/pkdb" title="GitHub code repository">
            <v-icon color="black">{{ icon('github')}}</v-icon>
        </v-btn>
    </v-toolbar>
</template>

<script>
    import {lookup_icon} from "@/icons"
    import  UserLogin from "./auth/UserLogin"

    export default {
        name: 'Navigation',
        components: {
            UserLogin,
        },
        data: () => ({
            dialog: false
        }),
        computed: {
            // vuex store
            admin_url() {
                return this.$store.state.django_domain + '/admin/';
            },
            api_url() {

                return this.$store.state.endpoints.api;
            },
            username(){
                return this.$store.state.username
            }
        },
        methods: {
            icon: function (key) {
                return lookup_icon(key)
            },
        }
    }
</script>

<style scoped>
    .fixed-nav-bar {
        position: fixed;
        top: 0;
        left: 0;
        z-index: 9999;
        width: 100%;
        height: 50px;
        background-color: #00a087;
    }
</style>