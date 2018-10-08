<template>
    <v-card id="studies-table">
        <heading-toolbar :count="data.count" :icon="icon('study')" title="Studies" :resource_url="resource_url"/>
        <v-data-table
                :headers="headers"
                :items="data.entries"
                hide-actions
                class="elevation-1">
            <template slot="items" slot-scope="table">
                <td>
                    <LinkButton :to="'/studies/'+ table.item.pk" :title="'Study: '+table.item.pk" :icon="icon('study')"/>
                    <JsonButton :resource_url="api + '/studies_read/'+ table.item.pk +'/?format=json'"/>
                </td>
                <td>{{ table.item.name }}</td>
                <td><a v-if="table.item.reference" :href="table.item.reference" :title="table.item.reference">
                    <v-icon>{{ icon('reference') }}</v-icon>

                </a>
                </td>
                <td>
                    <UserAvatar :user="table.item.creator"/>
                </td>
                <td>
                    <span v-for="(c, index2) in table.item.curators" :key="index2"><user-avatar :user="c"/></span>
                </td>
                <td>
                    <span v-for="(c, index2) in table.item.substances" :key="index2"><substance-chip :substance="c"/></span>
                </td>
                <td>
                    <v-container fluid grid-list-md>
                        <v-data-iterator  :items="table.item.files"
                                          rows-per-page-items=3
                                          content-tag="v-layout"
                                          wrap row>
                            <span slot="item" slot-scope="props" xs12 sm6  md4 lg3>
                                <file-chip  :file="props.item"/>
                            </span>
                        </v-data-iterator>
                    </v-container>
                </td>
                <td>
                    <a v-if="table.item.groupset" :href="table.item.groupset" :title="table.item.groupset">
                        <v-icon>{{ icon('groups') }}</v-icon></a>
                </td>
                <td>
                    <a v-if="table.item.individualset" :href="table.item.individualset" :title="table.item.individualset">
                        <v-icon>{{ icon('individuals') }}</v-icon></a>
                </td>
                <td>
                    <a v-if="table.item.interventionset" :href="table.item.interventionset" :title="table.item.interventionset">
                        <v-icon>{{ icon('interventions') }}</v-icon></a>
                </td>
                <td>
                    <a v-if="table.item.outputset" :href="table.item.outputset" :title="table.item.outputset">
                        <v-icon>{{ icon('outputs') }}</v-icon></a>
                </td>
            </template>
        </v-data-table>
    </v-card>
</template>

<script>
    import {lookup_icon} from "@/icons"
    import SubstanceChip from "../detail/SubstanceChip"
    import FileChip from "../detail/FileChip"

    export default {
        name: 'StudiesTable',
        components: {
            SubstanceChip: SubstanceChip,
            FileChip:FileChip,
        },
        props: {
            data: Object,
            resource_url: String,
        },
        data() {
            return {
                headers: [
                    {text: 'Study', value: 'study'},
                    {text: 'Name', value: 'name'},
                    {text: 'Reference', value: 'reference'},
                    {text: 'Creator', value: 'creator'},
                    {text: 'Curators', value: 'curators'},
                    {text: 'Substances', value: 'substances'},
                    {text: 'Files', value: 'files'},
                    {text: 'Groupset', value: 'groupset'},
                    {text: 'IndividualSet', value: 'individualset'},
                    {text: 'InterventionSet', value: 'interventionset'},
                    {text: 'OutputSet', value: 'outputset'},
                ],
            }
        },
        computed: {
            api() {
                return this.$store.state.endpoints.api;
            }
        },
        methods: {
            icon(key) {
                return lookup_icon(key)
            },
        }

    }
</script>

<style></style>