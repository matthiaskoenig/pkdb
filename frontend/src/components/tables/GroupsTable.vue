<template>
    <v-sheet flat>
        <table-toolbar :otype="otype" :count="count" :autofocus="autofocus" :url="url" @update="searchUpdate"/>
        <v-data-table
                fill-height
                fixed-header
                :height="windowHeight"
                dense
                :headers="headers"
                :items="entries"
                disable-sort
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
                <json-button :resource_url="api + 'groups/' + item.pk + '/?format=json'"/>
            </template>
            <template v-slot:item.name="{ item }">
                <object-chip :object="item"
                             otype="group"
                             :count="item.count"
                             :search="search"
                />
            </template>
            <!--
            <template v-slot:item.parent="{ item }">
                <object-chip v-if="item.parent"
                             :object="item.parent"
                             otype="group"
                             :search="search"
                />
            </template>
            -->
            <template v-slot:item.characteristica="{ item }">
                <characteristica-card-deck :characteristica="item.characteristica" />
            </template>
            <no-data/>
        </v-data-table>
    </v-sheet>
</template>

<script>
    import {searchTableMixin, UrlMixin} from "./mixins";
    import TableToolbar from './TableToolbar';
    import NoData from './NoData';
    import CharacteristicaCardDeck from '../detail/CharacteristicaCardDeck'

    export default {
        name: "GroupsTable",
        components: {
            CharacteristicaCardDeck,
            NoData,
            TableToolbar,
        },
        mixins: [searchTableMixin, UrlMixin],
        data () {
            return {
                otype: "groups",
                otype_single: "group",
                headers: [
                    {text: '', value: 'buttons', sortable: false},
                    {text: 'Name', value: 'name',  sortable: false},

                    // {text: 'Parent', value: 'parent'},
                    {text: 'Characteristica', value: 'characteristica', sortable: false},
                ]
            }
        },
    }
</script>

<style scoped>

</style>
