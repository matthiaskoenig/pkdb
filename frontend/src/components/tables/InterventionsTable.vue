<template>
    <v-card flat>
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
                <LinkButton :to="'/interventions/'+ item.pk"
                            :title="'Intervention: '+ item.pk"
                            icon="intervention"
                />
                <JsonButton :resource_url="api + 'interventions/'+ item.pk +'/?format=json'"/>
            </template>
            <template v-slot:item.name="{ item }">
                <object-chip :object="item"
                             otype="intervention"
                             :search="search"
                />
            </template>
            <template v-slot:item.substance="{ item }">
                <object-chip :object="item.substance"
                             otype="substance"
                             :search="search"
                />
            </template>
            <template v-slot:item.application="{ item }">
                <text-highlight :queries="[search]">{{ item.application.label }}</text-highlight><br />
                <text-highlight :queries="[search]">{{ item.time }}</text-highlight>
                    <span v-if="item.time_unit"> [<text-highlight :queries="[search]">{{ item.time_unit }}</text-highlight>]</span><br />
                <text-highlight :queries="[search]">{{ item.route.label }}</text-highlight><br />
                <text-highlight :queries="[search]">{{ item.form.label }}</text-highlight>
            </template>
            <template v-slot:item.value="{ item }">
                <characteristica-card :data="item" />
            </template>

            <no-data/>
        </v-data-table>
    </v-card>
</template>

<script>
    import {searchTableMixin} from "./mixins";
    import TableToolbar from './TableToolbar';
    import NoData from './NoData';
    import CharacteristicaCard from '../detail/CharacteristicaCard'

    export default {
        name: "InterventionsTable",
        components: {
            NoData,
            TableToolbar,
            CharacteristicaCard,
        },
        mixins: [searchTableMixin],
        data () {
            return {
                otype: "interventions",
                otype_single: "intervention",
                headers: [
                    {text: '', value: 'buttons',sortable: false},
                    {text: 'Name', value: 'name', sortable: false},
                    {text: 'Substance', value: 'substance', sortable: false},
                    {text: 'Application', value: 'application', sortable: false},
                    {text: 'Measurement', value: 'value', sortable: false},
                ],
            }
        },
    }
</script>

<style scoped>
</style>