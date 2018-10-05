<template>
    <div id="study-info">
        <v-layout row wrap>
            <v-flex xs2>
                <v-btn color="info" flat>Name</v-btn><br/>
                {{ study.name }}
            </v-flex>
            <v-flex xs2>
                <v-btn color="info" flat>Reference</v-btn><br/>
                <a v-if="study.reference" :href="study.reference" :title="study.reference"><v-icon>{{ icon('reference') }}</v-icon></a>
            </v-flex>
            <v-flex xs2>
                <v-btn color="info" flat>Creator</v-btn><br/>
                <UserAvatar :user="study.creator"/>
            </v-flex>
            <v-flex xs2>
                <v-btn color="info" flat>Curators</v-btn><br/>
                <span v-for="c in study.curators" :key="c.pk"><UserAvatar :user="c"/></span><br />
            </v-flex>
            <v-flex xs2>
                <v-btn color="info" flat>Substances</v-btn><br/>
                <span v-for="c in study.substances" :key="c.pk"><v-icon>{{ icon('substance') }}</v-icon>{{c.name}}<br /></span>
            </v-flex>
            <v-flex xs2>
                <v-btn color="info" flat>Files</v-btn><br/>
                <span v-for="f in study.files" :key="f"><a :href="f.pk" :title="f"><v-icon>{{ icon('file') }}</v-icon></a>&nbsp;</span>
            </v-flex>
        </v-layout>
    </div>
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