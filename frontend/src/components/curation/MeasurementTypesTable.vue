

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
            <template v-slot:item.buttons="{ item }">
                    <JsonButton :resource_url="api + 'measurement_types/'+ item.url_slug+ '/?format=json' "/>
            </template>
            <template v-slot:item.name="{ item }"> <text-highlight :queries="search.split(/[ ,]+/)">{{item.name}} </text-highlight> </template>
            <template v-slot:item.dtype="{ item }"><text-highlight :queries="search.split(/[ ,]+/)">{{item.dtype}} </text-highlight> </template>
            <template v-slot:item.description="{ item }"><text-highlight :queries="search.split(/[ ,]+/)">{{item.description}} </text-highlight> </template>
            <template v-slot:item.units="{ item }">
                <ul>
                    <v-chip v-for="unit in item.units" :key="unit">
                        {{unit}}
                    </v-chip>
                </ul>
            </template>
            <template v-slot:item.choices="{ item }">
                <ul>
                    <v-chip v-for="choice in item.choices" :key="choice.name">
                        {{choice}}
                    </v-chip>
                </ul>
            </template>
            <template v-slot:item.annotations="{ item }">
                <ul>
                    <v-chip v-for="annotation in item.annotations" :key="annotation.term">
                        {{annotation.collection}}:<b>{{annotation.term}}</b> | {{annotation.relation}}
                    </v-chip>
                </ul>
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
