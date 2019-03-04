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
                    <link-button :to="'/groups/'+ table.item.pk" :title="'Group: '+table.item.pk"
                                 :icon="icon('group')"/>

                    <!--<link-button :to="'/studies/'+ table.item.study.pk" :title="'Study: '+table.item.study.name" :icon="icon('study')"/>-->
                    <json-button :resource_url="api + '/groups_elastic/'+ table.item.pk +'/?format=json'"/>
                </td>
                <td>
                    <group-chip :group="table.item" :search="search"/>
                </td>
                <td>
                    <v-layout wrap>
                        <span v-for="item in table.item.characteristica_all_normed" :key="item.pk">
                            <characteristica-card :data="item"
                                                  :resource_url="characterica_url(get_ids(table.item.characteristica_all_normed))"/>
                        </span>
                    </v-layout>
                </td>
            </template>
            <no-data/>
        </v-data-table>
    </v-card>
</template>

<script>
    import {searchTableMixin, UrlMixin} from "./mixins";
    import TableToolbar from './TableToolbar';
    import NoData from './NoData';
    import CharacteristicaCard from '../detail/CharacteristicaCard'
    import GroupChip from '../detail/GroupChip'

    export default {
        name: "GroupsTable",
        components: {
            NoData,
            TableToolbar,
            CharacteristicaCard,
            GroupChip
        },
        mixins: [searchTableMixin,UrlMixin],
        data () {
            return {
                otype: "groups",
                otype_single: "group",
                headers: [
                    {text: '', value: 'buttons', sortable: false},
                    {text: 'Name', value: 'name'},
                    {text: 'Characteristica', value: 'characteristica'},
                ]
            }
        },
    }
</script>

<style scoped>

</style>
