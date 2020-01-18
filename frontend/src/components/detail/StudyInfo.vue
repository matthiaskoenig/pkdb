<template>
    <div class="study-info">
        <v-layout wrap>
            <v-flex md4>
                <v-btn icon>
                    <v-icon small
                            :title="'Study has '+ study.access + ' access'"
                            :color="study.access =='public' ? 'green' : 'red'"
                    >{{icon(study.access)}}</v-icon>
                </v-btn>
                <v-btn icon>
                    <v-icon small
                            :title="'Publication is '+ study.licence + ' access'"
                            :color="study.licence =='open' ? 'green' : 'red'"
                    >{{icon(study.licence)}}</v-icon>
                </v-btn>
                <get-data v-if="study.reference" :resource_url="reference_url(study.reference.sid)">
                    <template slot-scope="reference">
                        <reference-detail :reference="reference.data" :resource_url="reference_url(study.reference.sid)"/>
                    </template>
                </get-data>
                <Annotations :item="study"/>
            </v-flex>

            <v-flex md2>
                <v-card flat>
                    <div>
                        <span class="attr">Creator</span><br />
                        <user-avatar :user="study.creator"/>
                    </div>
                    <div>
                        <span class="attr">Curators</span><br />
                        <user-rating v-for="curator in study.curators" :key="curator.pk" :user="curator"/>
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
                        <span v-for="s in study.substances" v-bind:key="s">
                            <substance-chip :title="s"/>
                        </span>
                    </div>
                </v-card>
            </v-flex>

            <v-flex md4>
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
    </div>
</template>

<script>
    import {lookup_icon} from "@/icons"
    import ReferenceDetail from "./ReferenceDetail"
    import FileImageView from "./FileImageView"
    import {UrlMixin} from "../tables/mixins";
    import CountChip from "../detail/CountChip";

    export default {
        name: "StudyInfo",
        components: {
            ReferenceDetail: ReferenceDetail,
            FileImageView: FileImageView,
            CountChip: CountChip
        },
        props: {
            study: {
                type: Object,
                required: true,
            }
        },
        mixins: [UrlMixin],

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
            icon: function (key) {
                return lookup_icon(key)
            },
            is_image(file){
                return (file.endsWith(".png") || file.endsWith(".jpg") || file.endsWith(".jpeg"));
            }
        }

    }
</script>

<style scoped>
    .study-info {
        padding-top: 50px;
    }
</style>