<template>

    <v-card>
        <v-card-title>
            <v-toolbar id="heading-toolbar" color="secondary" dark>
                <heading :count="count"
                         :icon="icon('interventions')"
                         title="Interventions"
                         :resource_url="url"
                />
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
                    <LinkButton :to="'/interventions/'+ table.item.pk" :title="'Group: '+table.item.pk" :icon="icon('intervention')"/>
                    <JsonButton :resource_url="api + '/interventions_read/'+ table.item.pk +'/?format=json'"/>
                </td>
                <td>
                    <text-highlight :queries="[search]">{{table.item.name }}</text-highlight>
                </td>
                <td>
                    <text-highlight :queries="[search]"> {{table.item.category }}</text-highlight>
                </td>
                <td>
                    <text-highlight :queries="[search]"> {{table.item.choice }}</text-highlight>
                </td>
                <td>
                    <text-highlight :queries="[search]"> {{table.item.application }}</text-highlight><br/>
                    <text-highlight :queries="[search]">{{table.item.time}}</text-highlight> <span v-if="table.item.time_unit"> [<text-highlight :queries="[search]">{{table.item.time_unit }}</text-highlight>]</span><br />
                    <text-highlight :queries="[search]">{{ table.item.route }}</text-highlight> <br/>
                    <text-highlight :queries="[search]">{{table.item.form}}</text-highlight>
                </td>
                <td>
                    <substance-chip v-if="table.item.substance" :title="table.item.substance.name" :search="search"/>
                </td>
                <td><characteristica-card :data="table.item" /></td>
            </template>

            <template slot="no-data">
                <v-alert :value="true" color="warning" icon="fas fa-exclamation">
                    Sorry, nothing to display here :(
                </v-alert>
            </template>

        </v-data-table>
    </v-card>
</template>

<script>
    import axios from 'axios'
    import {lookup_icon} from "@/icons"
    import CharacteristicaCard from '../detail/CharacteristicaCard'
    import SubstanceChip from "../detail/SubstanceChip"

    export default {
        name: "InterventionsTable",
        components: {
            CharacteristicaCard,
            SubstanceChip
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
                    //{text: 'Intervention', value: 'intervention'},
                    {text: '', value: 'buttons',sortable: false},
                    {text: 'Name', value: 'name'},
                    {text: 'Category', value: 'category'},
                    {text: 'Choice', value: 'choice'},
                    {text: 'Application', value: 'application'},
                    {text: 'Substance', value: 'substance'},
                    {text: 'Value', value: 'value'},
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
                return this.$store.state.endpoints.api  + '/interventions_elastic/?format=json'
            },
            url() {
                let url = this.resource_url
                    + '&page='+ this.pagination.page
                    + '&page_size='+ this.pagination.rowsPerPage
                    + '&ordering='+ this.descending+ this.pagination.sortBy;
                if(this.search){
                    url += '&search='+ this.search
                }
                return url
            },
            descending() {
                return (this.pagination.descending ? "-" : "");
            }
        },

        methods: {
            icon(key) {
                return lookup_icon(key)
            },

            getData() {
                axios.get(this.url)
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