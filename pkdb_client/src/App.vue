<template>
  <div id="app">
    <!--<img alt="Vue logo" src="./assets/bg.jpg" height="100">-->
    <Navigation></Navigation>
    <router-view/>
    <div id="footer">
      <!-- FOOTER -->
      <p>&copy; 2017-2018 PK-DB</p>
    </div>
  </div>

</template>

<script>
import Navigation from './components/Navigation.vue'

export default {
    name: 'app',
    components: {
        'Navigation': Navigation
    }
}
</script>

<style>
#app {
  font-family: 'Avenir', Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  margin-top: 60px;
}
</style>
