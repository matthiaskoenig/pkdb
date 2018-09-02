<template>
        <b-navbar toggleable="md" type="dark" variant="primary">

            <b-navbar-toggle target="nav_collapse"></b-navbar-toggle>

            <router-link tag="span" to="/">
            <b-navbar-brand href="#">PK-DB</b-navbar-brand>
            </router-link>
            <b-collapse is-nav id="nav_collapse">

                <b-navbar-nav>
                    <!--
                    <b-nav-item active href="#" v-for="routes in links" v-bind:key="routes.id" :to="`${routes.page}`">{{routes.text}}</b-nav-item>
                    -->
                    <b-nav-item active href="#" v-for="(item, index) in links" :key="index" :to="`${item.page}`"><font-awesome-icon :icon="item.icon" />&nbsp;{{item.text}}</b-nav-item>


                </b-navbar-nav>

                <b-navbar-nav class="ml-auto">


                    <router-link tag="li" to="/about">
                        <b-nav-item active href="#"><font-awesome-icon icon="info-circle" />&nbsp;About</b-nav-item>
                    </router-link>
                    <b-nav-item active href="http://www.pk-db.com/api/" target="_blank"><font-awesome-icon icon="laptop-code" />&nbsp;API</b-nav-item>
                    <b-nav-item active href="http://www.github.com/matthiaskoenig/pkdb" target="_blank"><font-awesome-icon :icon="[ 'fab', 'github' ]" />&nbsp;Code</b-nav-item>

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
                        id: 1,
                        text: 'Studies',
                        page: '/studies',
                        icon: 'procedures'
                    },
                    {
                        id: 2,
                        text: 'Groups',
                        page:'/groups',
                        icon: 'users'
                    },
                    {
                        id: 3,
                        text: 'Individuals',
                        page:'/individuals',
                        icon: 'user'
                    },
                    {
                        id: 4,
                        text: 'Interventions',
                        page:'/interventions',
                        icon: 'capsules'
                    },
                    {
                        id: 5,
                        text: 'Outputs',
                        page:'/outputs',
                        icon: 'chart-bar'
                    },
                    {
                        id: 6,
                        text: 'Timecourses',
                        page:'/timecourses',
                        icon: 'chart-line'
                    },
                    {
                        id: 7,
                        text: 'References',
                        page:'/references',
                        icon: 'file-alt'
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