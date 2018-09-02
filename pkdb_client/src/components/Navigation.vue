<template>
        <b-navbar toggleable="md" type="dark" variant="primary">

            <b-navbar-toggle target="nav_collapse"></b-navbar-toggle>

            <b-navbar-brand href="#">PK-DB</b-navbar-brand>
            <b-collapse is-nav id="nav_collapse">

                <b-navbar-nav>
                    <b-nav-item active href="#" v-for="routes in links" v-bind:key="routes.id" :to="`${routes.page}`">{{routes.text}}</b-nav-item>
                </b-navbar-nav>

                <b-navbar-nav class="ml-auto">

                    <b-nav-item active href="http://www.pk-db.com/api/" target="_blank">API <img src="../assets/images/swagger.png" height="20" /></b-nav-item>
                    <b-nav-item active href="http://www.github.com/matthiaskoenig/pkdb" target="_blank"><font-awesome-icon icon="file-alt" /> Test</b-nav-item>

                </b-navbar-nav>


                <!-- Right aligned nav items
                <b-navbar-nav class="ml-auto">

                    <b-nav-form>
                        <b-form-input size="sm" class="mr-sm-2" type="text" placeholder="Search"/>
                        <b-button size="sm" class="my-2 my-sm-0" type="submit">Search</b-button>
                    </b-nav-form>

                    <b-nav-item-dropdown right>
                        <template slot="button-content">
                            <em>User</em>
                        </template>
                        <b-dropdown-item href="#">Profile</b-dropdown-item>
                        <b-dropdown-item href="#">Signout</b-dropdown-item>
                    </b-nav-item-dropdown>
                </b-navbar-nav>
                -->

            </b-collapse>
        </b-navbar>

        <!-- direct router links
        <nav>
            <router-link class="spacing" v-for="routes in links"
                         v-bind:key="routes.id"
                         :to="`${routes.page}`">{{routes.text}}</router-link>
        </nav>
        -->
</template>

<script>
    export default {
        name: 'Navigation',
        data() {
            return {
                links: [
                    {
                        id: 0,
                        text: 'Home',
                        page:'/'
                    },
                    {
                        id: 1,
                        text: 'Studies',
                        page:'/studies'
                    },
                    {
                        id: 2,
                        text: 'Groups',
                        page:'/groups'
                    },
                    {
                        id: 3,
                        text: 'Individuals',
                        page:'/individuals'
                    },
                    {
                        id: 4,
                        text: 'Interventions',
                        page:'/interventions'
                    },
                    {
                        id: 5,
                        text: 'Outputs',
                        page:'/outputs'
                    },
                    {
                        id: 6,
                        text: 'Timecourses',
                        page:'/timecourses'
                    },
                    {
                        id: 7,
                        text: 'References',
                        page:'/references'
                    },
                    {
                        id: 4,
                        text: 'About',
                        page:'/about'
                    },

                ]
            }
        }
    }
</script>
<style>
    .spacing {
        margin-right: 10px;
    }
</style>