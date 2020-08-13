<template>
    <v-app-bar id="navigation"
               class="fixed-nav-bar"
               clipped
               app
               permanent
               flat
               dense
               color="#000000"
    >

        <v-btn icon to="/" title="Home" color="white"><v-icon>{{ faIcon('home') }}</v-icon></v-btn>
        <v-btn icon to="/studies" title="Studies" color="white"><v-icon>{{ faIcon('studies') }}</v-icon></v-btn>
        <v-btn icon to="/search" title="Search" color="white"><v-icon>{{ faIcon('search') }}</v-icon></v-btn>

      <!--
      <v-btn icon to="/references" title="References" color="white"><v-icon>{{ faIcon('references') }}</v-icon></v-btn>
      <v-btn icon to="/groups" title="Groups" color="white"><v-icon>{{ faIcon('groups') }}</v-icon></v-btn>
      <v-btn icon to="/individuals" title="Individuals" color="white"><v-icon>{{ faIcon('individuals') }}</v-icon></v-btn>
      <v-btn icon to="/interventions" title="Interventions" color="white"><v-icon>{{ faIcon('interventions') }}</v-icon></v-btn>
      <v-btn icon to="/outputs" title="Outputs" color="white"><v-icon>{{ faIcon('outputs') }}</v-icon></v-btn>
      <v-btn icon to="/timecourses" title="Timecourses" color="white"><v-icon>{{ faIcon('timecourses') }}</v-icon></v-btn>
      -->
        <v-spacer></v-spacer>

        <!-- account -->
        <v-chip v-if="username" flat title="Logout" @click.stop="dialog=true">
            <user-avatar :username="username"></user-avatar>
            {{ username }}
        </v-chip>
        <v-btn icon v-if="username==null" title="Login" @click.stop="dialog=true">
            <v-icon color="white">{{ faIcon('account') }}</v-icon>
        </v-btn>
        <v-dialog v-model="dialog" max-width="500">
            <user-login></user-login>
        </v-dialog>

        <!-- links -->
        <v-btn icon to="/curation" title="Curation information" color="white"><v-icon>{{ faIcon('curation') }}</v-icon></v-btn>
        <v-btn icon :href="api_url" title="REST API" color="white"><v-icon>{{ faIcon('api') }}</v-icon></v-btn>
        <v-btn icon href="https://www.github.com/matthiaskoenig/pkdb" title="GitHub code repository" color="white">
            <v-icon>{{ faIcon('github')}}</v-icon>
        </v-btn>
    </v-app-bar>
</template>

<script>
    import {lookupIcon} from "@/icons"
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
            faIcon: function (key) {
                return lookupIcon(key)
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
    }
</style>