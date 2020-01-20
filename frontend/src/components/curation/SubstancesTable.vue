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
                    <JsonButton :resource_url="api + 'substances/'+ item.url_slug+ '/?format=json' "/>
            </template>
           <template v-slot:item.sid="{ item }"><text-highlight :queries="search.split(/[ ,]+/)">{{item.sid}} </text-highlight> </template>
           <template v-slot:item.name="{ item }"><text-highlight :queries="search.split(/[ ,]+/)">{{item.name}} </text-highlight> </template>
           <template v-slot:item.mass="{ item }"><text-highlight :queries="search.split(/[ ,]+/)">{{item.mass}} </text-highlight> </template>
           <template v-slot:item.charge="{ item }"><text-highlight :queries="search.split(/[ ,]+/)">{{item.charge}}  </text-highlight> </template>
           <template v-slot:item.formula="{ item }"><text-highlight :queries="search.split(/[ ,]+/)">{{item.formula}} </text-highlight> </template>
           <template v-slot:item.derived="{ item }">
                <v-chip :disabled="true" color='green' v-if="item.derived" >
                    <v-icon small title="derived from parents">{{icon("success")}}</v-icon>
                </v-chip>
            </template>
           <template v-slot:item.description="{ item }"><text-highlight :queries="search.split(/[ ,]+/)">{{item.description}} </text-highlight> </template>
           <template v-slot:item.parents="{ item }">
                <ul>
                    <substance-chip v-for="parent in item.parents" :title="parent.sid" :key="parent"/>
                </ul>
            </template>
           <template v-slot:item.synonyms="{ item }">
                <ul>
                    <v-chip v-for="synonym in item.synonyms" :key="synonym">
                        {{synonym}}
                    </v-chip>
                </ul>
            </template>
           <template v-slot:item.annotations="{ item }">
                <ul>
                    <v-chip v-for="annotation in item.annotations" :key="annotation">
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
                    {text: 'Synonyms', value: 'synonyms'},
                    {text: 'Annotations', value: 'annotations',sortable: false},

                ]
            }
        }

    }
</script>

<style scoped></style>


