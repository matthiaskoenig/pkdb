<template>
    <span class="link-button">
        <v-btn fab
               x-small
               text
               :color="color"
               :to="to"
               :title="title"
               @click="update_details"
               :disabled="disabled"
        >
            <v-icon>{{ faIcon(icon) }}</v-icon>
        </v-btn>
    </span>
</template>

<script>
    import {lookupIcon} from "@/icons"
    import axios from 'axios'

    export default {
        computed:{
            disabled(){
                if (this.to | (this.detail_info & this.show_type)){
                    return true} else {
                    return false
                }
            }
        },
        name: "LinkButton",
        props: {
            show_type: {
                type: String,
            },
            sid: {
                type: String
            },
            detail_info: {
                type: Object,
            },
            to: {
                type: String,
            },
            title: {
                type: String,
                required: true
            },
            icon: {
                type: String,
                required: true
            },
            color: {
                type: String,
                default: "black"
            },
        },
        methods: {
            getStudy(sid) {
                // object is an InfoNode
                let url = `${this.$store.state.endpoints.api}studies/${sid}/?format=json`;

                // get data (FIXME: caching of InfoNodes in store)
                axios.get(url)
                    .then(response => {
                        this.$store.state.show_type = this.show_type;
                        this.$store.state.detail_info =  response.data;
                        this.$store.state.display_detail = true;
                    })
                    .catch(err => {
                        this.exists = false;
                        console.log(err)
                    })
                    .finally(() => this.loading = false);

            },
            update_details(){
                if (this.show_type){
                    if (this.sid){
                        this.getStudy(this.sid);
                    }else{
                        this.$store.state.show_type = this.show_type;
                        this.$store.state.detail_info = this.detail_info;
                        this.$store.state.display_detail = true;
                    }
                   }
                },
            faIcon(key) {
                return lookupIcon(key)
            },
        }
    }
</script>

<style>
</style>