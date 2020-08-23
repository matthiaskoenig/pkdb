<template>

    <div class="study-info">
      <v-card flat>
      <v-row>
        <v-col col="12">
        <v-icon color="black">{{ faIcon('study') }}</v-icon>
        <span class="heading-title">&nbsp;{{ study.name }} ({{ study.sid }})</span>
          <v-btn icon>
            <v-icon small
                    :title="'Study is '+ study.access"
                    :color="study.access =='public' ? 'green' : 'red'"
            >{{ faIcon(study.access) }}</v-icon>
          </v-btn>

          <v-btn icon>
            <v-icon small
                    :title="'Publication is '+ study.licence + ' access'"
                    :color="study.licence =='open' ? 'green' : 'red'"
            >{{ faIcon(study.licence) }}</v-icon>
          </v-btn>
        </v-col>
      </v-row>


        <v-row>
          <v-col cols="4">
        <div v-if="study.substances && study.substances.length!=0">
          <span class="attr">Substances</span><br />
          <span v-for="substance in study.substances" :key="substance.sid">
                            <object-chip :object="substance"
                                         otype="substance"
                            />
                        </span>
        </div>
          </v-col>

          <v-col cols="4">
            <div>
              <span class="attr">Creator</span><br />
              <user-avatar :user="study.creator"/>
            </div>
          </v-col>
          <v-col cols="4">

          <span class="attr">Curators</span><br />
          <user-rating v-for="curator in study.curators"
                       :key="curator.username"
                       :user="curator"
          />
          </v-col>
        </v-row>

      <v-row>
        <v-col>
        <reference-detail :reference="study.reference" :resource_url="reference_url(study.reference.sid)"/>
        </v-col>
      </v-row>

        <v-row>
          <v-col>
          <Annotations :item="study"/>
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
              <span class="attr">Files</span><br />
              <span v-for="file in study.files" :key="file.pk">
                            <file-chip :file="file.file" />
              </span>
            </div>
          </v-col>
        </v-row>
      </v-card>





              <!--

                -->







    </div>
</template>

<script>
    import {lookupIcon} from "@/icons"
    import ReferenceDetail from "./ReferenceDetail"
    import FileImageView from "./FileImageView"
    import {UrlMixin} from "../tables/mixins";

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
        mixins: [UrlMixin],

        computed: {
          highlight(){
            return this.$store.state.highlight
          },
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
            is_image(file){
                return (file.endsWith(".png") || file.endsWith(".jpg") || file.endsWith(".jpeg"));
            }
        }

    }
</script>

<style scoped>
</style>