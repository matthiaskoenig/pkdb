<template>
    <Table :data="data" :resource_url="resource_url" title="Interventions" icon="capsules">
        <template slot="row" slot-scope="table">
            <md-table-cell md-label="Pk"><font-awesome-icon icon="capsules" />{{ table.item.pk }}</md-table-cell>
            <md-table-cell md-label="Name" >{{table.item.name }}</md-table-cell>
            <md-table-cell md-label="Category" >{{table.item.category }}</md-table-cell>
            <md-table-cell md-label="Choice">{{table.item.choice }}</md-table-cell>
            <md-table-cell md-label="Route">{{table.item.route }}</md-table-cell>
            <md-table-cell md-label="Form">{{table.item.form}}</md-table-cell>
            <md-table-cell md-label="Application">{{table.item.application}}</md-table-cell>
            <md-table-cell md-label="Substance"><a v-if="table.item.substance" :href="table.item.substance" :title="table.item.substance"><font-awesome-icon icon="tablets" /></a></md-table-cell>
            <md-table-cell md-label="Time"> {{table.item.time}} </md-table-cell>
            <md-table-cell md-label="Time Unit"> {{table.item.time_unit }} </md-table-cell>
            <md-table-cell md-label="Unit"> {{table.item.unit}} </md-table-cell>
            <md-table-cell md-label="Value"> {{table.item.value }} </md-table-cell>
            <md-table-cell md-label="Mean"> {{table.item.mean }}</md-table-cell>
            <md-table-cell md-label="Median"> {{table.item.median }}</md-table-cell>
            <md-table-cell md-label="Min">{{table.item.min }}</md-table-cell>
            <md-table-cell md-label="Max">{{table.item.max }}</md-table-cell>
            <md-table-cell md-label="Sd">{{table.item.sd }}</md-table-cell>
            <md-table-cell md-label="Se">{{table.item.se }}</md-table-cell>
            <md-table-cell md-label="Cv">{{table.item.cv }}</md-table-cell>
        </template>
    </Table>
</template>

<script>
    import Table from '@/components/tables/Table';

    export default {
    name: 'InterventionsTable',
    components: {
        Table: Table
    },
    props: {
        data: Object,
        resource_url: String,
    },
}
</script>

<style>
</style>