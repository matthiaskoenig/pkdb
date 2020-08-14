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
                :footer-props="footer_options"
        >
            <template v-slot:item.buttons="{ item }">
                    <LinkButton v-if="item.study"
                                :to="'/studies/'+ item.study.sid"
                                :title="'Study: '+item.study.name"
                                icon="study"
                    />
                    <link-button :to="'/references/'+ item.sid"
                                 :title="'Reference: '+item.name"
                                 icon="reference"
                    />
                    <json-button :resource_url="api + 'references/'+ item.sid +'/'"/>
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
                    {text: 'Sid', value: 'sid',sortable: false},
                    {text: 'Pmid', value: 'pmid',sortable: false},
                    {text: 'Name', value: 'name',sortable: false},
                    {text: 'Title', value: 'title',sortable: false},
                    {text: 'Journal', value: 'journal',sortable: false},
                    {text: 'Date', value: 'date',sortable: false},
                    {text: 'Abstract', value: 'abstract',sortable: false},
                ]
            }
        },
    }
</script>

<style scoped></style>