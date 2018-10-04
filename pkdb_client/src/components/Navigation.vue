<template>
    <div id="navigation">


        <b-navbar toggleable="md">

            <b-navbar-toggle target="nav_collapse"></b-navbar-toggle>

            <b-navbar-brand href="#">NavBar</b-navbar-brand>

            <b-collapse is-nav id="nav_collapse">

                <b-navbar-nav>
                    <b-nav-item href="#">Link</b-nav-item>
                    <b-nav-item href="#" disabled>Disabled</b-nav-item>
                </b-navbar-nav>

                <!-- Right aligned nav items -->
                <b-navbar-nav class="ml-auto">

                    <b-nav-form>
                        <b-form-input size="sm" class="mr-sm-2" type="text" placeholder="Search"/>
                        <b-button size="sm" class="my-2 my-sm-0" type="submit">Search</b-button>
                    </b-nav-form>

                    <b-nav-item-dropdown text="Lang" right>
                        <b-dropdown-item href="#">EN</b-dropdown-item>
                        <b-dropdown-item href="#">ES</b-dropdown-item>
                        <b-dropdown-item href="#">RU</b-dropdown-item>
                        <b-dropdown-item href="#">FA</b-dropdown-item>
                    </b-nav-item-dropdown>

                    <b-nav-item-dropdown right>
                        <!-- Using button-content slot -->
                        <template slot="button-content">
                            <em>User</em>
                        </template>
                        <b-dropdown-item href="#">Profile</b-dropdown-item>
                        <b-dropdown-item href="#">Signout</b-dropdown-item>
                    </b-nav-item-dropdown>
                </b-navbar-nav>

            </b-collapse>
        </b-navbar>

        <!-- navbar-1.vue -->




        <!-- Responsive Navigation Bar -->
        <!--
        <nav class="navbar navbar-expand-lg navbar-dark bg-dark fixed-top">
            <a class="navbar-brand" href="#">D</a>
            <button class="navbar-toggler" type="button" data-toggle="collapse" data-target="#navbarSupportedContent" aria-controls="navbarSupportedContent"
                    aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
            </button>



            <div class="collapse navbar-collapse" id="navbarSupportedContent">
                <ul class="navbar-nav mr-auto">
                    <li class="nav-item active">
                        <a class="nav-link" href="#">Home
                            <span class="sr-only">(current)</span>
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#">Blog</a>
                    </li>
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" id="navbarDropdown" role="button" data-toggle="dropdown" aria-haspopup="true"
                           aria-expanded="false">
                            Services
                        </a>
                        <div class="dropdown-menu" aria-labelledby="navbarDropdown">
                            <a class="dropdown-item" href="#">Action</a>
                            <a class="dropdown-item" href="#">Another action</a>
                            <div class="dropdown-divider"></div>
                            <a class="dropdown-item" href="#">Something else here</a>
                        </div>
                    </li>
                    <li class="nav-item">
                        <a href="#" class="nav-link">Contact Us</a>
                    </li>
                    <li class="nav-item">
                        <a href="#" class="nav-link">About Us</a>
                    </li>
                </ul>
                <form class="form-inline my-2 my-lg-0">
                    <input class="form-control mr-sm-2" type="search" placeholder="Search" aria-label="Search">
                    <button class="btn btn-danger my-2 my-sm-0" type="submit">Submit</button>
                </form>
            </div>
        </nav>
        -->
        <!-- Responsive Navigation Bar -->

        id label icon to
        <span class="badge-warning">
        <NavigationItem id="tab-home" label="Home" :md-icon="md_icon('home')" to="/" />
            Test
        </span>

        <md-tabs class="md-layout">
                <md-tab id="tab-home" md-label="Home" :md-icon=md_icon('home')" to="/"> </md-tab>
                <md-tab id="tab-studies" md-label="Studies" :md-icon=md_icon('studies')" to="/studies"></md-tab>
                <md-tab id="tab-groups" md-label="Groups" :md-icon=md_icon('groups')" to="/groups"></md-tab>
                <md-tab id="tab-individuals" md-label="Individuals" :md-icon=md_icon('individuals')" to="/individuals"></md-tab>
                <md-tab id="tab-interventions" md-label="Interventions" :md-icon=md_icon('interventions')" to="/interventions"></md-tab>
                <md-tab id="tab-outputs" md-label="Outputs" :md-icon=md_icon('outputs')" to="/outputs"></md-tab>
                <md-tab id="tab-timecourses" md-label="Timecourses" :md-icon=md_icon('timecourses')" to="/timecourses"></md-tab>
                <md-tab id="tab-references" md-label="References" :md-icon=md_icon('references')" to="/references"></md-tab>

                <!-- TODO: right aligned -->
                <md-tab to="/about" md-active-tab="false"  id="tab-about" :md-icon=md_icon('about')" md-label="About"></md-tab>
                <md-tab id="tab-api" md-label="API" :md-icon=md_icon('api')" :href="api_url"></md-tab>
                <md-tab id="tab-github" md-label="Code" :md-icon=md_icon('github')" href="https://www.github.com/matthiaskoenig/pkdb"></md-tab>

                <md-tab id="tab-admin" md-label="Admin" :md-icon=md_icon('admin')" :href="admin_url"></md-tab>
                <md-tab id="tab-accounts" md-label="Account" :md-icon=md_icon('account')" to="/account"></md-tab>
        </md-tabs>
    </div>

</template>

<script>
    import {lookup_md_icon} from "@/icons"
    import NavigationItem from "@/components/lib/NavigationItem"

    export default {
        name: 'Navigation',
        data(){
            return {}
        },
        components: {
            NavigationItem: NavigationItem
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
            }
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