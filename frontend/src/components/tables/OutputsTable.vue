<template>
    <v-sheet flat>
        <table-toolbar :otype="otype" :count="count" :autofocus="autofocus" :url="url" @update="searchUpdate"/>
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
                    <link-button v-if="item.study"
                                :sid="item.study.sid"
                                show_type_input="study"
                                :title="'Study: '+item.study.name"
                                icon="study"
                    />
                    <JsonButton :resource_url="api + 'outputs/'+ item.pk +'/?format=json'"/>
                </template>
                <template v-slot:item.calculated="{ item }">
                  <v-icon v-if="!item.calculated"
                          small
                          color="success">fas fa-check-circle
                  </v-icon>
                  <v-icon v-else
                          small
                          color="black"
                          title="Calculated from timecourse.">fas fa-times-circle
                  </v-icon>
                </template>
                <template v-slot:item.details="{ item }">
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
                  <br />
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
                  <br />
                    <object-chip :object="item.tissue"
                                 otype="tissue"
                                 :search="search"
                    />

                </template>

                <template v-slot:item.time="{ item }">

                </template>
                <template v-slot:item.output="{ item }">
                  <v-layout d-flex flex-wrap >
                    <characteristica-card :data="item"/>
                  </v-layout>
                </template>

            <no-data/>
        </v-data-table>
    </v-sheet>
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
                    {text: 'Measured', value: 'calculated', sortable: false},
                    {text: 'Details', value: 'details',sortable: false},
                    {text: 'Output', value: 'output', sortable: false},

                ]
            }
        },
    }
</script>

<style scoped></style>
