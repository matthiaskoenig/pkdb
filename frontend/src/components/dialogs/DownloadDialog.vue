<template>
    <v-card>
            <v-card-title>
              Download
            </v-card-title>
            <v-card-text>
              During the download a lot of data processing has to performed. For large datasets this can take up to several minutes.
              <v-spacer></v-spacer>
            </v-card-text>
            <v-list dense >
              <v-header class="pl-6"> You are downloading:</v-header>

              <v-list-item>
                <v-list-item-subtitle>UUID</v-list-item-subtitle>
                <v-list-item-title>{{results.uuid}}</v-list-item-title>

              </v-list-item>
              <v-list-item>
                <v-list-item-subtitle>Studies</v-list-item-subtitle>
                <v-list-item-title>{{results.studies}}</v-list-item-title>

              </v-list-item>
              <v-list-item>
                <v-list-item-subtitle>Groups</v-list-item-subtitle>
                <v-list-item-title>{{results.groups}}</v-list-item-title>

              </v-list-item>
              <v-list-item>
                <v-list-item-subtitle>Individuals</v-list-item-subtitle>
                <v-list-item-title>{{results.individuals}}</v-list-item-title>
              </v-list-item>
              <v-list-item>
                <v-list-item-subtitle>Interventions</v-list-item-subtitle>
                <v-list-item-title>{{results.interventions}}</v-list-item-title>
              </v-list-item>

              <v-list-item>
                <v-list-item-subtitle>Outputs</v-list-item-subtitle>

                <v-list-item-title>{{results.outputs}}</v-list-item-title>

              </v-list-item>

              <v-list-item>
                <v-list-item-subtitle>Timecourse</v-list-item-subtitle>

                <v-list-item-title>{{results.timecourses}}</v-list-item-title>

              </v-list-item>
              <v-list-item>
                <v-list-item-subtitle>Scatter</v-list-item-subtitle>
                <v-list-item-title>{{results.scatter}}</v-list-item-title>
              </v-list-item>
            </v-list>

            <v-card-actions>
              <v-progress-circular indeterminate color="primary"  v-if="loadingDownload"/>

              <v-btn text v-on:click.native="cancel">
                    cancel
                </v-btn>


            </v-card-actions>
    </v-card>
</template>

<script>
    import {StoreInteractionMixin} from "../../storeInteraction";
    import {SearchMixin} from "../../search";

    export default {
      name: "DownloadDialog",
      methods: {
        cancel() {
          this.loadingDownload = false
        }
      },
      mixins:[StoreInteractionMixin, SearchMixin],
    }
</script>

<style scoped>
</style>