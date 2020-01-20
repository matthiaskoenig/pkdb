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
                    <LinkButton :to="'/timecourses/'+ item.pk" :title="'Timecourse: '+item.pk" :icon="icon('output')"/>
                    <JsonButton :resource_url="api + 'timecourses_elastic/'+ item.pk +'/?format=json'"/>
                </template>

                <template v-slot:item.measurement_type="{ item }"><text-highlight :queries="search.split(/[ ,]+/)">{{item.measurement_type }}</text-highlight></template>
                <template v-slot:item.group="{ item }">
                    <get-data v-if="item.group" :resource_url="group_url(item.group.pk)">
                        <span slot-scope="data">
                            <group-chip :group="data.data" :search="search"/>
                        </span>
                    </get-data>
                </template>
                <template v-slot:item.individual="{ item }">
                    <get-data v-if="item.individual" :resource_url="individual_url(item.individual.pk)">
                        <span slot-scope="data">
                            <individual-chip :individual="data.data" :search="search"/>
                        </span>
                    </get-data>
                </template>
                <template v-slot:item.interventions="{ item }">
                    <span v-for="(intervention, index2) in item.interventions" :key="index2">
                        <get-data :resource_url="intervention_url(intervention.pk)">
                        <span slot-scope="data">
                            <intervention-chip :intervention="data.data" :search="search"/>
                        </span>
                    </get-data>
                    </span>
                </template>
                <template v-slot:item.tissue="{ item }">
                    <text-highlight :queries="search.split(/[ ,]+/)">
                        {{item.tissue}}
                    </text-highlight>
                </template>

                <template v-slot:item.substance="{ item }">
                    <substance-chip :title="item.substance" :search="search"/>
                </template>
                <template v-slot:item.timecourse="{ item }">
                    <timecourse-plot :timecourse="item"/>
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
                    {text: 'Timecourse', value: 'timecourse'},
                ]
            }
        },
    }
</script>

<style scoped>

</style>
