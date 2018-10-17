<template>

    <v-card>
        <v-card-title>
            <v-toolbar id="heading-toolbar" color="secondary" dark>
                <Heading :count="count" :icon="icon('timecourses')" title="Timecourses" :resource_url="resource_url"/>
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
                    <LinkButton :to="'/timecourses/'+ table.item.pk" :title="'Timecourse: '+table.item.pk" :icon="icon('output')"/>
                    <JsonButton :resource_url="api + '/timecourses_read/'+ table.item.pk +'/?format=json'"/>
                </td>
                <td><text-highlight :queries="search.split(/[ ,]+/)">{{table.item.pktype }}</text-highlight></td>
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
                    <span v-for="(intervention_url, index2) in table.item.interventions" :key="index2">
                    <a :href="intervention_url" :title="intervention"><v-icon>{{ icon('intervention') }}</v-icon></a>&nbsp;
                        <get-data :resource_url="intervention_url">
                        <div slot-scope="data">
                            <text-highlight :queries="search.split(/[ ,]+/)">
                                {{ data.data.name }}
                            </text-highlight>
                        </div>
                    </get-data>
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
                <td>
                    <TimecoursePlot :timecourse="table.item"/>
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
    import TimecoursePlot from '../plots/TimecoursePlot'
    import GroupButton from '../lib/GroupButton'
    import IndividualButton from '../lib/IndividualButton'
    import SubstanceChip from "../detail/SubstanceChip"


    export default {
        name: "TimecoursesTable2",
        components:{
            GroupButton,
            IndividualButton,
            TimecoursePlot,
            SubstanceChip,

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
                    {text: 'Type', value: 'type'},
                    {text: 'Group', value: 'group'},
                    {text: 'Individual', value: 'individual'},
                    {text: 'Interventions', value: 'interventions',sortable: false},
                    {text: 'Tissue', value: 'tissue'},
                    {text: 'Substance', value: 'substance'},
                    {text: 'Timecourse', value: 'auc_end'},
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
                return this.$store.state.endpoints.api  + '/timecourses_elastic/?format=json&final=true'
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
                    + '/timecourses_elastic/?format=json&final=true'
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
