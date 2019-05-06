<template>
    <v-toolbar id="navigation" class="fixed-nav-bar" flat dense>
        <!--
        <v-toolbar-side-icon></v-toolbar-side-icon>
        <v-toolbar-title class="white--text">PK-DB</v-toolbar-title>
        -->
        <v-btn icon to="/" title="Home">
            <v-icon>{{ icon('home') }}</v-icon>
        </v-btn>
        <!--<v-spacer></v-spacer>-->

        <v-btn icon to="/studies" title="Studies"><v-icon>{{ icon('studies') }}</v-icon></v-btn>
        <v-btn icon to="/groups" title="Groups"><v-icon>{{ icon('groups') }}</v-icon></v-btn>
        <v-btn icon to="/individuals" title="Individuals"><v-icon>{{ icon('individuals') }}</v-icon></v-btn>
        <v-btn icon to="/interventions" title="Interventions"><v-icon>{{ icon('interventions') }}</v-icon></v-btn>
        <v-btn icon to="/outputs" title="Outputs"><v-icon>{{ icon('outputs') }}</v-icon></v-btn>
        <v-btn icon to="/timecourses" title="Timecourses"><v-icon>{{ icon('timecourses') }}</v-icon></v-btn>
        <v-btn icon to="/references" title="References"><v-icon>{{ icon('references') }}</v-icon></v-btn>

        <v-spacer></v-spacer>

        <v-btn icon to="/account" title="User account settings">
            <v-icon>{{ icon('account') }}</v-icon>
        </v-btn>
        <v-btn icon to="/curation" title="Curation information"><v-icon>{{ icon('curation') }}</v-icon></v-btn>
        <v-btn icon :href="api_url" title="REST API"><v-icon>{{ icon('api') }}</v-icon></v-btn>
        <!--
        <v-btn icon to="/about" title="About PK-DB"><v-icon>{{ icon('about') }}</v-icon></v-btn>
        -->
        <v-btn icon :href="admin_url" title="Django admin interface">
            <v-icon>{{ icon('admin') }}</v-icon>
        </v-btn>
        <v-btn icon href="https://www.github.com/matthiaskoenig/pkdb" title="GitHub code repository">
            <v-icon>{{ icon('github')}}</v-icon>
        </v-btn>
    </v-toolbar>
</template>

<script>
    import {lookup_icon} from "@/icons"
    export default {
        name: 'Navigation',
        data(){
            return {}
        },
        components: {

        },
        computed: {
            // vuex store
            admin_url() {
                return this.$store.state.django_domain + '/admin/';
            },
            api_url() {

                return this.$store.state.endpoints.api;
            },
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