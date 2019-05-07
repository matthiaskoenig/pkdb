<template>
    <div class="study-info">
        <v-layout wrap>
            <v-flex md2>

            <v-card flat>
                <div v-if="study.substances && study.substances.length>0">
                    <span class="attr">Substances</span><br />

                    <span v-for="s in study.substances" v-bind:key="s">
                        <substance-chip :title="s"/>
                    </span>
                    <!-- <v-icon>{{ icon('substance') }}</v-icon>&nbsp;{{c.name}}<br /></span>-->
                </div>
                <div >
                    <span class="attr">Creator</span><br />
                    <user-avatar :user="study.creator"/>
                </div>

                <div>
                    <span class="attr">Curators</span><br />
                    <user-rating v-for="c in study.curators" :key="c.pk" :user="c"/>
                </div>


                <div v-if="study.keywords && study.keywords.length>0">
                    <span class="attr">Keywords</span><br />
                    <span v-for="keyword in study.keywords" :key="keyword">{{keyword}}<br /></span>
                </div>
                <div>
                    <span class="attr">Files</span><br />
                </div>
                <div v-if="study.files.includes('permission denied')">
                    Permission denied
                </div>

                <div v-else>
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
                    <file-image-view v-if="study.files" :files="study.files"/>
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
            images_url() {
                var list = [];
                for (var k = 0; k < this.study.files.length; k++) {
                    var item = this.study.files[k];
                    if (item.name.endsWith("png")) {
                        list.push(item)
                    }
                }
                return list;
            },
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