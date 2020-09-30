<template>
  <v-navigation-drawer
      v-model="drawer"
      :mini-variant.sync="mini"
      clipped
      permanent
      app
      right
      dark
      mini-variant-width="40"
      width="450"
  >
    <v-list-item @click.stop="mini = !mini" title="Hide details panel">
      <v-btn
          icon
          v-if="!mini"
          @click.stop="mini = !mini"
      >
        <v-icon>{{ faIcon("right_arrow") }}</v-icon>
      </v-btn>

      <v-list-item-avatar v-if="mini" title="Show details panel">
        <v-icon>{{ faIcon('info') }}</v-icon>
      </v-list-item-avatar>

    </v-list-item>
    <detail-content/>

  </v-navigation-drawer>
</template>

<script>


import {IconsMixin} from "../../icons";
import DetailContent from "../detail/DetailContent";
import {StoreInteractionMixin} from "../../storeInteraction";

export default {
  name: 'DetailDrawer',
  components: {
    DetailContent},
  mixins: [IconsMixin, StoreInteractionMixin],
  data: () => ({
    drawer:true
  }),
}
</script>

<style>
</style>