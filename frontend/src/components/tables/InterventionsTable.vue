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
                <LinkButton :to="'/interventions/'+ item.pk"
                            :title="'Intervention: '+ item.pk"
                            icon="intervention"
                />
                <JsonButton :resource_url="api + 'interventions/'+ item.pk +'/?format=json'"/>
            </template>
            <template v-slot:item.name="{ item }">
                <object-chip :object="item"
                             otype="intervention"
                             :name="item.name"
                             :search="search"
                />
            </template>
            <template v-slot:item.application="{ item }">
                <text-highlight :queries="[search]">{{ item.application }}</text-highlight><br />
                <text-highlight :queries="[search]">{{ item.time }}</text-highlight>
                    <span v-if="item.time_unit"> [<text-highlight :queries="[search]">{{ item.time_unit }}</text-highlight>]</span><br />
                <text-highlight :queries="[search]">{{ item.route }}</text-highlight><br />
                <text-highlight :queries="[search]">{{ item.form }}</text-highlight>
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
                    {text: 'Name', value: 'name'},
                    {text: 'Application', value: 'application'},
                    {text: 'Measurement', value: 'value'},
                ],
            }
        },
    }
</script>

<style scoped>
</style>