<template>
    <div>
        <Table  :resource="resource" :api="api" :resource_url="resource_url" :comments="comments" :descriptions="descriptions">
            <template slot="title">
                <font-awesome-icon icon="chart-line" /> Timecourses
            </template>
            <template slot="tableRow" slot-scope="table">

                <md-table-cell md-label="Pk"> <font-awesome-icon icon="chart-line" /> {{ table.item.pk }} </md-table-cell>
                <md-table-cell md-label="PK Type" >{{ table.item.pktype }}</md-table-cell>
                <md-table-cell md-label="Group" ><a v-if="table.item.group" :href="table.item.group" :title="table.item.group"><font-awesome-icon icon="users" /></a></md-table-cell>
                <md-table-cell md-label="Individual"><a v-if="table.item.individual" :href="table.item.individual" :title="table.item.individual"><font-awesome-icon icon="user" /></a></md-table-cell>
                <md-table-cell md-label="Interventions"><span v-for="(intervention, index2) in table.item.interventions" :key="index2">
                        <a :href="intervention" :title="intervention"><font-awesome-icon icon="capsules" /></a>&nbsp;</span></md-table-cell>
                <md-table-cell md-label="Tissue">{{table.item.tissue}}</md-table-cell>
                <md-table-cell md-label="Substance"><a v-if="table.item.substance" :href="table.item.substance" :title="table.item.substance"><font-awesome-icon icon="tablets" /></a></md-table-cell>

                <!--
                <md-table-cell md-label="Time"> {{table.item.time}} </md-table-cell>
                <md-table-cell md-label="Time Unit"> {{ table.item.time_unit }} </md-table-cell>
                <md-table-cell md-label="Unit"> {{table.item.unit}} </md-table-cell>
                <md-table-cell md-label="Value"> {{ table.item.value }} </md-table-cell>
                <md-table-cell md-label="Mean"> {{ table.item.mean }}</md-table-cell>
                <md-table-cell md-label="Median"> {{ table.item.median }}</md-table-cell>
                <md-table-cell md-label="Min">{{ table.item.min }}</md-table-cell>
                <md-table-cell md-label="Max">{{ table.item.max }}</md-table-cell>
                <md-table-cell md-label="Sd">{{ table.item.sd }}</md-table-cell>
                <md-table-cell md-label="Se">{{ table.item.se }}</md-table-cell>
                <md-table-cell md-label="Cv">{{ table.item.cv }}</md-table-cell>
                -->
                <md-table-cell md-label="Timecourse"><TimecourseSmall :timecourse="table.item"/></md-table-cell>
            </template>
        </Table>
    </div>
</template>

<script>

    import Table from '@/components/tables/Table'
    import TimecourseSmall from '@/components/TimecourseSmall'

export default {
    name: 'TimecoursesTable',
    components: {
        TimecourseSmall: TimecourseSmall,
        Table: Table,

    },
    props: {
        resource: Object,
        api:String,
        descriptions:Array,
        comments:Array,
        resource_url:String,
    }
}
</script>

<style>
</style>