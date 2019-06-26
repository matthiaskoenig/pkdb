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
                    <LinkButton :to="'/timecourses/'+ table.item.pk" :title="'Timecourse: '+table.item.pk" :icon="icon('output')"/>
                    <JsonButton :resource_url="api + '/timecourses_elastic/'+ table.item.pk +'/?format=json'"/>
                </td>
                <td><text-highlight :queries="search.split(/[ ,]+/)">{{table.item.measurement_type }}</text-highlight></td>
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
                    <span v-for="(intervention, index2) in table.item.interventions" :key="index2">
                        <get-data :resource_url="intervention_url(intervention.pk)">
                        <span slot-scope="data">
                            <intervention-chip :intervention="data.data" :search="search"/>
                        </span>
                    </get-data>
                    </span>
                </td>
                <td>
                    <text-highlight :queries="search.split(/[ ,]+/)">
                        {{table.item.tissue}}
                    </text-highlight>
                </td>
                <td>
                    <substance-chip :title="table.item.substance" :search="search"/>
                </td>
                <td>
                    <timecourse-plot :timecourse="table.item"/>
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
    import GroupButton from '../lib/GroupButton'
    import IndividualButton from '../lib/IndividualButton'
    import TimecoursePlot from '../plots/TimecoursePlot'
    import SubstanceChip from "../detail/SubstanceChip"
    import InterventionChip from "../detail/InterventionChip"
    import GroupChip from "../detail/GroupChip"
    import IndividualChip from "../detail/IndividualChip"


    export default {
        name: "TimecoursesTable",
        components: {
            NoData,
            TableToolbar,
            GroupButton,
            IndividualButton,
            TimecoursePlot,
            SubstanceChip,
            InterventionChip,
            GroupChip,
            IndividualChip
        },
        mixins: [searchTableMixin, UrlMixin],
        data() {
            return {
                otype: "timecourses",
                otype_single: "timecourse",
                headers: [
                    {text: '', value: 'buttons', sortable: false},
                    {text: 'Measurement Type', value: 'measurement_type'},
                    {text: 'Group', value: 'group'},
                    {text: 'Individual', value: 'individual'},
                    {text: 'Interventions', value: 'interventions', sortable: false},
                    {text: 'Tissue', value: 'tissue'},
                    {text: 'Substance', value: 'substance'},
                    {text: 'Timecourse', value: 'auc_end'},
                ]
            }
        },
    }
</script>

<style scoped>

</style>
