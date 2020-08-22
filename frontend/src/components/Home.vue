<template>
  <div id="home">
    <v-row>
      <v-col>
        <overview/>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <about/>
      </v-col>
    </v-row>
  </div>
</template>

<script>
import Overview from "./Overview";
import About from './About'

export default {
  name: 'Home',
  components: {
    Overview,
    About,
  }
}
</script>

<style>
</style>