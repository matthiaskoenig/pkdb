<template>
  <v-card>
    <v-card-title>
      <v-progress-circular
          v-if="loadingDownload"
          indeterminate
          color="primary"
          class="mr-2"
          title="Download in progress, please be patient"
      />
      Download in progress
    </v-card-title>

    <v-card-text>
      Data processing for download can take up to several minutes for large datasets.
      Please be patient.

    <v-list dense>
      <v-header>Data content</v-header>
      <v-list-item v-for="(item, key) in results" :key="key">
        <v-list-item-subtitle>{{ key }}</v-list-item-subtitle>
        <v-list-item-title>{{ item }}</v-list-item-title>
      </v-list-item>
    </v-list>

      <v-spacer></v-spacer>
      <v-btn text v-on:click.native="cancel">
        <v-icon left>{{ faIcon("cancel") }}</v-icon>
        cancel
      </v-btn>
    </v-card-text>
  </v-card>
</template>

<script>
import {StoreInteractionMixin} from "../../storeInteraction";
import {IconsMixin} from "../../icons";

export default {
  name: "DownloadDialog",
  methods: {
    cancel() {
      // FIXME: stop download server side
      this.loadingDownload = false
    }
  },
  mixins: [StoreInteractionMixin, IconsMixin],
}
</script>

<style scoped>
</style>