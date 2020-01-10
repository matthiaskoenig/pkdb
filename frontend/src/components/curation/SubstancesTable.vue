<template>
    <v-card>
        <table-toolbar :otype="otype" :count="count" :autofocus="autofocus" :url="url" @update="searchUpdate"/>
        <v-data-table
                :headers="headers"
                :items="entries"
                :pagination.sync="pagination"
                :total-items="count"
                :loading="loading"
                :class="table_class"
        >
            <template slot="items" slot-scope="table">
                <td>
                    <JsonButton :resource_url="api + 'substances/'+ table.item.url_slug+ '/?format=json' "/>
                </td>
                <td><text-highlight :queries="search.split(/[ ,]+/)">{{table.item.sid}} </text-highlight> </td>
                <td><text-highlight :queries="search.split(/[ ,]+/)">{{table.item.name}} </text-highlight> </td>
                <td><text-highlight :queries="search.split(/[ ,]+/)">{{table.item.mass}} </text-highlight> </td>
                <td><text-highlight :queries="search.split(/[ ,]+/)">{{table.item.charge}}  </text-highlight> </td>
                <td><text-highlight :queries="search.split(/[ ,]+/)">{{table.item.formula}} </text-highlight> </td>
                <td>
                    <v-chip :disabled="true" color='green' v-if="table.item.derived" >
                        <v-icon small title="derived from parents">{{icon("success")}}</v-icon>
                    </v-chip>
                </td>
                <td><text-highlight :queries="search.split(/[ ,]+/)">{{table.item.description}} </text-highlight> </td>
                <td>

                    <ul>
                        <substance-chip v-for="parent in table.item.parents" :title="parent.sid"/>
                    </ul>

                </td>

                <td>

                    <ul>
                        <v-chip v-for="annotation in table.item.annotations">
                            {{annotation.collection}}:<b>{{annotation.term}}</b>  |  {{annotation.relation}}
                        </v-chip>
                    </ul>

                </td>

            </template>
            <no-data/>
        </v-data-table>
    </v-card>
</template>

<script>
    import {searchTableMixin, UrlMixin} from "../tables/mixins";
    import TableToolbar from '../tables/TableToolbar';
    import NoData from '../tables/NoData';

    export default {
        name: "SubstancesTable",
        components: {
            NoData,
            TableToolbar,
        },
        mixins: [searchTableMixin, UrlMixin],
        data () {
            return {
                otype: "substances",
                otype_single: "substances",
                headers: [
                    {text: '', value: 'buttons',sortable: false},
                    {text: 'Sid', value: 'sid'},
                    {text: 'Name', value: 'name'},
                    {text: 'Mass', value: 'mass'},
                    {text: 'Charge', value: 'charge'},
                    {text: 'Formula', value: 'formula'},
                    {text: 'Derived', value: 'derived'},
                    {text: 'Description', value: 'description'},
                    {text: 'Parents', value: 'parents',sortable: false},
                    {text: 'Annotations', value: 'annotations',sortable: false},

                ]
            }
        }

    }
</script>

<style scoped></style>


