<template>
  <div id="app">
    <img alt="Vue logo" src="./assets/bg.jpg" height="100">
    <About msg="Welcome to the PK-DB App"/>
    <div id="footer">
      <!-- FOOTER -->
      <p>&copy; 2017-2018 PK-DB</p>
    </div>
  </div>

</template>

<script>
import About from './components/About.vue'

export default {
  name: 'app',
  components: {
      About
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
