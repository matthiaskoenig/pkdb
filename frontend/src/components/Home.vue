<template>
  <v-main id="home">
    <v-row align="start"
           justify="center">
      <v-col sm="12" md="10" lg="8">
        <overview/>
      </v-col>
    </v-row>
    <v-row align="start"
           justify="center">
      <v-col sm="12" md="10" lg="8">
        <about/>
      </v-col>
    </v-row>
  </v-main>
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