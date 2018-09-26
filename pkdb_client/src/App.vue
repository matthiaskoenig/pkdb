<template>
  <div id="app">
    <head>
      <!-- TODO: check if needed, move to main.js -->
      <link rel="stylesheet" href="//fonts.googleapis.com/css?family=Roboto:400,500,700,400italic|Material+Icons">

    </head>
    <Navigation></Navigation>
    <br />
    <router-view :api="api"></router-view>
    <Footer></Footer>
  </div>
</template>

<script>
import Navigation from './components/Navigation.vue'
import Footer from './components/Footer.vue'

export default {
    name: 'app',
    components: {
        'Navigation': Navigation,
        'Footer': Footer
    },
    data(){
        return {
            api: "http://localhost:8000/api/v1"
            // api: "https://pk-db.com/api/v1"
        }
    }
}
</script>

<style>
#app {
  // font-family: 'Avenir', Helvetica, Arial, sans-serif;
  // -webkit-font-smoothing: antialiased;
  // -moz-osx-font-smoothing: grayscale;
  // text-align: center;
  // color: #2c3e50;
  // margin-top: 0px;
}
</style>
