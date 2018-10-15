

<template>

    <v-card>
        <v-card-title>
            <v-toolbar id="heading-toolbar" color="secondary" dark>
                <Heading :count="count" :icon="icon('references')" title="References" :resource_url="resource_url"/>
                <v-spacer></v-spacer>
                <v-text-field
                        v-model="search"
                        append-icon="fa-search"
                        label="Search"
                        single-line
                        hide-details
                >
                </v-text-field>
            </v-toolbar>

        </v-card-title>

        <v-data-table
                :headers="headers"
                :items="entries"
                :pagination.sync="pagination"
                :total-items="count"
                :loading="loading"
                class="elevation-1"
        >

            <template slot="items" slot-scope="table">
                <td>
                    <link-button :to="'/references/'+ table.item.pk" :title="'Reference: '+table.item.pk" :icon="icon('reference')"/>
                    <json-button :resource_url="api + '/references_read/'+ table.item.pk +'/?format=json'"/>
                </td>
                <td><text-highlight :queries="[search]">{{ table.item.sid }}</text-highlight></td>
                <td>
                    <a :href="'https://www.ncbi.nlm.nih.gov/pubmed/'+table.item.pmid"
                       target="_blank"><text-highlight :queries="[search]">{{ table.item.pmid }}</text-highlight></a>
                </td>
                <td> <text-highlight :queries="[search]">{{ table.item.name }}</text-highlight> </td>
                <td> <text-highlight :queries="[search]">{{table.item.title}}</text-highlight></td>
                <td> <text-highlight :queries="[search]">{{table.item.journal}}</text-highlight></td>
                <td> <text-highlight :queries="[search]">{{table.item.date}}</text-highlight></td>
                <td> <text-highlight :queries="[search]">{{table.item.abstract}}</text-highlight></td>
            </template>

            <template slot="no-data">
                <v-alert :value="true" color="error" icon="fas fa-exclamation">
                    Sorry, nothing to display here :(
                </v-alert>
            </template>

        </v-data-table>
    </v-card>
</template>

<script>
    import axios from 'axios'
    import {lookup_icon} from "@/icons"

    export default {
        name: "searchtable",
        data () {
                return {
                    count: 0,
                    entries: [],
                    loading: true,
                    search: '',
                    pagination: {},
                    rowsPerPageItems: [5, 10, 20, 50, 100],
                    headers: [
                        {text: '', value: 'buttons',sortable: false},
                        {text: 'Sid', value: 'sid'},
                        {text: 'Pmid', value: 'pmid'},
                        {text: 'Name', value: 'name'},
                        {text: 'Title', value: 'title'},
                        {text: 'Journal', value: 'journal'},
                        {text: 'Date', value: 'date'},
                        {text: 'Abstract', value: 'abstract'},
                    ]
                }
            },
            watch: {
                pagination: {
                    handler () {
                        this.getData()
                    },
                    deep: true
                },
                search: {
                    handler () {
                        this.getData();
                    },
                    deep: true
                }
            },
            mounted () {
                this.getData()
            },
            computed: {
                api() {
                    return this.$store.state.endpoints.api;

                },
                resource_url() {
                     return this.$store.state.endpoints.api  + '/references_elastic/?format=json'
                },
                descending() {
                    if(this.pagination.descending){
                        return "-";
                    }
                    else{
                        return ""
                    }
                }
            },

            methods: {
                icon: function (key) {
                    return lookup_icon(key)
                },
                getData() {

                    let url = this.$store.state.endpoints.api
                        + '/references_elastic/?format=json'
                        +'&page='+ this.pagination.page
                        +'&page_size='+ this.pagination.rowsPerPage
                        +'&ordering='+ this.descending+ this.pagination.sortBy;
                        if(this.search){
                            url += '&search='+ this.search
                        }

                    axios.get(url)
                        .then(res => {
                            this.entries = res.data.data.data;
                            this.count = res.data.data.count;
                        })
                        .catch(err => console.log(err.response.data))
                        .finally(() => this.loading = false);

                }
            }
        }
</script>

<style scoped>

</style>