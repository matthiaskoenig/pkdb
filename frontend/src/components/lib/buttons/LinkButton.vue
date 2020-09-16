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
    import axios from 'axios'
    import {IconsMixin} from "../../../icons";
    import {StoreInteractionMixin} from "../../../storeInteraction";

    export default {
      mixins: [IconsMixin, StoreInteractionMixin],
        computed:{
            disabled(){
                if (this.to | (this.detail_info_input & this.show_type_input)){
                    return true} else {
                    return false
                }
            }
        },
        name: "LinkButton",
        props: {
          show_type_input: {
                type: String,
            },
            sid: {
                type: String
            },
            detail_info_input: {
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
                        this.show_type = this.show_type_input;
                        this.detail_info =  response.data;
                        this.display_detail = true;
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
                        this.show_type = this.show_type_input;
                        this.detail_info = this.detail_info_input;
                        this.display_detail = true;
                    }
                   }
            }

        }
    }
</script>

<style>
</style>