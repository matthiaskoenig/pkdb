<template>
    <div id="app">
        <head>
            <!-- TODO: check if needed, move to main.js -->
            <link rel="stylesheet" href="//fonts.googleapis.com/css?family=Roboto:400,500,700,400italic|Material+Icons">
            <meta name="description" content="PK-DB">
            <meta name="author" content="Jan Grzegorzewski and Matthias Koenig">
            <title>PK-DB</title>
        </head>
        <div class="container">
            <div class="row">
                <Navigation v-bind:api="api" v-bind:domain="domain"></Navigation>
            </div>
            <div class="row">
                <router-view v-bind:api="api" v-bind:domain="domain"></router-view>
            </div>

            <div class="row">
                <Footer></Footer>
            </div>
        </div>
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
        background-color: #ffffff;

        margin-left: 20px;
        margin-right: 20px;
    }
</style>
