<template>
    <span id="file-chip" class="text-xs-center" @mouseover="showText=true" @mouseleave="showText=true">

        <a :href="backend+file" :title="backend+file">
            <v-chip dark>
                <v-icon color="orange" v-if="filetype(file)=='image'" small>{{ icon('file_image') }}</v-icon>
                <v-icon color="blue" v-if="filetype(file)=='data'" small>{{ icon('file') }}</v-icon>
                <v-icon color="green" v-if="filetype(file)=='spreadsheet'" small>{{ icon('file_excel') }}</v-icon>
                <v-icon color="red" v-if="filetype(file)=='pdf'" small>{{ icon('file_pdf') }}</v-icon>
                <v-icon color="white" v-if="filetype(file)=='other'" small>{{ icon('file') }}</v-icon>
                &nbsp;
                <span v-show="showText">
                    <text-highlight :queries="search.split(/[ ,]+/)">&nbsp;{{name(file)}}</text-highlight>
                </span>
            </v-chip>
        </a>
    </span>
</template>

<script>
    import {lookup_icon} from "@/icons"

    export default {
        name: "FileChip",
        props: {
            file: String,
            search: {type:String, default:""},
        },
        data () {
            return {
                showText: true
            }
        },
        methods: {
            icon(key) {
                return lookup_icon(key)
            },
            name(url) {
                return url.substr(url.lastIndexOf('/') + 1);
            },
            filetype(file){
                if (file.endsWith(".png")){
                    return "image"
                }
                if (file.endsWith(".jpg")){
                    return "image"
                }
                if (file.endsWith(".jpeg")){
                    return "image"
                }
                if (file.endsWith(".csv")){
                    return "data"
                }
                if (file.endsWith(".tsv")){
                    return "data"
                }
                if (file.endsWith(".ods")){
                    return "spreadsheet"
                }
                if (file.endsWith(".xlsx")){
                    return "spreadsheet"
                }
                if (file.endsWith(".pdf")){
                    return "pdf"
                }
                return "other"
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