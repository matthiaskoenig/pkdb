<template>
    <div id="references-table">
    <heading :count="data.count" :icon="icon('references')" title="References" :resource_url="resource_url"/>
    <v-card>
        <v-data-table
                :headers="headers"
                :items="data.entries"
                hide-actions
                class="elevation-1">
            <template slot="items" slot-scope="table">
                <td>
                    <link-button :to="'/references/'+ table.item.pk" :title="'Reference: '+table.item.pk" :icon="icon('reference')"/>
                    <json-button :resource_url="api + '/references_read/'+ table.item.pk +'/?format=json'"/>
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
    </div>
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
