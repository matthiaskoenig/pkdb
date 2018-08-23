<template>
  <div id="app">
      <Reference></Reference>
  </div>
</template>

<script>
import Reference from './components/Reference'
export default {
  name: 'App',
  components: {
    Reference
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
