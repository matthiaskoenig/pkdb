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
            update_details(){
                if (this.show_type){
                this.$store.state.show_type = this.show_type;
                this.$store.state.detail_info = this.detail_info;
                this.$store.state.display_detail = true }
                },
            faIcon(key) {
                return lookupIcon(key)
            },
        }
    }
</script>

<style>
</style>