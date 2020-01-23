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
                    <LinkButton :to="'/outputs/'+ item.pk"
                                :title="'Output: '+item.pk"
                                :icon="otype"
                    />
                    <JsonButton :resource_url="api + 'outputs/'+ item.pk +'/?format=json'"/>
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

                <template v-slot:item.time="{ item }">
                    {{item.time}}
                    <span v-if="item.time_unit">[{{ item.time_unit }}]</span>
                </template>
                <template v-slot:item.value="{ item }"><characteristica-card :data="item"/></template>
                <template v-slot:item.calculated="{ item }">
                    <v-chip :disabled="true" color='green' v-if="item.calculated" >
                        <v-icon small :title="'is calculated from timecourse with pk:' + item.timecourse.pk">fas fa-check-circle</v-icon>
                    </v-chip>
                </template>

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
                    {text: 'Measurement Type', value: 'measurement_type'},
                    {text: 'Subjects', value: 'subject'},
                    {text: 'Interventions', value: 'interventions',sortable: false},
                    {text: 'Tissue', value: 'tissue'},
                    {text: 'Time', value: 'time'},
                    {text: 'Value', value: 'value'},
                    {text: 'Calculated', value: 'calculated'},

                ]
            }
        },
    }
</script>

<style scoped></style>
