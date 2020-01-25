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
                <LinkButton v-if="item.study"
                            :to="'/studies/'+ item.study.sid"
                            :title="'Study: '+item.study.name"
                            icon="study"
                />
                <LinkButton :to="'/timecourses/'+ item.pk"
                            :title="'Timecourse: '+item.pk"
                            icon="timecourse"
                />
                <JsonButton :resource_url="api + 'timecourses/'+ item.pk +'/?format=json'"/>
            </template>

            <template v-slot:item.measurement_type="{ item }"><text-highlight :queries="search.split(/[ ,]+/)">{{item.measurement_type }} </text-highlight> </template>
            <template v-slot:item.subject="{ item }">
                <get-data v-if="item.group" :resource_url="group_url(item.group.pk)">
                        <span slot-scope="data">
                            <object-chip :object="data.data"
                                         otype="group"
                                         :search="search"
                            />
                        </span>
                </get-data>
                <get-data v-if="item.individual" :resource_url="individual_url(item.individual.pk)">
                        <span slot-scope="data">
                            <object-chip :object="data.data"
                                         otype="individual"
                                         :search="search"
                            />
                        </span>
                </get-data>
            </template>
            <template v-slot:item.interventions="{ item }">
                    <span v-if="item.interventions" v-for="(intervention, index2) in item.interventions" :key="index2">
                        <get-data :resource_url="intervention_url(intervention.pk)">
                            <span slot-scope="data">
                                <object-chip :object="data.data"
                                             otype="intervention"
                                             :search="search"
                                />
                            </span>
                        </get-data>&nbsp;
                    </span>
            </template>
            <template v-slot:item.tissue="{ item }">
                <text-highlight :queries="search.split(/[ ,]+/)">
                    {{ item.tissue }}
                </text-highlight>
            </template>

            <template v-slot:item.substance="{ item }">
                <object-chip :object="item.substance"
                             otype="substance"
                             :search="search"
                />
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
    import TimecoursePlot from '../plots/TimecoursePlot'

    export default {
        name: "TimecoursesTable",
        components: {
            NoData,
            TableToolbar,
            TimecoursePlot,
        },
        mixins: [searchTableMixin, UrlMixin],
        data() {
            return {
                otype: "timecourses",
                otype_single: "timecourse",
                headers: [
                    {text: '', value: 'buttons', sortable: false},
                    {text: 'Measurement Type', value: 'measurement_type'},
                    {text: 'Subjects', value: 'subject'},
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
