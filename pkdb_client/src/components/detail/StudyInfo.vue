<template>
    <div id="study-info">
        Name: {{ study.name }}<br />
        Reference: <a v-if="study.reference" :href="study.reference" :title="study.reference"><v-icon>{{ icon('reference') }}</v-icon></a><br />
        Creator: <UserAvatar :user="study.creator"/><br />
        Curators: <span v-for="(c, index2) in study.curators" :key="index2"><UserAvatar :user="c"/></span><br />
        Substances: <span v-for="(c, index2) in study.substances" :key="index2"><v-icon>{{ icon('substance') }}</v-icon>{{c.name}}</span><br />
        Files: <span v-for="(f, index2) in study.files" :key="index2"><a :href="f" :title="f"><v-icon>{{ icon('file') }}</v-icon></a>&nbsp;</span><br />
    </div>
</template>

<script>
    export default {
        name: "StudyInfo",
        props: {
            study: {
                type: Object,
                required: true,
            }
        }
    }
</script>

<style scoped>

</style>