<template>
    <v-card>
        <table-toolbar :otype="otype" :count="count" :autofocus="autofocus" :url="url" />
        <v-data-table
                :headers="headers"
                :items="entries"
                :options.sync="options"
                :server-items-length="count"
                :loading="loading"
                :class="table_class"
        >
            <template v-slot:item.buttons="{ item }">
                <JsonButton :resource_url="api + 'routes/'+ item.url_slug+ '/?format=json' "/>
            </template>
            <template v-slot:item.sid="{ item }">{{item.sid}}</template>
            <template v-slot:item.name="{ item }">{{item.name}}</template>
            <template v-slot:item.creator="{ item }">{{item.creator}}</template>
            <template v-slot:item.description="{ item }">{{item.description}}</template>
            <template v-slot:item.synonyms="{ item }">
                <ul>
                    <v-chip v-for="synonym in item.synonyms" :key="synonym">
                        {{synonym}}
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
        name: "RoutesTable",
        components: {
            NoData,
            TableToolbar,
        },
        mixins: [searchTableMixin, UrlMixin],
        data () {
            return {
                otype: "routes",
                otype_single: "routes",
                headers: [
                    {text: '', value: 'buttons',sortable: false},
                    {text: 'Sid', value: 'sid'},
                    {text: 'Name', value: 'name'},
                    {text: 'Creator', value: 'creator'},
                    {text: 'Description', value: 'description'},
                    {text: 'Synonyms', value: 'synonyms'},
                    {text: 'Annotations', value: 'annotations',sortable: false},

                ]
            }
        },
        computed:
            {
                resource_url() {
                    return this.$store.state.endpoints.api  + this.otype + '/?format=json'
                }
            }

    }
</script>

<style scoped></style>
