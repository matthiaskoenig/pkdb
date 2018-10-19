<template>

    <v-card>
        <v-card-title>
            <v-toolbar id="heading-toolbar" color="secondary" dark>
                <Heading :count="count" :icon="icon('individuals')" title="Individuals" :resource_url="resource_url"/>
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
                    <link-button :to="'/individuals/'+ table.item.pk" :title="'Individual: '+table.item.pk" :icon="icon('individual')"/>
                    <json-button :resource_url="api + '/individuals_read/'+ table.item.pk +'/?format=json'"/>
                </td>
                <td>
                    <individual-info :individual="table.item"/>
                </td>

                <td>
                     <v-layout wrap>
                            <span v-for="item in table.item.characteristica_all_final" :key="item">
                                <characteristica-card :data="item" :resource_url="get_characterica_url(ids(table.item.characteristica_all_final))" />
                            </span>
                     </v-layout>

                </td>
            </template>

        </v-data-table>
    </v-card>
</template>

<script>
    import axios from 'axios'
    import {lookup_icon} from "@/icons"
    import CharacteristicaCard from '../detail/CharacteristicaCard'


    export default {
        name: "IndividualsTable2",
        components:{
            CharacteristicaCard,

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
                    {text: 'Info', value: 'info'},
                    {text: 'Characteristica', value: 'characteristica'},
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
                return this.$store.state.endpoints.api  + '/individuals_elastic/?format=json'
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
            ids(array_of_obj){
                return array_of_obj.map(i => i.pk)
            },

            get_characterica_url(ids){
                return this.$store.state.endpoints.api + '/characteristica_elastic/?ids='+ ids.join('__')+'&ordering=-count'
            },

            icon: function (key) {
                return lookup_icon(key)
            },

            getData() {

                let url = this.$store.state.endpoints.api
                    + '/individuals_elastic/?format=json'
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
