<template>
    <span id="file-chip" class="text-xs-center" @mouseover="showText=true" @mouseleave="showText=true">

        <a :href="backend+file" :title="backend+file">
            <v-chip>
                <v-icon small>{{ icon('file') }}</v-icon>
                <span v-show="showText">
                    <text-highlight :queries="search.split(/[ ,]+/)">&nbsp;{{name(file)}}</text-highlight>
                </span>
            </v-chip>
        </a>

        <!--
        <span v-if="!is_image(file)">

        <span v-else>
            <v-dialog scrollable>


            <v-btn slot="activator" fab dark small flat color="black"
                   :disabled="resource_url ? false : true" title="PDF">
                <v-icon dark>fas fa-file</v-icon>
            </v-btn>
                <v-card style="height: 800px;">
                    <embed :src="resource_url"  height="100%" width="100%"/>
                </v-card>
            </v-dialog>
        </span>
        </span>
        -->
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
            is_image(file){
                return (file.endsWith(".png") || file.endsWith(".jpg") || file.endsWith(".jpeg"));
            },
            is_data(file){
                return (file.endsWith(".csv") || file.endsWith(".tsv") || file.endsWith(".jpeg"));
            },
            is_spreadsheet(file){
                return (file.endsWith(".xlsx"));
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