<template>
    <div id="app">
        <head>
            <meta name="description" content="PK-DB">
            <meta name="author" content="Jan Grzegorzewski and Matthias Koenig">
            <title>PK-DB</title>
        </head>

        <v-container grid-list-md text-xs-center>
            <v-layout row wrap>
                <v-flex xs12>
                    <Navigation></Navigation>
                </v-flex>

                <v-flex xs12>
                    <router-view v-bind:api="api" v-bind:domain="domain"></router-view>
                </v-flex>
                <v-flex>
                <Footer></Footer>
                </v-flex>
            </v-layout>
        </v-container>
    </div>
</template>

<script>
    import Navigation from '@/components/Navigation.vue';
    import Footer from '@/components/Footer.vue';

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

<style>
    #app {
        font-family: 'Avenir', Helvetica, Arial, sans-serif;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }
</style>
