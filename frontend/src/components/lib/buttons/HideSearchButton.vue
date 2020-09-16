<template>
  <v-btn
      class="ml-4"
      x-small
      icon
      title="Hide search panel"
      @click.stop="hide_search = !hide_search"
  >
    <v-icon>{{ faIcon("left_arrow") }}</v-icon>
  </v-btn>
</template>

<script>

import {StoreInteractionMixin} from "../../../storeInteraction";
import {IconsMixin} from "../../../icons";

export default {
  name: "HideSearchButton",
  mixins: [StoreInteractionMixin,IconsMixin],

}
</script>

<style scoped>

</style>