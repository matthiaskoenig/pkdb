<template>
    <v-card flat>
        <table-toolbar otype="timecourse" :count="count" :autofocus="autofocus" :url="url" @update="searchUpdate"/>
        <v-data-table
                fill-height
                fixed-header
                :height="windowHeight"
                :headers="headers"
                :items="entries"
                :options.sync="options"
                :server-items-length="count"
                :loading="loading"
                :class="table_class"
                :footer-props="footer_options"
        >
            <template v-slot:item.buttons="{ item }">
                <LinkButton v-if="item.study"
                            :sid="item.study.sid"
                            show_type="study"
                            :title="'Study: '+item.study.name"
                            icon="study"
                />
            </template>

          <template v-slot:item.name="{ item }">
            {{item.name}}

          </template>

            <template v-slot:item.measurement_type="{ item }">
                <object-chip :object="item.array[0][0].measurement_type"
                             otype="measurement_type"
                             :search="search"
                />
            </template>
            <template v-slot:item.details="{ item }">
                <get-data v-if="Object.keys(item.array[0][0].group).length !== 0" :resource_url="group_url(item.array[0][0].group.pk)">
                        <span slot-scope="data">
                            <object-chip :object="data.data"
                                         otype="group"
                                         :search="search"
                            />
                        </span>
                </get-data>
                <get-data v-if="Object.keys(item.array[0][0].individual).length !== 0" :resource_url="individual_url(item.array[0][0].individual.pk)">
                        <span slot-scope="data">
                            <object-chip :object="data.data"
                                         otype="individual"
                                         :search="search"
                            />
                        </span>
                </get-data>
              <br />
                    <span v-if="item.array[0][0].interventions" v-for="(intervention, index2) in item.array[0][0].interventions" :key="index2">
                        <get-data :resource_url="intervention_url(intervention.pk)">
                            <span slot-scope="data">
                                <object-chip :object="data.data"
                                             otype="intervention"
                                             :search="search"
                                />
                            </span>
                        </get-data>&nbsp;
                    </span>
               <br />
                <object-chip :object="item.array[0][0].tissue"
                             otype="tissue"
                             :search="search"
                />
                <br />
                <object-chip :object="item.array[0][0].substance"
                             otype="substance"
                             :search="search"
                />
            </template>

            <template v-slot:item.timecourse="{ item }">

                <timecourse-plot :array="item.array"/>
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
      method: {
    },

        mixins: [searchTableMixin, UrlMixin],

        data() {
            return {
                otype: "subsets",
                otype_single: "subset",
                headers: [
                    {text: '', value: 'buttons', sortable: false},
                    {text: 'Measurement', value: 'measurement_type', sortable: false},
                    {text: 'Details', value: 'details',sortable: false},
                    {text: 'Timecourse', value: 'timecourse',sortable: false},
                ]
            }
        },
    }
</script>

<style scoped>

</style>
