

<template>
    <v-card>
        <table-toolbar :otype="otype" :count="count" :autofocus="autofocus" :url="url" @update="searchUpdate"/>
        <v-data-table
                :headers="headers"
                :items="entries"
                :options.sync="options"
                :server-items-length="count"
                :loading="loading"
                :class="table_class"
        >
            <template slot="items" slot-scope="table">
                <td>
                    <JsonButton :resource_url="api + 'measurement_types/'+ table.item.url_slug+ '/?format=json' "/>
                </td>
                <td><text-highlight :queries="search.split(/[ ,]+/)">{{table.item.name}} </text-highlight> </td>
                <td><text-highlight :queries="search.split(/[ ,]+/)">{{table.item.dtype}} </text-highlight> </td>
                <td><text-highlight :queries="search.split(/[ ,]+/)">{{table.item.description}} </text-highlight> </td>
                <td>
                    <ul>
                        <v-chip v-for="unit in table.item.units" :key="unit">
                            {{unit}}
                        </v-chip>
                    </ul>
                </td>
                <td>
                    <ul>
                        <v-chip v-for="choice in table.item.choices" :key="choice">
                            {{choice}}
                        </v-chip>
                    </ul>
                </td>
                <td>
                    <ul>
                        <v-chip v-for="annotation in table.item.annotations" :key="annotation">
                            {{annotation.collection}}:<b>{{annotation.term}}</b> | {{annotation.relation}}
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
        name: "MeasurementTypesTable",
        components: {
            NoData,
            TableToolbar,
        },
        mixins: [searchTableMixin, UrlMixin],
        data () {
            return {
                otype: "measurement_types",
                otype_single: "measurement_type",
                headers: [
                    {text: '', value: 'buttons',sortable: false},
                    {text: 'Name', value: 'name'},
                    {text: 'Data Type', value: 'dtype'},
                    {text: 'Description', value: 'description'},
                    {text: 'Units', value: 'units'},
                    {text: 'Choices', value: 'choices'},
                    {text: 'Annotations', value: 'annotations',sortable: false},

                ]
            }
        }

    }
</script>

<style scoped></style>
