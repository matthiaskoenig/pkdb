<template>
    <v-toolbar color="white">
        <v-toolbar-title>Substance Selection</v-toolbar-title>
        <v-autocomplete
                :loading="loading"
                :items="items"
                :search-input.sync="search"
                v-model="select"
                cache-items
                class="mx-3"
                flat
                hide-no-data
                hide-details
                label="What Substance are you searching?"
                solo-inverted
        ></v-autocomplete>
    </v-toolbar>
</template>
<script>
    import axios from 'axios';

    export default {
        name: 'autocomplete',

        data () {
            return {
                loading: false,
                items: [],
                search: null,
                select: null,
            }
        },
        //options with array without pagination
        watch: {
            search (val) {
                val && val !== this.select && this.querySelections(val)
            }
        },
        methods: {
            querySelections (v) {

                this.loading = true;
                // Simulated ajax query

                this.fetch_data(this.substanceSuggest());
                this.loading = false

            },

            fetch_data(url){
                axios.get(url)
                    .then(response => {

                        this.items =  response.data.results.map(x => x.name) ;

                        this.loaded = true;
                    })
                    .catch((error)=>{
                        this.items = null;
                        console.error(this.resource_url);
                        console.error(error);
                    })
            },
            substanceSuggest(){
                return this.api + "substances/";

            },
        },
        computed:{
            api() {
                return this.$store.state.endpoints.api;
            }}}




</script>