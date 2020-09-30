<template>
  <v-chip
          class="ma-1"
          flat
          pill
          small
          :href="url"
          target="_blank"
  >
    <strong><text-highlight :queries="highlight">{{ name }}</text-highlight> </strong>| <text-highlight :queries="highlight">{{ accession}}</text-highlight>
  </v-chip>
</template>

<script>
import {StoreInteractionMixin} from "../../storeInteraction";

export default {
  name: "Xref",
  mixins: [StoreInteractionMixin],
  props: {
    name: {
      type: String,
      required: true,
    },
    accession: {
      type: String,
      required: true,
    },
    url: {
      type: String,
      required: true,
    }
  }
}
</script>

<style scoped>

</style>