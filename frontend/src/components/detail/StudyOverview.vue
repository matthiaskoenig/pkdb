<template>
    <v-card flat class="ma-0 pa-0">


      <v-card-title>
        <v-list-item three-line >
          <v-list-item-content>
            <div class="overline">
              <v-icon class="mr-4">{{ faIcon('study') }}</v-icon> Study
              <text-highlight :queries="highlight">
              {{ study.name }} ({{ study.sid }})
              </text-highlight>
              <JsonButton :resource_url="api + 'studies/'+ study.sid +'/?format=json'"/>
            </div>
            <v-list-item-title class="headline mb-1">
                <v-icon small
                        :title="'Study is '+ study.access"
                        :color="study.access =='public' ? 'green' : 'red'"
                >{{ faIcon(study.access) }}
                </v-icon>

                <v-icon small class="ma-2"
                        :title="'Publication is '+ study.licence + ' licence'"
                        :color="study.licence =='open' ? 'green' : 'red'"
                >{{ faIcon(study.licence) }}
                </v-icon>

            </v-list-item-title>


          </v-list-item-content>
        </v-list-item>
      </v-card-title>
      <v-card-text>




      <v-row>
        <v-col cols="6">
          <div v-if="study.substances && study.substances.length!=0">
            <span class="attr">Substances</span><br/>
            <span v-for="substance in study.substances" :key="substance.sid">
                            <object-chip :object="substance"
                                         otype="substance"
                            />
                        </span>
          </div>
        </v-col>

        <v-col cols="6">

          <div>
            <span class="attr">Creator</span><br/>
            <user-avatar :user="study.creator"/>
          </div>
          <div class="mt-4">
            <span class="attr">Curators</span><br/>
            <user-rating v-for="curator in study.curators"
                         :key="curator.username"
                         :user="curator"
            />
          </div>
        </v-col>
      </v-row>

      <v-row>
        <v-col>
          <reference-detail :reference="study.reference" :resource_url="reference_url(study.reference.sid)"/>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-alert v-if="study.files.length == 0"
            dense
            text
            type="info"
          >
            No images or no permission
          </v-alert>
          <file-image-view v-else :files="images"/>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <div v-if="study.files.length > 0">
            <span class="attr">Files</span><br/>
            <span v-for="file in study.files" :key="file.pk">
              <file-chip :file="file.file"/>
            </span>
          </div>
        </v-col>
      </v-row>
      <v-row>
        <annotations :item="study" title="Study"/>
        <annotations  v-if="study.groupset" title="Groups" :item="study.groupset"/>
        <annotations v-if="study.individualset" title="Individuals" :item="study.individualset"/>
        <annotations v-if="study.interventionset" title="Interventions" :item="study.interventionset"/>
        <annotations v-if="study.outputset" title="Outputs" :item="study.outputset"/>
      </v-row>
      </v-card-text>

    </v-card>
</template>

<script>
import {lookupIcon} from "@/icons"
import ReferenceDetail from "./ReferenceDetail"
import FileImageView from "./FileImageView"
import {UrlMixin} from "../tables/mixins";
import {ApiInteractionMixin} from "../../apiInteraction";

export default {
  name: "StudyOverview",
  components: {
    ReferenceDetail: ReferenceDetail,
    FileImageView: FileImageView,
  },
  props: {
    study: {
      type: Object,
      required: true,
    }
  },
  mixins: [UrlMixin, ApiInteractionMixin],

  computed: {
    images() {
      let list = [];
      for (let k = 0; k < this.study.files.length; k++) {
        let item = this.study.files[k];

        if (this.is_image(item.file)) {
          list.push(item)
        }
      }
      // FIXME: sort by filename

      return list;
    }
  },
  methods: {
    faIcon: function (key) {
      return lookupIcon(key)
    },
    is_image(file) {
      return (file.endsWith(".png") || file.endsWith(".jpg") || file.endsWith(".jpeg"));
    }
  }

}
</script>

<style scoped>
</style>