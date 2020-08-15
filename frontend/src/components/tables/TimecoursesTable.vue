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
                :footer-props="footer_options"
        >
            <template v-slot:item.buttons="{ item }">
                <LinkButton v-if="item.study"
                            :to="'/studies/'+ item.study.sid"
                            :title="'Study: '+item.study.name"
                            icon="study"
                />
            </template>

            <template v-slot:item.measurement_type="{ item }">
                <object-chip :object="f(item).measurement_type"
                             otype="measurement_type"
                             :search="search"
                />
            </template>
            <template v-slot:item.subject="{ item }">
                <get-data v-if="f(item).group" :resource_url="group_url(f(item).group.pk)">
                        <span slot-scope="data">
                            <object-chip :object="data.data"
                                         otype="group"
                                         :search="search"
                            />
                        </span>
                </get-data>
                <get-data v-if="f(item).individual" :resource_url="individual_url(f(item).individual.pk)">
                        <span slot-scope="data">
                            <object-chip :object="data.data"
                                         otype="individual"
                                         :search="search"
                            />
                        </span>
                </get-data>
            </template>
            <template v-slot:item.interventions="{ item }">
                    <span v-if="f(item).interventions" v-for="(intervention, index2) in f(item).interventions" :key="index2">
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
                <object-chip :object="f(item).tissue"
                             otype="tissue"
                             :search="search"
                />
            </template>

            <template v-slot:item.substance="{ item }">
                <object-chip :object="f(item).substance"
                             otype="substance"
                             :search="search"
                />
            </template>

            <template v-slot:item.timecourse="{ item }">
              <!--
                <timecourse-plot :timecourse="f(item)"/>
                -->
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
      method:{
          f(item){
            return item[0][0]
          }
      },

        mixins: [searchTableMixin, UrlMixin],
        data() {
            return {
                otype: "subsets",
                otype_single: "subset",
                headers: [
                    {text: '', value: 'buttons', sortable: false},
                    {text: 'Measurement Type', value: 'measurement_type',sortable: false},
                    {text: 'Subjects', value: 'subject',sortable: false},
                    {text: 'Interventions', value: 'interventions', sortable: false},
                    {text: 'Tissue', value: 'tissue',sortable: false},
                    {text: 'Substance', value: 'substance',sortable: false},
                    {text: 'Timecourse', value: 'timecourse',sortable: false},
                ]
            }
        },
    }
</script>

<style scoped>

</style>
