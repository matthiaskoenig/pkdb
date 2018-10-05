<template>
    <div id="study-info">
        Name: {{ study.name }}<br />
        Reference: <a v-if="study.reference" :href="study.reference" :title="study.reference"><v-icon>{{ icon('reference') }}</v-icon></a><br />
        Creator: <UserAvatar :user="study.creator"/><br />
        Curators: <span v-for="c in study.curators" :key="c.pk"><UserAvatar :user="c"/></span><br />
        Substances: <span v-for="c in study.substances" :key="c.pk"><v-icon>{{ icon('substance') }}</v-icon>{{c.name}}</span><br />
        Files: <span v-for="f in study.files" :key="f"><a :href="f.pk" :title="f"><v-icon>{{ icon('file') }}</v-icon></a>&nbsp;</span><br />
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