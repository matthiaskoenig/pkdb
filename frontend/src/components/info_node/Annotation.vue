<template>
  <v-chip
      class="ma-1"
      color="black"
      dark
      pill
      small
      :href="annotation.url"
      target="_blank"
      :title="'Open ' + annotation.collection + '|' + annotation.term"
  >
    <text-highlight :queries="highlight">
        {{ annotation.relation }}
    </text-highlight> |
    <strong>
      <text-highlight :queries="highlight">
        {{ annotation.collection }}
      </text-highlight>
    </strong>|
    <text-highlight :queries="highlight">
      {{ annotation.term }}
    </text-highlight>
  </v-chip>
</template>

<script>
import {StoreInteractionMixin} from "../../storeInteraction";

export default {
  name: "Annotation",
  mixins: [StoreInteractionMixin],
  props: {
    annotation: {
      type: Object,
      required: true,
    }
  }


}
</script>

<style scoped>

</style>