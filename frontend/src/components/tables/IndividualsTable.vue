<template>
    <v-card flat>
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
                <LinkButton v-if="item.study"
                            :sid="item.study.sid"
                            show_type="study"
                            :title="'Study: '+item.study.name"
                            icon="study"
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
                    {text: 'Individual', value: 'individual' ,sortable: false},
                    {text: 'Group', value: 'group', sortable: false},
                    {text: 'Characteristica', value: 'characteristica', sortable: false},
                ]
            }
        },
      methods:{

      }
    }
</script>

<style scoped></style>
