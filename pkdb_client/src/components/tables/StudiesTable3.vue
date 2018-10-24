<template>
    <v-card>
        <table-toolbar :otype="otype" :count="count" :url="url" @update="searchUpdate"/>
        <v-data-table
                :headers="headers"
                :items="entries"
                :pagination.sync="pagination"
                :total-items="count"
                :loading="loading"
                :class="table_class"
        >
            <template slot="items" slot-scope="table">
                <td>
                    <LinkButton :to="'/studies/'+ table.item.pk" :title="'Study: '+table.item.pk" :icon="icon('study')"/>
                    <LinkButton :to="'/references/'+ table.item.reference.sid" :title="'Refernce: '+table.item.reference.sid" :icon="icon('reference')"/>
                    <JsonButton :resource_url="api + '/studies_elastic/'+ table.item.pk +'/?format=json'"/>
                    <export-format-button :resource_url="api + '/studies/'+ table.item.pk +'/?format=json'"/>

                </td>
                <td>
                    <text-highlight :queries="search.split(/[ ,]+/)"> {{ table.item.name }}</text-highlight>
                </td>
                <td>
                    <span v-for="description in table.item.descriptions" > {{description.text}}</span>
                    <comments :comments="table.item.comments" :search="search"/>

                </td>
                <td>
                    <UserAvatar :user="table.item.creator" :search="search"/>
                </td>
                <td>
                    <span v-for="(c, index2) in table.item.curators" :key="index2"><user-avatar :user="c" :search="search"/></span>
                </td>
                <td>
                    <span v-for="(c, index2) in table.item.substances" :key="index2"><substance-chip :title="c" :search="search"/></span>
                </td>
                <td>
                    <v-container fluid grid-list-md>
                        <v-data-iterator  :items="table.item.files"
                                          content-tag="v-layout"
                                          wrap row>
                            <span slot="item" slot-scope="props" xs12 sm6 md4 lg3>
                               <file-chip :file="props.item.file" :search="search"/>
                            </span>
                        </v-data-iterator>
                    </v-container>
                </td>
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
        name: "GroupsTable3",
        components: {
            NoData,
            TableToolbar,
            CharacteristicaCard,
        },
        mixins: [searchTableMixin],
        data () {
            return {
                otype: "studies",
                otype_single: "study",
                headers: [
                    {text: '', value: 'buttons',sortable: false},
                    {text: 'Name', value: 'name'},
                    {text: 'Descriptions', value: 'descriptions'},
                    {text: 'Creator', value: 'creator'},
                    {text: 'Curators', value: 'curators',sortable: false},
                    {text: 'Substances', value: 'substances',sortable: false},
                    {text: 'Files', value: 'files',sortable: false},
                ],
            }
        },
    }
</script>

<style scoped></style>