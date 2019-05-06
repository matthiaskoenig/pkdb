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
                    <LinkButton :to="'/studies/'+ table.item.pk" :title="'Study: '+table.item.pk" :icon="icon('study')"/>
                    <LinkButton :to="'/references/'+ table.item.reference.sid" :title="'Reference: '+table.item.reference.sid" :icon="icon('reference')"/>
                    <JsonButton :resource_url="api + '/studies_elastic/'+ table.item.pk +'/?format=json'"/>
                    <export-format-button :resource_url="api + '/studies/'+ table.item.pk +'/?format=json'"/>
                </td>
                <td>
                    <text-highlight :queries="search.split(/[ ,]+/)"> {{ table.item.name }}</text-highlight>
                </td>
                <td>
                    <span v-for="(c, index2) in table.item.substances" :key="index2"><substance-chip :title="c" :search="search"/></span>
                </td>
                <td>
                    <count-chip :count=table.item.group_count icon="group"></count-chip>
                    <count-chip :count=table.item.individual_count icon="individual"></count-chip>
                    <count-chip :count=table.item.intervention_count icon="intervention"></count-chip>
                    <count-chip :count=table.item.output_count icon="output"></count-chip>
                    <count-chip :count=table.item.timecourse_count icon="timecourse"></count-chip>
                </td>
                <td>
                    <UserAvatar :user="table.item.creator" :search="search"/>
                </td>
                <td>
                    <span v-for="(c, index2) in table.item.curators" :key="index2"><user-avatar :user="c" :search="search"/></span>
                </td>
            </template>
            <no-data/>
        </v-data-table>
    </v-card>
</template>

<script>
    import {searchTableMixin} from "./mixins";
    import TableToolbar from './TableToolbar';
    import NoData from './NoData';
    import CharacteristicaCard from '../detail/CharacteristicaCard'
    import GroupChip from "../detail/GroupChip";
    import CountChip from "../detail/CountChip";

    export default {
        name: "StudiesTable",
        components: {
            GroupChip,
            NoData,
            TableToolbar,
            CharacteristicaCard,
            CountChip
        },
        mixins: [searchTableMixin],
        data () {
            return {
                otype: "studies",
                otype_single: "study",
                headers: [
                    {text: '', value: 'buttons',sortable: false},
                    {text: 'Name', value: 'name'},
                    {text: 'Substances', value: 'substances',sortable: false},
                    {text: 'Counts', value: 'counts',sortable: false},
                    {text: 'Creator', value: 'creator'},
                    {text: 'Curators', value: 'curators',sortable: false},
                ],
            }
        },
    }
</script>

<style scoped></style>