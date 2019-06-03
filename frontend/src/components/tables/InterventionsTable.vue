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
                    <LinkButton :to="'/interventions/'+ table.item.pk" :title="'Group: '+table.item.pk" :icon="icon(otype_single)"/>
                    <JsonButton :resource_url="api + '/interventions_elastic/'+ table.item.pk +'/?format=json'"/>
                </td>
                <td>
                    <intervention-chip :intervention="table.item" :search="search"/>
                </td>
                <td>
                    <text-highlight :queries="[search]"> {{table.item.application }}</text-highlight><br />
                    <text-highlight :queries="[search]">{{table.item.time}}</text-highlight>
                        <span v-if="table.item.time_unit"> [<text-highlight :queries="[search]">{{table.item.time_unit }}</text-highlight>]</span><br />
                    <text-highlight :queries="[search]">{{ table.item.route }}</text-highlight><br />
                    <text-highlight :queries="[search]">{{table.item.form}}</text-highlight>
                </td>

                <td><characteristica-card :data="table.item" /></td>
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
    import SubstanceChip from "../detail/SubstanceChip"
    import InterventionChip from "../detail/InterventionChip"

    export default {
        name: "InterventionsTable",
        components: {
            NoData,
            TableToolbar,
            CharacteristicaCard,
            SubstanceChip,
            InterventionChip
        },
        mixins: [searchTableMixin],
        data () {
            return {
                otype: "interventions",
                otype_single: "intervention",
                headers: [
                    {text: '', value: 'buttons',sortable: false},
                    {text: 'Name', value: 'name'},
                    {text: 'Application', value: 'application'},
                    {text: 'Measurement', value: 'value'},
                ],
            }
        },
    }
</script>

<style scoped>
</style>