<template>
    <div id="app">
        <v-app>
            <v-container fluid grid-list-xl>
                <v-layout row>
                    <v-flex lg12>
                        <Navigation></Navigation>
                    </v-flex>
                </v-layout>
                <v-layout row>
                    <v-flex lg12>
                        <router-view v-bind:api="api" v-bind:domain="domain"></router-view>
                    </v-flex>
                </v-layout>
                <v-layout row>
                    <v-flex lg12>
                    <Footer></Footer>
                    </v-flex>
                </v-layout>
            </v-container>
        </v-app>
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

<style lang="scss">
    #app {
        font-family: 'Avenir', Helvetica, Arial, sans-serif;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
        text-align: center;
    }
</style>
