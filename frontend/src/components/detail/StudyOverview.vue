<template>
  <!--
  <v-card
      width="100%"
      flat
  >
    <v-list-item three-line>
      <v-list-item-content>
        <div class="overline mb-4">
          <json-button v-if="url" :resource_url="url"></json-button> {{ data.ntype.toUpperCase() }}
          STUDY
        </div>

        <v-list-item-title class="headline mb-1"><text-highlight :queries="highlight">{{ data.label }}</text-highlight></v-list-item-title>
        <v-list-item-subtitle v-if="parents_labels.length>0">Parents: {{ parents_labels.join(', ') }}</v-list-item-subtitle>
      </v-list-item-content>
    </v-list-item>

    <v-card-text>
      <div v-if="data.description && data.description.length>0">
        <text-highlight :queries="highlight">
          {{ data.description }}<br />
        </text-highlight>
      </div>
  -->



    <div class="study-info">
        <v-layout wrap>
            <v-flex md3>
                <v-card flat>
                <v-icon color="black">{{ faIcon('study') }}</v-icon>
                <span class="heading-title">&nbsp;{{ study.name }} ({{ study.sid }})</span><br />

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
                    {{ study.date }}<br />

                <Annotations :item="study"/>
                </v-card>
            </v-flex>

            <v-flex md2>
                <v-card flat>
                    <div>
                        <span class="attr">Creator</span><br />
                        <user-avatar :user="study.creator"/>
                    </div>
                    <div>
                        <span class="attr">Curators</span><br />
                        <user-rating v-for="curator in study.curators"
                                     :key="curator.username"
                                     :user="curator"
                        />
                    </div>
                     <div v-if="study.files.length > 0">
                        <span class="attr">Files</span><br />
                          <span v-for="file in study.files" :key="file.pk">
                                <file-chip :file="file.file" />
                        </span>
                    </div>

                </v-card>
            </v-flex>
            <v-flex md2>
                <v-card flat>
                    <div v-if="study.substances && study.substances.length!=0">
                        <span class="attr">Substances</span><br />
                        <span v-for="substance in study.substances" :key="substance.sid">
                            <object-chip :object="substance"
                                         otype="substance"
                            />
                        </span>
                    </div>
                </v-card>
            </v-flex>

            <v-flex md5>
                <v-alert v-if="study.files.length == 0"
                         dense
                         text
                         type="info"
                >
                    No images or no permission
                </v-alert>
                <file-image-view v-else :files="images"/>
            </v-flex>

        </v-layout>
        <v-layout wrap>
            <v-flex md7>
                        <reference-detail :reference="study.reference" :resource_url="reference_url(study.reference.sid)"/>
            </v-flex>
        </v-layout>
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