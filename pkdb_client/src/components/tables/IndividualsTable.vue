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
                    <link-button :to="'/individuals/'+ table.item.pk" :title="'Individual: '+table.item.pk" :icon="icon('individual')"/>
                    <!--<link-button :to="'/studies/'+ table.item.study.pk" :title="'Study: '+ table.item.study.name" :icon="icon('study')"/>-->
                    <json-button :resource_url="api + '/individuals_elastic/'+ table.item.pk +'/?format=json'"/>
                </td>
                <td>
                    <div class="attr-card">
                        <individual-chip :individual="table.item" :search="search"/>
                    </div>
                </td>
                <td>
                    <get-data :resource_url="group_url(table.item.group.pk)">
                        <span slot-scope="group">
                            <group-chip :group="group.data" :search="search"/>
                        </span>
                    </get-data>
                </td>
                <td>
                     <v-layout wrap>
                        <span v-for="item in table.item.characteristica_all_final" :key="item.pk">
                            <characteristica-card :data="item" :resource_url="characterica_url(get_ids(table.item.characteristica_all_final))" />
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
    import IndividualChip from '../detail/IndividualChip'

    export default {
        name: "IndividualsTable",
        components: {
            NoData,
            TableToolbar,
            CharacteristicaCard,
            IndividualChip,
            GroupChip
        },
        mixins: [searchTableMixin, UrlMixin],
        data () {
            return {
                otype: "individuals",
                otype_single: "individual",
                headers: [
                    {text: '', value: 'buttons',sortable: false},
                    {text: 'Individual', value: 'individual'},
                    {text: 'Group', value: 'group'},
                    {text: 'Characteristica', value: 'characteristica'},
                ]
            }
        },
    }
</script>

<style scoped></style>
