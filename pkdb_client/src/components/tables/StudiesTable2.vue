

<template>

    <v-card>
        <v-card-title>
            <v-toolbar id="heading-toolbar" color="secondary" dark>
                <Heading :count="count" :icon="icon('study')" title="Studies" :resource_url="resource_url"/>
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
                    <LinkButton :to="'/studies/'+ table.item.pk" :title="'Study: '+table.item.pk" :icon="icon('study')"/>
                    <JsonButton :resource_url="api + '/studies_read/'+ table.item.pk +'/?format=json'"/>
                </td>
                <td><text-highlight :queries="search.split(/[ ,]+/)"> {{ table.item.name }} </text-highlight></td>

                <td><a v-if="table.item.reference" :href="table.item.reference" :title="table.item.reference">
                    <v-icon>{{ icon('reference') }}</v-icon>

                </a>
                </td>
                <td>
                    <UserAvatar :user="table.item.creator" :search="search"/>
                </td>
                <td>
                    <span v-for="(c, index2) in table.item.curators" :key="index2"><user-avatar :user="c" :search="search"/></span>
                </td>
                <td>
                    <span v-for="(c, index2) in table.item.substances" :key="index2"><substance-chip :title="c" :search="search"/></span>
                </td>
                <td>
                    <v-container fluid grid-list-md>
                        <v-data-iterator  :items="table.item.files"
                                          content-tag="v-layout"
                                          wrap row>
                            <span slot="item" slot-scope="props" xs12 sm6  md4 lg3>
                               <file-chip  :file="props.item" :search="search"/>
                            </span>
                        </v-data-iterator>
                    </v-container>
                </td>
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
    import SubstanceChip from "../detail/SubstanceChip"
    import FileChip from "../detail/FileChip"


    export default {
        name: "StudiesTable2",
        components: {
            SubstanceChip: SubstanceChip,
            FileChip:FileChip,
        },
        data () {
                return {
                    count: 0,
                    entries: [],
                    loading: true,
                    search: '',
                    pagination: {},
                    rowsPerPageItems: [5, 10, 20, 50, 100],
                    headers: [
                        //{text: 'Study', value: 'study'},
                        {text: '', value: 'buttons',sortable: false},
                        {text: 'Name', value: 'name'},
                        {text: 'Reference', value: 'reference'},
                        {text: 'Creator', value: 'creator'},
                        {text: 'Curators', value: 'curators',sortable: false},
                        {text: 'Substances', value: 'substances',sortable: false},
                        {text: 'Files', value: 'files',sortable: false},

                    ],
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
                    return this.$store.state.endpoints.api  +  '/studies_elastic/?format=json'
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
                        + '/studies_elastic/?format=json'
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
    .highlight {
        font-weight: bold;
    }
</style>