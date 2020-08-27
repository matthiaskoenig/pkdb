<template>
  <div id="app">
    <v-app class="app">
          <navigation></navigation>
        <v-row>
          <router-view v-bind:api="api" v-bind:domain="domain"></router-view>
        </v-row>
        <!--
        <v-row>
          <footer-bar></footer-bar>
        </v-row>
        -->
    </v-app>
  </div>
</template>

<script>
    import Navigation from './components/navigation/Navigation.vue';
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
      padding: 0px;
      text-align: left;
    }
    html { overflow-y: auto !important; }
    .search-navbar {
      position: fixed;
      top: 48px;
      left: 0;
      z-index: 9999;
      margin-left: 5px;
      margin-right: 5px;
      height: 32px;
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
