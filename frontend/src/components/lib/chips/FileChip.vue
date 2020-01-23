<template>
    <span id="file-chip" class="text-xs-center" @mouseover="showText=true" @mouseleave="showText=true">

        <a  @click.prevent="downloadItem(file_url)" :href="file_url" :title="file_url">
            <v-chip>
                <v-icon color="orange" v-if="filetype(file)=='image'" small>{{ faIcon('file_image') }}</v-icon>
                <v-icon color="blue" v-if="filetype(file)=='data'" small>{{ faIcon('file') }}</v-icon>
                <v-icon color="green" v-if="filetype(file)=='spreadsheet'" small>{{ faIcon('file_excel') }}</v-icon>
                <v-icon color="red" v-if="filetype(file)=='pdf'" small>{{ faIcon('file_pdf') }}</v-icon>
                <v-icon color="white" v-if="filetype(file)=='other'" small>{{ faIcon('file') }}</v-icon>
                &nbsp;
                <span v-show="showText">
                    <text-highlight :queries="search.split(/[ ,]+/)">&nbsp;{{ name(file) }}</text-highlight>
                </span>
            </v-chip>
        </a>
    </span>
</template>

<script>
    import {lookupIcon} from "@/icons"
    import axios from 'axios'

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
            downloadItem(url){
                if (localStorage.getItem('token'))
                { var headers = {Authorization :  'Token ' + localStorage.getItem('token')}}
                else {
                    headers = {}
                }
                axios.get(url,{ headers: headers, responseType: 'arraybuffer'})
                    .then(response => {
                        let url_data = window.URL.createObjectURL(new Blob([response.data]));
                        let link = document.createElement('a');
                        link.href = url_data;
                        link.setAttribute('download', this.name(url)); //or any other extension
                        document.body.appendChild(link);
                        link.click()

                    })
                    .catch((error)=>{
                        console.error(url);
                        console.error(error);
                    })
            },
            faIcon(key) {
                return lookupIcon(key)
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
            file_url() {
                if (this.file.startsWith(this.backend)){
                    return this.file
                }
                else{
                    return this.backend+this.file
                }
            },
        },
    }
</script>

<style scoped>

</style>