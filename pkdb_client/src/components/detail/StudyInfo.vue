<template>
    <div class="study-info">
        <v-layout>
        <div class="attr-card">
            <span class="attr">Name</span>
            {{ study.name }}
        </div>
        <div class="attr-card">
            <span class="attr">Reference</span><br />
            <a v-if="study.reference" :href="study.reference" :title="study.reference"><v-icon>{{ icon('reference') }}</v-icon></a>
        </div>
        <div class="attr-card">
            <span class="attr">Creator</span><br />
            <user-avatar :user="study.creator"/>
        </div>
        <div class="attr-card">
            <span class="attr">Curators</span><br />
            <user-avatar v-for="c in study.curators" :key="c.pk" :user="c"/>
        </div>
        <div class="attr-card-no-width">
            <span class="attr">Substances</span><br />
            <span v-for="c in study.substances" :key="c.pk"><v-icon>{{ icon('substance') }}</v-icon>{{c.name}}</span>
        </div>
        <div class="attr-card-no-width">
            <span class="attr">Files</span><br />
            <span v-for="f in study.files" :key="f"><a :href="f.pk" :title="f"><v-icon>{{ icon('file') }}</v-icon></a>&nbsp;</span>
        </div>
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
    .study-info {
        padding-top: 20px;
        height: 70px;
    }
</style>