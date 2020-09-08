<template>
  <v-main id="home" class="pl-1 pr-1">
    <v-container fluid>
      <v-row align="start"
             justify="center">
        <v-col xs="11" sm="11" md="10" lg="8">
          <overview/>
        </v-col>
      </v-row>
    </v-container>
  </v-main>
</template>

<script>
import Overview from "./Overview";


export default {
  name: 'Home',
  components: {
    Overview,
  }
}
</script>

<style>
</style>