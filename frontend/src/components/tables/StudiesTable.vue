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
                <LinkButton :to="'/studies/'+ item.sid" :title="'Study: '+item.pk" :icon="icon('study')"/>
                <LinkButton v-if="item.reference" :to="'/references/'+ item.reference.sid" :title="'Reference: '+item.reference.sid" :icon="icon('reference')"/>
                <JsonButton :resource_url="api + 'studies_elastic/'+ item.sid +'/?format=json'"/>
                <export-format-button :resource_url="api + 'studies/'+ item.sid +'/?format=json'"/>
            </template>
            <template v-slot:item.sid="{ item }">
                <text-highlight :queries="search.split(/[ ,]+/)"> {{ item.sid }}</text-highlight>

            </template>

            <template v-slot:item.name="{ item }">
                <text-highlight :queries="search.split(/[ ,]+/)"> {{ item.name }}</text-highlight>
            </template>


            <template v-slot:item.counts="{ item }">
                <count-chip :disabled="true" :count=item.group_count icon="group" name="group"></count-chip>
                <count-chip :disabled="true" :count=item.individual_count icon="individual" name="individual"></count-chip>
                <count-chip :disabled="true" :count=item.intervention_count icon="intervention" name="intervention"></count-chip>
                <count-chip :disabled="true" :count=item.output_count icon="output" name="output"></count-chip >
                <count-chip :disabled="true" :count=item.timecourse_count icon="timecourse" name="timecourse"></count-chip>
            </template>

            <template v-slot:item.substances="{ item }">
                <span v-for="(c, index2) in item.substances" :key="index2"><substance-chip :title="c" :search="search"/></span>
            </template>

            <template v-slot:item.creator="{ item }">
                <user-avatar :user="item.creator" :search="search"/>
            </template>

            <template v-slot:item.curators="{ item }">
                <span v-for="(c, index2) in item.curators" :key="index2"><user-rating :user="c" :search="search"/></span>
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
    import GroupChip from "../detail/GroupChip";
    import CountChip from "../detail/CountChip";


    export default {
        name: "StudiesTable",
        components: {
            GroupChip,
            NoData,
            TableToolbar,
            CharacteristicaCard,
            CountChip
        },
        mixins: [searchTableMixin],
        data () {
            return {
                otype: "studies",
                otype_single: "study",
                headers: [
                    {text: '', value: 'buttons', sortable: false},
                    {text: 'Sid', value: 'sid'},
                    {text: 'Name', value: 'name'},
                    {text: 'Counts', value: 'counts', sortable: false},
                    {text: 'Substances', value: 'substances', sortable: false},
                    {text: 'Creator', value: 'creator',},
                    {text: 'Curators', value: 'curators', sortable: false},
                ],
            }
        },
    }
</script>

<style scoped></style>