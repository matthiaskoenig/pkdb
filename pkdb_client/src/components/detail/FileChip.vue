<template>
    <div id="file-chip" class="text-xs-center">
        <a :href="backend+file" :title="backend+file">
            <v-chip color="orange">
                <v-icon>{{ icon('file') }}</v-icon>&nbsp;
                <text-highlight :queries="search.split(/[ ,]+/)">{{name(file)}}</text-highlight>
            </v-chip>
        </a>
    </div>
</template>

<script>
    import {lookup_icon} from "@/icons"

    export default {
        name: "FileChip",
        props: {
            file: String,
            search: {type:String, default:""},
        },
        methods: {
            icon(key) {
                return lookup_icon(key)
            },
            name(url) {
                return url.substr(url.lastIndexOf('/') + 1);
            }
        },
        computed: {
            backend() {
                return this.$store.state.django_domain;
            },

        },
    }
</script>

<style scoped>

</style>