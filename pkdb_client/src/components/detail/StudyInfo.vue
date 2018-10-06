<template>
    <v-layout id="study-info" row wrap>
        <v-flex>
            <info-text>Name</info-text><br/>
            {{ study.name }}
        </v-flex>
        <v-flex>
            <info-text>Reference</info-text><br/>
            <a v-if="study.reference" :href="study.reference" :title="study.reference"><v-icon>{{ icon('reference') }}</v-icon></a>
        </v-flex>
        <v-flex>
            <info-text>Creator</info-text><br/>
            <UserAvatar :user="study.creator"/>
        </v-flex>
        <v-flex>
            <info-text>Curators</info-text><br/>
            <span v-for="c in study.curators" :key="c.pk"><UserAvatar :user="c"/></span><br />
        </v-flex>
        <v-flex>
            <info-text>Substances</info-text><br/>
            <span v-for="c in study.substances" :key="c.pk"><v-icon>{{ icon('substance') }}</v-icon>{{c.name}}<br /></span>
        </v-flex>
        <v-flex>
            <info-text>Files</info-text><br/>
            <span v-for="f in study.files" :key="f"><a :href="f.pk" :title="f"><v-icon>{{ icon('file') }}</v-icon></a>&nbsp;</span>
        </v-flex>
    </v-layout>
</template>

<script>
    import {lookup_icon} from "@/icons"

    export default {
        name: "StudyInfo",
        props: {
            study: {
                type: Object,
                required: true,
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
</style>