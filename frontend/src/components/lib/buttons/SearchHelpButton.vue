<template>
  <v-btn
      small
      fab
      icon
      text
      title="Search help with examples"
      @click.stop="show_help"
      class="mr-4"

  >

    <v-icon >fas fa fa-question</v-icon>
  </v-btn>
</template>

<script>
import {StoreInteractionMixin} from "../../../storeInteraction";

export default {
  name: "SearchHelpButton",
  mixins: [StoreInteractionMixin],
  methods: {
      show_help() {
        this.show_type = 'help'
        this.display_detail = true
      }
  }

}
</script>

<style scoped>

</style>