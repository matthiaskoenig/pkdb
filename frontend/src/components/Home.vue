<template>
  <v-main id="home" class="pl-1 pr-1">
    <v-container fluid>
      <v-row align="start"
             justify="center">
        <v-col xs="11" sm="11" md="10" lg="8">
          <overview/>
        </v-col>
      </v-row>
      <v-row align="start"
             justify="center">
        <v-col sm="11" md="10" lg="8">
          <about/>
        </v-col>
      </v-row>
    </v-container>
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