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
                <link-button :to="'/groups/'+ item.pk"
                             :title="'Group: '+item.pk"
                             icon="group"
                />

                <!--<link-button :to="'/studies/'+ item.study.pk" :title="'Study: '+item.study.name" :icon="icon('study')"/>-->
                <json-button :resource_url="api + 'groups/'+ item.pk +'/?format=json'"/>
            </template>
            <template v-slot:item.name="{ item }">
                <object-chip :object="item"
                             otype="group"
                             :search="search"
                />
            </template>
            <template v-slot:item.parent="{ item }">
                <object-chip v-if="item.parent"
                             :object="item.parent"
                             otype="group"
                             :search="search"
                />
            </template>
            <template v-slot:item.characteristica="{ item }">
                <characteristica-card-deck :characteristica="item.characteristica_all_normed" />
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
                    {text: 'Name', value: 'name'},
                    {text: 'Parent', value: 'parent'},
                    {text: 'Characteristica', value: 'characteristica'},
                ]
            }
        },
    }
</script>

<style scoped>

</style>
