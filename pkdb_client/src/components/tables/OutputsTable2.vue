<template>

    <v-card>
        <v-card-title>
            <v-toolbar id="heading-toolbar" color="secondary" dark>
                <Heading :count="count" :icon="icon('outputs')" title="Outputs" :resource_url="resource_url"/>
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
                    <LinkButton :to="'/outputs/'+ table.item.pk" :title="'Output: '+table.item.pk" :icon="icon('output')"/>
                    <JsonButton :resource_url="api + '/outputs_read/'+ table.item.pk +'/?format=json'"/>
                </td>
                <td><text-highlight :queries="search.split(/[ ,]+/)">{{table.item.pktype }} </text-highlight> </td>
                <td>
                    <get-data v-if="table.item.group" :resource_url="table.item.group">
                        <div slot-scope="data">
                            <group-button :group="data.data" />
                            <text-highlight :queries="search.split(/[ ,]+/)">{{ data.data.name }}</text-highlight>
                        </div>
                    </get-data>
                </td>
                <td>
                    <get-data v-if="table.item.individual" :resource_url="table.item.individual">
                        <div slot-scope="data">
                            <individual-button :individual="data.data" />
                            <text-highlight :queries="search.split(/[ ,]+/)">{{ data.data.name }}</text-highlight>
                        </div>
                    </get-data>
                <td>
                    <span v-if="table.item.interventions" v-for="(intervention_url, index2) in table.item.interventions" :key="index2">
                        <get-data :resource_url="intervention_url">
                        <div slot-scope="data">
                            <a :href="intervention_url" :title="data.data.name"><v-icon>{{ icon('intervention') }}</v-icon></a>
                            <text-highlight :queries="search.split(/[ ,]+/)">
                            {{ data.data.name }}
                            </text-highlight>
                        </div>
                        </get-data>&nbsp;
                    </span>
                </td>
                <td>
                    <text-highlight :queries="search.split(/[ ,]+/)">
                        {{table.item.tissue}}
                    </text-highlight>
                </td>
                <td>
                    <substance-chip :substance="table.item.substance.name" :search="search"/>
                </td>
                <td>{{table.item.time}} <span v-if="table.item.time_unit">[{{table.item.time_unit }}]</span></td>
                <td><characteristica-card :data="table.item"/></td>
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
    import GroupButton from '../lib/GroupButton'
    import IndividualButton from '../lib/IndividualButton'
    import CharacteristicaCard from '../detail/CharacteristicaCard'
    import SubstanceChip from "../detail/SubstanceChip"


    export default {
        name: "OutputsTable2",
        components:{
            GroupButton,
            IndividualButton,
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
                    {text: '', value: 'buttons',sortable: false},
                    {text: 'Type', value: 'pktype'},
                    {text: 'Group', value: 'group'},
                    {text: 'Individual', value: 'individual'},
                    {text: 'Interventions', value: 'interventions',sortable: false},
                    {text: 'Tissue', value: 'tissue'},
                    {text: 'Substance', value: 'substance'},
                    {text: 'Time', value: 'time'},
                    {text: 'Value', value: 'value'},
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
                return this.$store.state.endpoints.api  + '/outputs_elastic/?format=json&final=true'
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
                    + '/outputs_elastic/?format=json'
                    +'&final=true'
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
