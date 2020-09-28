<template>
  <v-btn
      fab
      text
      icon
      small
ater      title="Hide search panel"
      @click.stop="hide_search = !hide_search"
  >
    <v-icon>{{ faIcon("left_arrow") }}</v-icon>
  </v-btn>

  <!--

<v-btn
    small
    fab
    icon
    text
    title="Search help with examples"
    @click.stop="show_help"
>

  <v-icon >fas fa fa-question</v-icon>
</v-btn>
-->
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