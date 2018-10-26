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
                    <LinkButton :to="'/outputs/'+ table.item.pk" :title="'Output: '+table.item.pk" :icon="icon(otype)"/>
                    <JsonButton :resource_url="api + '/outputs_elastic/'+ table.item.pk +'/?format=json'"/>
                </td>
                <td><text-highlight :queries="search.split(/[ ,]+/)">{{table.item.pktype }} </text-highlight> </td>
                <td>
                    <get-data v-if="table.item.group" :resource_url="group_url(table.item.group.pk)">
                        <span slot-scope="data">
                            <group-chip :group="data.data" :search="search"/>
                        </span>
                    </get-data>
                </td>
                <td>
                    <get-data v-if="table.item.individual" :resource_url="individual_url(table.item.individual.pk)">
                        <span slot-scope="data">
                            <individual-chip :individual="data.data" :search="search"/>
                        </span>
                    </get-data>
                <td>
                    <span v-if="table.item.interventions" v-for="(intervention, index2) in table.item.interventions" :key="index2">
                        <get-data :resource_url="intervention_url(intervention.pk)">
                            <span slot-scope="data">
                                <intervention-chip :intervention="data.data" :search="search"/>
                            </span>
                        </get-data>&nbsp;
                    </span>
                </td>
                <td>
                    <text-highlight :queries="search.split(/[ ,]+/)">
                        {{table.item.tissue}}
                    </text-highlight>
                </td>
                <td>
                    <substance-chip :title="table.item.substance.name" :search="search"/>
                </td>
                <td>
                    {{table.item.time}}
                    <span v-if="table.item.time_unit">[{{table.item.time_unit }}]</span>
                </td>
                <td><characteristica-card :data="table.item"/></td>
            </template>
            <no-data/>
        </v-data-table>
    </v-card>
</template>

<script>
    import {searchTableMixin, UrlMixin} from "./mixins";
    import TableToolbar from './TableToolbar';
    import NoData from './NoData';
    import GroupButton from '../lib/GroupButton'
    import IndividualButton from '../lib/IndividualButton'
    import CharacteristicaCard from '../detail/CharacteristicaCard'
    import SubstanceChip from "../detail/SubstanceChip"
    import InterventionChip from "../detail/InterventionChip"
    import GroupChip from "../detail/GroupChip"
    import IndividualChip from "../detail/IndividualChip"

    export default {
        name: "OutputsTable",
        components: {
            NoData,
            TableToolbar,
            GroupButton,
            IndividualButton,
            CharacteristicaCard,
            SubstanceChip,
            InterventionChip,
            GroupChip,
            IndividualChip
        },
        mixins: [searchTableMixin, UrlMixin],
        data () {
            return {
                otype: "outputs",
                otype_single: "output",
                headers: [
                    {text: '', value: 'buttons',sortable: false},
                    {text: 'Type', value: 'pktype'},
                    {text: 'Group', value: 'group'},
                    {text: 'Individual', value: 'individual'},
                    {text: 'Interventions', value: 'interventions',sortable: false},
                    {text: 'Tissue', value: 'tissue'},
                    {text: 'Substance', value: 'substance'},
                    {text: 'Time', value: 'time'},
                    {text: 'Value', value: 'value'},
                ]
            }
        },
    }
</script>

<style scoped></style>
