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
                    <LinkButton :to="'/timecourses/'+ table.item.pk" :title="'Timecourse: '+table.item.pk" :icon="icon('output')"/>
                    <JsonButton :resource_url="api + '/timecourses_read/'+ table.item.pk +'/?format=json'"/>
                </td>
                <td><text-highlight :queries="search.split(/[ ,]+/)">{{table.item.pktype }}</text-highlight></td>
                <td>
                    <get-data v-if="table.item.group" :resource_url="table.item.group">
                        <div slot-scope="data">
                            <group-button :group="data.data" />
                            <text-highlight :queries="search.split(/[ ,]+/)">{{ data.data.name }}</text-highlight>
                        </div>
                    </get-data>
                </td>
                <td>
                    <get-data v-if="table.item.individual" :resource_url="table.item.individual">
                        <div slot-scope="data">
                            <individual-button :individual="data.data" />
                            <text-highlight :queries="search.split(/[ ,]+/)">{{ data.data.name }}</text-highlight>
                        </div>
                    </get-data>
                <td>
                    <span v-for="(intervention_url, index2) in table.item.interventions" :key="index2">
                    <a :href="intervention_url"><v-icon>{{ icon('intervention') }}</v-icon></a>&nbsp;
                        <get-data :resource_url="intervention_url">
                        <div slot-scope="data">
                            <text-highlight :queries="search.split(/[ ,]+/)">
                                {{ data.data.name }}
                            </text-highlight>
                        </div>
                    </get-data>
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
                    <timecourse-plot :timecourse="table.item"/>
                </td>
            </template>
            <no-data/>

        </v-data-table>
    </v-card>
</template>

<script>
    import {searchTableMixin} from "./mixins";
    import TableToolbar from '../lib/TableToolbar';
    import NoData from '../lib/NoData';
    import GroupButton from '../lib/GroupButton'
    import IndividualButton from '../lib/IndividualButton'
    import TimecoursePlot from '../plots/TimecoursePlot'
    import SubstanceChip from "../detail/SubstanceChip"


    export default {
        name: "TimecoursesTable3",
        components: {
            NoData,
            TableToolbar,
            GroupButton,
            IndividualButton,
            TimecoursePlot,
            SubstanceChip,
        },
        mixins: [searchTableMixin],
        data() {
            return {
                otype: "timecourses",
                otype_single: "timecourse",
                headers: [
                    {text: '', value: 'buttons', sortable: false},
                    {text: 'Type', value: 'type'},
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
