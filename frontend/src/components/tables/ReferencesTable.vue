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
                    <link-button :to="'/references/'+ table.item.sid" :title="'Reference: '+table.item.name" :icon="icon('reference')"/>
                    <link-button v-if="table.item.study" :to="'/studies/'+ table.item.study.sid" :title="'Study: '+table.item.study.name" :icon="icon('study')"/>
                    <!--
                    <file-button v-if="table.item.pdf" :resource_url='backend+table.item.pdf' :title="table.item.pdf"/>
                    -->
                    <json-button :resource_url="api + '/references_elastic/'+ table.item.sid +'/'"/>

                </td>
                <td><text-highlight :queries="[search]">{{ table.item.sid }}</text-highlight></td>
                <td>
                    <a :href="'https://www.ncbi.nlm.nih.gov/pubmed/'+table.item.pmid"
                       target="_blank"><text-highlight :queries="[search]">{{ table.item.pmid }}</text-highlight></a>
                </td>
                <td> <text-highlight :queries="[search]">{{ table.item.name }}</text-highlight> </td>
                <td> <text-highlight :queries="[search]">{{table.item.title}}</text-highlight></td>
                <td> <text-highlight :queries="[search]">{{table.item.journal}}</text-highlight></td>
                <td> <text-highlight :queries="[search]">{{table.item.date}}</text-highlight></td>
                <td> <text-highlight :queries="[search]">{{table.item.abstract}}</text-highlight></td>
            </template>
            <no-data/>
        </v-data-table>
    </v-card>
</template>

<script>
    import {searchTableMixin} from "./mixins";
    import TableToolbar from './TableToolbar';
    import NoData from './NoData';

    export default {
        name: "ReferencesTable3",
        components: {
            NoData,
            TableToolbar,
        },
        mixins: [searchTableMixin],
        data () {
            return {
                otype: "references",
                otype_single: "reference",
                headers: [
                    {text: '', value: 'buttons',sortable: false},
                    {text: 'Sid', value: 'sid'},
                    {text: 'Pmid', value: 'pmid'},
                    {text: 'Name', value: 'name'},
                    {text: 'Title', value: 'title'},
                    {text: 'Journal', value: 'journal'},
                    {text: 'Date', value: 'date'},
                    {text: 'Abstract', value: 'abstract'},
                ]
            }
        },
    }
</script>

<style scoped></style>