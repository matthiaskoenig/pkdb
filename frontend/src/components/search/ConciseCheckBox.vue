<template>
  <v-checkbox
      type="checkbox"
      class="ma-0"
      v-model="concise"
      @click.stop=""
      label="Concise"
      hide-details
      hint="Concises the data."
  ></v-checkbox>
</template>
<script>
import {StoreInteractionMixin} from "../../storeInteraction";

export default {
  name: "ConciseCheckBox",
  mixins: [StoreInteractionMixin]
}
</script>

<style scoped>

</style>