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
                    <LinkButton :to="'/outputs/'+ item.pk"
                                :title="'Output: '+item.pk"
                                :icon="otype"
                    />
                    <JsonButton :resource_url="api + 'outputs/'+ item.pk +'/?format=json'"/>
                </template>
                <template v-slot:item.measurement_type="{ item }">
                    <object-chip :object="item.measurement_type"
                                 otype="measurement_type"
                                 :search="search"
                    />
                </template>
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
                <template v-slot:item.calculated="{ item }">
                    <v-icon v-if="!item.calculated"
                            small
                            color="success">fas fa-check-circle
                    </v-icon>
                    <v-icon v-else
                            small
                            color="black"
                            :title="'Calculated from timecourse: ' + item.timecourse.pk">fas fa-times-circle
                    </v-icon>

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
                    <object-chip :object="item.tissue"
                                 otype="tissue"
                                 :search="search"
                    />
                </template>

                <template v-slot:item.time="{ item }">
                    {{item.time}}
                    <span v-if="item.time_unit">[{{ item.time_unit }}]</span>
                </template>
                <template v-slot:item.value="{ item }"><characteristica-card :data="item"/></template>

            <no-data/>
        </v-data-table>
    </v-card>
</template>

<script>
    import {searchTableMixin, UrlMixin} from "./mixins";
    import TableToolbar from './TableToolbar';
    import NoData from './NoData';
    import CharacteristicaCard from '../detail/CharacteristicaCard'

    export default {
        name: "OutputsTable",
        components: {
            NoData,
            TableToolbar,
            CharacteristicaCard
        },
        mixins: [searchTableMixin, UrlMixin],
        data () {
            return {
                otype: "outputs",
                otype_single: "output",
                headers: [
                    {text: '', value: 'buttons',sortable: false},
                    {text: 'Measured', value: 'calculated',sortable: false},
                    {text: 'Measurement Type', value: 'measurement_type',sortable: false},
                    {text: 'Subjects', value: 'subject',sortable: false},
                    {text: 'Interventions', value: 'interventions',sortable: false},
                    {text: 'Tissue', value: 'tissue',sortable: false},
                    {text: 'Time', value: 'time',sortable: false},
                    {text: 'Value', value: 'value',sortable: false},


                ]
            }
        },
    }
</script>

<style scoped></style>
