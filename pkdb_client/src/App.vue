<template>
    <div id="app">
        <v-app>
            <v-container fluid grid-list-xl style="padding: 0;">
                <v-layout row>
                    <v-flex lg12 style="padding-top: 0; padding-bottom: 0;">
                        <navigation></navigation>
                    </v-flex>
                </v-layout>
                <v-layout row style="padding-top: 55px;">
                    <v-flex lg12">
                        <router-view v-bind:api="api" v-bind:domain="domain"></router-view>
                    </v-flex>
                </v-layout>
                <v-layout row>
                    <v-flex lg12>
                    <footer></footer>
                    </v-flex>
                </v-layout>
            </v-container>
        </v-app>
    </div>
</template>

<script>
    import Navigation from './components/Navigation.vue';
    import Footer from './components/Footer.vue';

    export default {
        name: 'app',
        components: {
            'Navigation': Navigation,
            'Footer': Footer
        },
        data() {
            return {}
        },
        computed: {
            domain() {
                return this.$store.state.django_domain;
            },
            api() {
                return this.$store.state.endpoints.api;
            }
        },
    }
</script>

<style lang="scss">
    #app {
        font-family: 'Avenir', Helvetica, Arial, sans-serif;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
        text-align: center;
    }

    /* attributes */
    .attr {
        font-weight: bold;
    }
</style>
