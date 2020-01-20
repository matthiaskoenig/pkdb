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
            <template v-slot:item="table">
            <td>
                    <JsonButton :resource_url="api + 'routes/'+ table.item.url_slug+ '/?format=json' "/>
                </td>
                <td>{{table.item.sid}}</td>
                <td>{{table.item.name}}</td>
                <td>{{table.item.creator}}</td>
                <td>{{table.item.description}}</td>
                <td>
                    <ul>
                        <v-chip v-for="synonym in table.item.synonyms" :key="synonym">
                            {{synonym}}
                        </v-chip>
                    </ul>

                </td>
                <td>

                    <ul>
                        <v-chip v-for="annotation in table.item.annotations" :key="annotation.term">
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
