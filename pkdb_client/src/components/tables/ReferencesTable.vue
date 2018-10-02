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

<script>
    import Table from '@/components/tables/Table'

    export default {
        name: 'ReferencesTable',
        components: {
            Table
        },
        props: {
            data: Object,
            resource_url:String,
        }
    }
</script>

<style>
</style>