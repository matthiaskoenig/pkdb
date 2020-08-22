<template>
    <v-app-bar id="navigation"
               class="fixed-nav-bar"
               app
               permanent
               flat
               dark
               dense
               color="#222222"
    >
      <v-app-bar-nav-icon></v-app-bar-nav-icon>
      <v-toolbar-title color="white">PK-DB</v-toolbar-title>
      <v-spacer></v-spacer>

      <v-btn icon to="/" title="Home" color="white"><v-icon>{{ faIcon('home') }}</v-icon></v-btn>

      <v-btn icon to="/studies" title="Data" color="#1E90FF"><v-icon>{{ faIcon('data') }}</v-icon></v-btn>
      <v-btn icon to="/search" title="Search" color="#41b883"><v-icon>{{ faIcon('search') }}</v-icon></v-btn>

      <v-btn icon to="/curation" title="Curation information" color="grey"><v-icon>{{ faIcon('curation') }}</v-icon></v-btn>

      <v-btn icon :href="api_url" title="REST API" color="grey"><v-icon>{{ faIcon('api') }}</v-icon></v-btn>
      <!-- account -->
        <v-chip v-if="username" flat title="Logout" @click.stop="dialog=true" color="grey">
            <user-avatar :username="username"></user-avatar>
            {{ username }}
        </v-chip>
        <v-btn icon v-if="username==null" title="Login" @click.stop="dialog=true" color="grey">
            <v-icon >{{ faIcon('account') }}</v-icon>
        </v-btn>

        <v-dialog v-model="dialog" max-width="500">
            <user-login></user-login>
        </v-dialog>



      <!--
        <v-btn icon href="https://www.github.com/matthiaskoenig/pkdb" title="GitHub code repository" color="white">
            <v-icon small>{{ faIcon('github')}}</v-icon>
        </v-btn>
        -->
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