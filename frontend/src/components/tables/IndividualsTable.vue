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
                <link-button :to="'/individuals/'+ item.pk"
                             :title="'Individual: '+item.pk"
                             icon="individual"
                />
                <json-button :resource_url="api + 'individuals/'+ item.pk +'/?format=json'"/>
            </template>
            <template v-slot:item.individual="{ item }">
                <object-chip :object="item"
                             otype="individual"
                             :search="search"
                />
            </template>
            <template v-slot:item.group="{ item }">
                <get-data :resource_url="group_url(item.group.pk)">
                    <span slot-scope="group">
                    <object-chip :object="group.data"
                                 otype="group"
                                 :count="group.data.count"
                                 :search="search"
                    />
                    </span>
                </get-data>
            </template>
            <template v-slot:item.characteristica="{ item }">
                <characteristica-card-deck :characteristica="item.characteristica" />
            </template>
            <no-data/>
        </v-data-table>
    </v-card>
</template>

<script>
    import {searchTableMixin, UrlMixin} from "./mixins";
    import TableToolbar from './TableToolbar';
    import NoData from './NoData';
    import CharacteristicaCardDeck from '../detail/CharacteristicaCardDeck'

    export default {
        name: "IndividualsTable",
        components: {
            NoData,
            TableToolbar,
            CharacteristicaCardDeck,
        },
        mixins: [searchTableMixin, UrlMixin],
        data () {
            return {
                otype: "individuals",
                otype_single: "individual",
                headers: [
                    {text: '', value: 'buttons',sortable: false},
                    {text: 'Individual', value: 'individual'},
                    {text: 'Group', value: 'group'},
                    {text: 'Characteristica', value: 'characteristica'},
                ]
            }
        },
    }
</script>

<style scoped></style>
