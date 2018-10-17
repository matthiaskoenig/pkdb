<template>
    <div class="study-info">
        <v-layout>
            <v-flex xs2>
            <v-card flat>

                <div>
                    <span class="attr">Name</span><br />
                    {{ study.name }}
                </div>

                <div>
                    <span class="attr">Creator</span><br />
                    <user-avatar :user="study.creator"/>
                </div>

                <div>
                    <span class="attr">Curators</span><br />
                    <user-avatar v-for="c in study.curators" :key="c.pk" :user="c"/>
                </div>

                <div>
                    <span class="attr">Substances</span><br />
                    <span v-for="c in study.substances" :key="c.pk"><v-icon>{{ icon('substance') }}</v-icon>{{c.name}}</span><br />
                </div>
                <div>
                    <span class="attr">Files</span><br />
                    <span v-for="f in study.files" :key="f.name"><a :href="f.pk" :title="f.name"><v-icon>{{ icon('file') }}</v-icon></a>&nbsp;</span>
                </div>
            </v-card>

            </v-flex>
            <v-flex xs5>
                <get-data v-if="study.reference" :resource_url="study.reference">
                    <template slot-scope="reference">
                        <reference-detail :reference="reference.data" :resource_url="study.reference"/>
                    </template>
                </get-data>
            </v-flex>
            <v-flex>
                <file-image-view v-if="study.files" :files="study.files"/>
            </v-flex>

        </v-layout>
    </div>
</template>

<script>
    import {lookup_icon} from "@/icons"
    import ReferenceDetail from "./ReferenceDetail"
    import FileImageView from "./FileImageView"

    export default {
        name: "StudyInfo",
        components: {
            ReferenceDetail: ReferenceDetail,
            FileImageView: FileImageView
        },
        props: {
            study: {
                type: Object,
                required: true,
            }
        },

        computed: {
            images() {
                var list = [];
                for (var k = 0; k < this.study.files.length; k++) {
                    var item = this.study.files[k];
                    console.log(item);
                    if (item.name.endsWith("png")) {
                        list.push(item)
                    }
                }
                return list;
            }
        },
        methods: {
            icon: function (key) {
                return lookup_icon(key)
            },
        }
    }
</script>

<style scoped>
    .study-info {
        padding-top: 10px;
    / / height: 70 px;
    }
</style>