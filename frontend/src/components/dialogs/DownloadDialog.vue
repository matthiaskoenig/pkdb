<template>
    <v-card>
            <v-card-title>
              Download
            </v-card-title>
            <v-card-text>
              Download can take a very long (5 min) if you do not filter for a small amount of data.
              <v-spacer></v-spacer>
            </v-card-text>
            <v-list dense>
              <v-subheader> You are downloading:</v-subheader>

              <v-list-item>
                <v-subheader>UUID</v-subheader>
                <v-list-item-content>
                <v-list-item-title>{{results.uuid}}</v-list-item-title>
                </v-list-item-content>

              </v-list-item>
              <v-list-item>
                <v-subheader>Studies</v-subheader>
                <v-list-item-content>
                <v-list-item-title>{{results.studies}}</v-list-item-title>
                </v-list-item-content>

              </v-list-item>
              <v-list-item>
                <v-subheader>Groups</v-subheader>
                <v-list-item-content>
                <v-list-item-title>{{results.groups}}</v-list-item-title>
                </v-list-item-content>

              </v-list-item>
              <v-list-item>
                <v-subheader>Individuals</v-subheader>
                <v-list-item-content>
                <v-list-item-title>{{results.individuals}}</v-list-item-title>
                </v-list-item-content>

              </v-list-item>
              <v-list-item>
                <v-subheader>Interventions</v-subheader>

                <v-list-item-content>
                <v-list-item-title>{{results.interventions}}</v-list-item-title>
                </v-list-item-content>

              </v-list-item>

              <v-list-item>
                <v-subheader>Outputs</v-subheader>

                <v-list-item-content>
                <v-list-item-title>{{results.outputs}}</v-list-item-title>
                </v-list-item-content>

              </v-list-item>

              <v-list-item>
                <v-subheader>Timecourse</v-subheader>

                <v-list-item-content>
                <v-list-item-title>{{results.timecourses}}</v-list-item-title>
                </v-list-item-content>

              </v-list-item>
              <v-list-item>
                <v-subheader>Scatter</v-subheader>

                <v-list-item-content>
                <v-list-item-title>{{results.scatter}}</v-list-item-title>
                </v-list-item-content>

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