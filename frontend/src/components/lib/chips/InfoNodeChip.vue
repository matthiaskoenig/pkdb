<template>
  <v-chip
      class="ma-1"
      color="black"
      outlined
      pill
      small
  >
    <!-- highlight name for curation -->
    <span v-if="item.label === item.name">
            <strong><text-highlight :queries="highlight.split(/[ ,]+/)">{{ item.label }}</text-highlight></strong>
          </span>
    <span v-if="item.label !== item.name">
            <text-highlight :queries="highlight.split(/[ ,]+/)">{{ item.label }}</text-highlight> |
            <strong><text-highlight :queries="highlight.split(/[ ,]+/)">{{ item.name }}</text-highlight></strong>
          </span>
  </v-chip>
</template>

<script>
import {StoreInteractionMixin} from "../../../storeInteraction";

export default {
  name: "InfoNodeChip",
  mixins:[StoreInteractionMixin],
  props:{
    item:{
      type: Object
    }
  }
}
</script>

<style scoped>

</style>