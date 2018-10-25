<template>
    <v-card>
        <table-toolbar :otype="otype" :count="count" :url="url" @update="searchUpdate"/>
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
                    <json-button :resource_url="api + '/groups_elastic/'+ table.item.pk +'/?format=json'"/>
                </td>
                <td>
                    <group-info :group="table.item"/>
                </td>
                <td>
                    <v-layout wrap>
                        <span v-for="item in table.item.characteristica_all_final" :key="item.pk">
                            <characteristica-card :data="item"
                                                  :resource_url="characterica_url(get_ids(table.item.characteristica_all_final))"/>
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

    export default {
        name: "GroupsTable",
        components: {
            NoData,
            TableToolbar,
            CharacteristicaCard,
        },
        mixins: [searchTableMixin,UrlMixin],
        data () {
            return {
                otype: "groups",
                otype_single: "group",
                headers: [
                    {text: '', value: 'buttons', sortable: false},
                    {text: 'Info', value: 'info'},
                    {text: 'Characteristica', value: 'characteristica'},
                ]
            }
        },
    }
</script>

<style scoped>

</style>
