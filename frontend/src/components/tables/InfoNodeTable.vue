

<template>

    <v-card>

        <table-toolbar :otype="otype" :count="count" :autofocus="autofocus" :url="url" @update="searchUpdate"/>
        <v-col class="d-flex" cols="12" sm="6">
            <v-select
                    :items="ntypes"
                    label="Solo field"
                    v-model="ntype"
                    dense
                    solo
            ></v-select>
        </v-col>
        <v-data-table
                :headers="headers"
                :items="entries"
                :options.sync="options"
                :server-items-length="count"
                :loading="loading"
                :class="table_class"
                :footer-props="footer_options"
        >
            <template v-slot:item.buttons="{ item }">
                <JsonButton :resource_url="api + 'info_nodes/'+ item.url_slug+ '/?format=json' "/>
            </template>
            <template v-slot:item.sid="{ item }"> <text-highlight :queries="search.split(/[ ,]+/)">{{item.sid}} </text-highlight> </template>
            <template v-slot:item.name="{ item }"> <text-highlight :queries="search.split(/[ ,]+/)">{{item.name}} </text-highlight> </template>
            <template v-slot:item.ntype="{ item }"><text-highlight :queries="search.split(/[ ,]+/)">{{item.ntype}} </text-highlight> </template>
            <template v-slot:item.dtype="{ item }"><text-highlight :queries="search.split(/[ ,]+/)">{{item.dtype}} </text-highlight> </template>
            <template v-slot:item.description="{ item }"><text-highlight :queries="search.split(/[ ,]+/)">{{item.description}} </text-highlight> </template>
            <template v-slot:item.synonyms="{ item }">
                <ul>
                    <v-chip v-for="synonym in item.synonyms" :key="synonym.pk">
                        {{synonym}}
                    </v-chip>
                </ul>
            </template>
            <template v-slot:item.parents="{ item }">
                 <span v-for="(parents, index2) in item.parents" :key="index2">
                    <object-chip :object="parents"
                                 otype="info_node"
                                 :search="search"
                    /><br />
                </span>
            </template>
            <template v-slot:item.annotations="{ item }">
                <ul>
                    <v-chip v-for="annotation in item.annotations" :key="annotation.term">
                        {{annotation.collection}}:<b>{{annotation.term}}</b> | {{annotation.relation}}
                    </v-chip>
                </ul>
            </template>

            <template v-slot:item.extras="{ item }">
                <ul v-if="item.ntype==='measurement_type'">

                    <span v-if="item.measurement_type.units.length > 0" >
                        Units:
                     <v-chip v-for="unit in item.measurement_type.units" :key="unit">
                        {{unit}}
                    </v-chip>
                    </span >

                    <span v-if="item.measurement_type.choices.length > 0" >
                        Choices:
                    <v-chip v-for="choice in item.measurement_type.choices" :key="choice">
                        <text-highlight :queries="search.split(/[ ,]+/)">
                            {{choice}}
                        </text-highlight>
                    </v-chip>
                    </span >

                </ul>

                <span v-if="item.ntype==='substance'">
                    <text-highlight :queries="search.split(/[ ,]+/)"> Mass: {{item.substance.mass}} </text-highlight>
                    <text-highlight :queries="search.split(/[ ,]+/)"> Charge: {{item.substance.charge}} </text-highlight>
                    <text-highlight :queries="search.split(/[ ,]+/)"> Formula: {{item.substance.formula}} </text-highlight>
                    <text-highlight :queries="search.split(/[ ,]+/)"> Derived: {{item.substance.derived}} </text-highlight>
                </span>

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
        name: "InfoNodeTable",
        components: {
            NoData,
            TableToolbar,
        },
        mixins: [searchTableMixin, UrlMixin],
        data () {
            return {
                otype: "info_nodes",
                ntypes:["all", "info_node", "choice","measurement_type","application",  "tissue", "method", "route", "form", "substance"],
                otype_single: "info_nodes",
                headers: [
                    {text: '', value: 'buttons',sortable: false},
                    {text: 'Sid', value: 'sid'},
                    {text: 'Name', value: 'name'},
                    {text: 'Node Type', value: 'ntype'},
                    {text: 'Data Type', value: 'dtype'},
                    {text: 'Description', value: 'description'},
                    {text: 'Synonyms', value: 'synonyms'},
                    {text: 'Parents', value: 'parents'},
                    {text: 'Annotations', value: 'annotations',sortable: false},
                    {text: 'Extra', value: "extras"},




                ]
            }
        }

    }
</script>

<style scoped></style>
