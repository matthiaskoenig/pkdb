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
                    <link-button :to="'/individuals/'+ item.pk" :title="'Individual: '+item.pk" :icon="icon('individual')"/>
                    <!--<link-button :to="'/studies/'+ item.study.pk" :title="'Study: '+ item.study.name" :icon="icon('study')"/>-->
                    <json-button :resource_url="api + 'individuals_elastic/'+ item.pk +'/?format=json'"/>
            </template>
            <template v-slot:item.individual="{ item }">
                <div class="attr-card">
                    <individual-chip :individual="item" :search="search"/>
                </div>
            </template>
            <template v-slot:item.group="{ item }">
                <get-data :resource_url="group_url(item.group.pk)">
                    <span slot-scope="group">
                        <group-chip :group="group.data" :search="search"/>
                    </span>
                </get-data>
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
