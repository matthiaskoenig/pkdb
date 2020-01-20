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
                    <link-button :to="'/groups/'+ item.pk" :title="'Group: '+item.pk"
                                 :icon="icon('group')"/>

                    <!--<link-button :to="'/studies/'+ item.study.pk" :title="'Study: '+item.study.name" :icon="icon('study')"/>-->
                    <json-button :resource_url="api + 'groups_elastic/'+ item.pk +'/?format=json'"/>
                </template>
            <template v-slot:item.name="{ item }">
                    <group-chip :group="item" :search="search"/>
                </template>
            <template v-slot:item.parent="{ item }">
                    <group-chip v-if="item.parent" :group="item.parent" :search="search"/>

                </template>
            <template v-slot:item.characteristica="{ item }">
                <v-layout wrap>
                    <span v-for="characteristica in item.characteristica_all_normed" :key="characteristica.pk">
                         <characteristica-card :data="characteristica" :resource_url="characterica_url([characteristica.pk])"/>
                    </span>
                </v-layout>
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
                    {text: 'Parent', value: 'parent'},
                    {text: 'Characteristica', value: 'characteristica'},
                ]
            }
        },
    }
</script>

<style scoped>

</style>
