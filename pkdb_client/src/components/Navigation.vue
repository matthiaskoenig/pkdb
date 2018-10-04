<template>
    <div>
        <md-tabs class="md-layout">
                <md-tab id="tab-home" md-label="Home" :md-icon="icon('home')" to="/"> </md-tab>
                <md-tab id="tab-studies" md-label="Studies" :md-icon="icon('studies')" to="/studies"></md-tab>
                <md-tab id="tab-groups" md-label="Groups" :md-icon="icon('groups')" to="/groups"></md-tab>
                <md-tab id="tab-individuals" md-label="Individuals" :md-icon="icon('individuals')" to="/individuals"></md-tab>
                <md-tab id="tab-interventions" md-label="Interventions" :md-icon="icon('interventions')" to="/interventions"></md-tab>
                <md-tab id="tab-outputs" md-label="Outputs" :md-icon="icon('outputs')" to="/outputs"></md-tab>
                <md-tab id="tab-timecourses" md-label="Timecourses" :md-icon="icon('timecourses')" to="/timecourses"></md-tab>
                <md-tab id="tab-references" md-label="References" :md-icon="icon('references')" to="/references"></md-tab>

                <!-- TODO: right aligned -->
                <md-tab to="/about" md-active-tab="false"  id="tab-about" :md-icon="icon('about')" md-label="About"></md-tab>
                <md-tab id="tab-api" md-label="API" :md-icon="icon('api')" :href="api_url"></md-tab>
                <md-tab id="tab-github" md-label="Code" :md-icon="icon('github')" href="https://www.github.com/matthiaskoenig/pkdb"></md-tab>

                <md-tab id="tab-admin" md-label="Admin" :md-icon="icon('admin')" :href="admin_url"></md-tab>
                <md-tab id="tab-accounts" md-label="Account" :md-icon="icon('account')" to="/account"></md-tab>
        </md-tabs>

    </div>

</template>

<script>
    import {lookup_md_icon} from "@/icons"

    export default {
        name: 'Navigation',
        data(){
            return {}
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
                return lookup_md_icon(key)
            }
        }
    }
</script>

<style>

</style>