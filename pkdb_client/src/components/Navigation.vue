<template>
    <div id="navigation">

        <md-tabs class="md-layout">
                <md-tab id="tab-home" md-label="Home" :md-icon="md_icon('home')" to="/"> </md-tab>
                <md-tab id="tab-studies" md-label="Studies" :md-icon="md_icon('studies')" to="/studies"></md-tab>
                <md-tab id="tab-groups" md-label="Groups" :md-icon="md_icon('groups')" to="/groups"></md-tab>
                <md-tab id="tab-individuals" md-label="Individuals" :md-icon="md_icon('individuals')" to="/individuals"></md-tab>
                <md-tab id="tab-interventions" md-label="Interventions" :md-icon="md_icon('interventions')" to="/interventions"></md-tab>
                <md-tab id="tab-outputs" md-label="Outputs" :md-icon="md_icon('outputs')" to="/outputs"></md-tab>
                <md-tab id="tab-timecourses" md-label="Timecourses" :md-icon="md_icon('timecourses')" to="/timecourses"></md-tab>
                <md-tab id="tab-references" md-label="References" :md-icon="md_icon('references')" to="/references"></md-tab>

                <!-- TODO: right aligned -->
                <md-tab to="/about" md-active-tab="false"  id="tab-about" :md-icon="md_icon('about')" md-label="About"></md-tab>
                <md-tab id="tab-api" md-label="API" :md-icon="md_icon('api')" :href="api_url"></md-tab>
                <md-tab id="tab-github" md-label="Code" :md-icon="md_icon('github')" href="https://www.github.com/matthiaskoenig/pkdb"></md-tab>

                <md-tab id="tab-admin" md-label="Admin" :md-icon="md_icon('admin')" :href="admin_url"></md-tab>
                <md-tab id="tab-accounts" md-label="Account" :md-icon="md_icon('account')" to="/account"></md-tab>
        </md-tabs>
    </div>

</template>

<script>
    import {lookup_md_icon, lookup_icon} from "@/icons"
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
            md_icon: function (key) {
                return lookup_md_icon(key)
            },
            icon: function (key) {
                return lookup_icon(key)
            },
        }
    }
</script>

<style>
    #navigation {
        font-family: 'Avenir', Helvetica, Arial, sans-serif;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
        background-color: #ffffff;

        margin-bottom: 5px;
    }
</style>