<template>
  <v-btn
      x-small
      fab text
      title="Clear current search"
      @click.stop="reset"
  >
    <v-icon small>fas fa fa-trash-alt</v-icon>
  </v-btn>
</template>

<script>
import {StoreInteractionMixin} from "../../../storeInteraction";

export default {
  mixins: [StoreInteractionMixin],
  name: "ClearSearchButton",


}
</script>

<style scoped>

</style>