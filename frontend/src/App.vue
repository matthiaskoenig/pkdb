<template>
  <div id="app">
    <v-app class="app">
      <v-container fluid>
        <v-row>
          <navigation></navigation>
        </v-row>
        <v-row style="padding-top: 30px;">
          <router-view v-bind:api="api" v-bind:domain="domain"></router-view>
        </v-row>
        <!--
        <v-row>
          <footer-bar></footer-bar>
        </v-row>
        -->
      </v-container>
    </v-app>
  </div>
</template>

<script>
    import Navigation from './components/Navigation.vue';
    // import FooterBar from './components/FooterBar.vue';

    export default {
        name: 'app',
        components: {
            'Navigation': Navigation,
            // 'FooterBar': FooterBar
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
        // text-align: center;
    }

    .app {
        padding: 0;
    }
    .v-card {
        padding: 5px;
        text-align: left;
    }
    .main {
      padding: 20px;
      text-align: left;
    }


    .search {
      color: #41b883;
    }
    .data {
      color: #1e90ff;
    }

    /* attributes */
    .attr {
        font-weight: bold;
    }
    .attr-card {
        width: 110px;
        min-height: 50px;
    }
    .attr-card-no-width {
        height: 50px;
        padding-left: 10px;
        padding-right: 10px;
    }
    .detail-card {
        padding: 10px;
    }
    .detail-dialog {
        width: 200px;
    }
</style>
