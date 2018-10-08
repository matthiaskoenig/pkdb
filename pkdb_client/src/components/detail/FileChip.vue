<template>
    <div id="file-chip" class="text-xs-center">
        <a :href="file.file" :title="file.file"><v-chip> <v-icon>{{ icon('file') }}</v-icon>{{name(file.file)}}</v-chip> </a>
    </div>
</template>

<script>
    import {lookup_icon} from "@/icons"
    export default {
        name: "FileChip",
        props: {
            file : Object,
        },
        methods: {
            icon(key) {
                return lookup_icon(key)
            },
                name(url){return url.substr(url.lastIndexOf('/') + 1);}
        }
    }
</script>

<style scoped>

</style>