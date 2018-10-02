<template>
    <Table :data="data" :resource_url="resource_url" title="Studies" icon="procedures">
        <template slot="row" slot-scope="table">
            <md-table-cell md-label="Pk">
                <DetailButton :to="'studies/'+ table.item.pk" title="Study" icon="procedures"/>{{ table.item.pk }}
            </md-table-cell>
            <md-table-cell md-label="Name">{{ table.item.name }}</md-table-cell>
            <md-table-cell md-label="Reference"><a v-if="table.item.reference" :href="table.item.reference" :title="table.item.reference"><font-awesome-icon icon="file-alt"/> </a></md-table-cell>
            <md-table-cell md-label="Creator">
                <UserAvatar :user="table.item.creator"/>
            </md-table-cell>
            <md-table-cell md-label="Curators">
                <span v-for="(c, index2) in table.item.curators" :key="index2"><UserAvatar :user="c"/></span>
            </md-table-cell>
            <md-table-cell md-label="Substances"><span v-for="(c, index2) in table.item.substances" :key="index2"><font-awesome-icon icon="tablets"/> {{c.name}}</span></md-table-cell>
            <md-table-cell md-label="Files"><span v-for="(f, index2) in table.item.files" :key="index2"><a :href="f" :title="f"><font-awesome-icon icon="file-medical"/></a>&nbsp;</span> </md-table-cell>
            <md-table-cell md-label="Groupset"><a v-if="table.item.groupset" :href="table.item.groupset" :title="table.item.groupset"><font-awesome-icon icon="users"/></a></md-table-cell>
            <md-table-cell md-label="Individualset"><a v-if="table.item.individualset" :href="table.item.individualset" :title="table.item.individualset"><font-awesome-icon icon="user"/></a></md-table-cell>
            <md-table-cell md-label="Interventionset"><a v-if="table.item.interventionset" :href="table.item.interventionset" :title="table.item.interventionset"><font-awesome-icon icon="capsules"/></a></md-table-cell>
            <md-table-cell md-label="Outputset"><a v-if="table.item.outputset" :href="table.item.outputset" :title="table.item.outputset"> <font-awesome-icon icon="chart-bar"/></a></md-table-cell>
            <md-table-cell md-label="Design">{{ table.item.design }}</md-table-cell>
            <md-table-cell md-label="Keywords"><span v-for="(c, index2) in table.item.keywords" :key="index2">
                <a :href="c" :title="c"><font-awesome-icon icon="tablets"/></a>&nbsp;</span>
            </md-table-cell>
        </template>
    </Table>
</template>

<script>
    import Table from '@/components/tables/Table';

    export default {
        name: 'StudiesTable',
        components: {
            Table: Table
        },
        props: {
            data: Object,
            resource_url: String,
        },
    }
</script>

<style></style>