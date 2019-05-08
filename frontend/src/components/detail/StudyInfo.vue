<template>
    <div class="study-info">
        <v-layout wrap>
            <v-flex md2>

            <v-card flat>
                <div v-if="study.substances && study.substances.length>0">
                    <span class="attr">Substances</span><br />
                    <span v-for="s in study.substances.sort()" v-bind:key="s">
                        <substance-chip :title="s"/>
                    </span>
                </div>

                <div v-if="study.keywords && study.keywords.length>0">
                    <span class="attr">Keywords</span><br />
                    <span v-for="keyword in study.keywords.sort()" :key="keyword">
                        <keyword-chip :keyword="keyword"/><br />
                    </span>
                </div>

                <div>
                    <span class="attr">Creator</span><br />
                    <user-avatar :user="study.creator"/>
                </div>

                <div>
                    <span class="attr">Curators</span><br />
                    <user-rating v-for="c in study.curators.sort()" :key="c.pk" :user="c"/>
                </div>

                <div v-if="study.files && study.files.length>0">
                    <span class="attr">Files</span><br />
                      <span v-if="file" v-for="file in study.files">
                        <div v-if="file.file">
                            <file-chip v-if="!is_image(file.file)" :file="file.file" />
                        </div>
                    </span>
                </div>
            </v-card>

            </v-flex>
            <v-flex md5>
                <get-data v-if="study.reference" :resource_url="reference_url(study.reference.sid)">
                    <template slot-scope="reference">
                        <reference-detail :reference="reference.data" :resource_url="reference_url(study.reference.sid)"/>
                    </template>
                </get-data>
                <Annotations :item="study"/>
            </v-flex>
            <v-flex md5>
                <div v-if="study.files.length == 0">
                    <warning-chip title="no files or no permission"></warning-chip>
                </div>
                <div v-else>
                    <file-image-view v-if="images.length != 0" :files="images"/>
                </div>
            </v-flex>

            <v-flex md12>

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
    import WarningChip from "./WarningChip";

    export default {
        name: "StudyInfo",
        components: {
            WarningChip,
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
                var list = [];
                for (var k = 0; k < this.study.files.length; k++) {
                    var item = this.study.files[k];

                    if (this.is_image(item.file)) {
                        list.push(item)
                    }
                }
                return list;
            },
            image_files(){

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