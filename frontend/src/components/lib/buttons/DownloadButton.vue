<template>

  <v-btn v-if="study_count>0"
         fab
         x-small
         text
         @click.stop="downloadData"
         :loading="loadingDownload"
         :disabled="loadingDownload"
         title="Download selected data"
  >
    <v-icon small>{{ faIcon('download') }}</v-icon>

  </v-btn>
</template>

<script>
import {SearchMixin} from "../../../search";
import {IconsMixin} from "@/icons"

export default {
  mixins:[SearchMixin, IconsMixin],
  name: "DownloadButton",
  props: {
    study_count:   {
    type: Number,
    default: () => 0

},
  },
  data(){
    return {
      loadingDownload: false,
    }
  }
}
</script>

<style scoped>

</style>