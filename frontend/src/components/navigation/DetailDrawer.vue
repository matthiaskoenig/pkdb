<template>
  <v-navigation-drawer
      v-model="drawer"
      :mini-variant.sync="mini"
      clipped
      app
      permanent
      right
      width="400"
  >
    <v-list-item class="px-2">
      <v-list-item-avatar>
        <v-icon> fas fa fa-question</v-icon>
      </v-list-item-avatar>

      <v-list-item-title>Details</v-list-item-title>

      <v-btn
          icon
          @click.stop="mini = !mini"
      >
        <v-icon>{{faIcon("right_arrow")}}</v-icon>
      </v-btn>
    </v-list-item>

    <v-divider></v-divider>

    <search-help v-if="!mini"/>

  </v-navigation-drawer>
</template>

<script>


import {IconsMixin} from "../../icons";
import SearchHelp from "../search/SearchHelp";

export default {
  name: 'DetailDrawer',
  components: {SearchHelp},
  mixins: [IconsMixin],
  data: () => ({
    drawer: false,
    mini: true,

  })
}
</script>

<style scoped>
</style>