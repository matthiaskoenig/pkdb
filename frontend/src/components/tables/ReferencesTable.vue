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
                    <link-button :to="'/references/'+ item.sid" :title="'Reference: '+item.name" :icon="icon('reference')"/>
                    <link-button v-if="item.study" :to="'/studies/'+ item.study.sid" :title="'Study: '+item.study.name" :icon="icon('study')"/>
                    <!--
                    <file-button v-if="item.pdf" :resource_url='backend+item.pdf' :title="item.pdf"/>
                    -->
                    <json-button :resource_url="api + 'references_elastic/'+ item.sid +'/'"/>

            </template>
            <template  v-slot:item.sid="{ item }">
                <text-highlight :queries="[search]">{{ item.sid }}</text-highlight>
            </template>
            <template  v-slot:item.pmid="{ item }">
                <a :href="'https://www.ncbi.nlm.nih.gov/pubmed/'+item.pmid"
                   target="_blank"><text-highlight :queries="[search]">{{ item.pmid }}</text-highlight></a>
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