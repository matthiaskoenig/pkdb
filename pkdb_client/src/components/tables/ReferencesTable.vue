<template>
    <Table :data="data" :resource_url="resource_url" title="References" icon="file-alt">
        <template slot="row" slot-scope="table">
            <md-table-cell md-label="Pk">
                <DetailButton title="Reference" icon="file-alt"/>{{ table.item.pk }}
            </md-table-cell>

            <md-table-cell md-label="Sid">
                <font-awesome-icon icon="file-alt"/>{{ table.item.sid }}
            </md-table-cell>
            <md-table-cell md-label="Pmid"><a :href="'https://www.ncbi.nlm.nih.gov/pubmed/'+table.item.pmid"
                                              target="_blank">{{ table.item.pmid }}</a></md-table-cell>
            <md-table-cell md-label="Name">{{ table.item.name }}</md-table-cell>
            <md-table-cell md-label="Title">{{ table.item.title }}</md-table-cell>
            <md-table-cell md-label="Journal">{{ table.item.journal }}</md-table-cell>
            <md-table-cell md-label="Date">{{table.item.date}}</md-table-cell>
            <md-table-cell md-label="Abstract">{{table.item.abstract}}</md-table-cell>
        </template>
    </Table>
</template>


<template>
    <v-card>
        <v-card-title>
            <Heading :count="data.count" :icon="icon('references')" title="References" :resource_url="resource_url"/>
        </v-card-title>

        <v-data-table
                :headers="headers"
                :items="data.entries"
                hide-actions
                class="elevation-1">
            <template slot="items" slot-scope="table">
                <td>
                    <LinkButton :to="'/references/'+ table.item.pk" :title="'Reference: '+table.item.pk" :icon="icon('reference')"/>
                    <JsonButton :resource_url="api + '/references_read/'+ table.item.pk +'/?format=json'"/>
                </td>
                <td>{{ table.item.sid }}</td>
                <td>
                    <a :href="'https://www.ncbi.nlm.nih.gov/pubmed/'+table.item.pmid"
                       target="_blank">{{ table.item.pmid }}</a>
                </td>
                <td>{{table.item.name}}</td>
                <td>{{table.item.title}}</td>
                <td>{{table.item.journal}}</td>
                <td>{{table.item.date}}</td>
                <td>{{table.item.abstract}}</td>
            </template>
        </v-data-table>
    </v-card>
</template>


<script>
    import {lookup_icon} from "@/icons"

    export default {
        name: 'ReferencesTable',
        props: {
            data: Object,
            resource_url: String,
        },
        data() {
            return {
                headers: [
                    {text: 'Sid', value: 'sid'},
                    {text: 'Pmid', value: 'pmid'},
                    {text: 'Name', value: 'name'},
                    {text: 'Title', value: 'title'},
                    {text: 'Journal', value: 'journal'},
                    {text: 'Date', value: 'date'},
                    {text: 'Abstract', value: 'abstract'},
                ],
            }
        },
        computed: {
            api() {
                return this.$store.state.endpoints.api;
            }
        },
        methods: {
            icon: function (key) {
                return lookup_icon(key)
            },
        }
    }
</script>
<style>


</style>
