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

    <v-dialog v-model="loadingDownload" max-width="600">
      <download-dialog></download-dialog>
    </v-dialog>
  </v-btn>
</template>

<script>
import {SearchMixin} from "../../../search";
import {IconsMixin} from "@/icons"
import DownloadDialog from "../../dialogs/DownloadDialog";
import {StoreInteractionMixin} from "../../../storeInteraction";

export default {
  components: {DownloadDialog},
  mixins:[SearchMixin, IconsMixin, StoreInteractionMixin],
  name: "DownloadButton",
  props: {
    study_count:   {
    type: Number,
    default: () => 0
    }
  }
}
</script>

<style scoped>

</style>