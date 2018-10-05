<template>
    <v-card>
    <v-card-title>
        <Heading :count="data.count" :icon="icon('study')" title="Studies" :resource_url="resource_url"/>
    </v-card-title>

    <v-data-table
            :headers="headers"
            :items="data.entries"
            hide-actions
            class="elevation-1">
        <template slot="items" slot-scope="table">
            <td>
                <LinkButton :to="'studies/'+ table.item.pk" :title="'Study: '+table.item.pk" :icon="icon('study')"/>
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
                <span v-for="(c, index2) in table.item.curators" :key="index2"><UserAvatar :user="c"/></span>
            </td>
            <td>
                <span v-for="(c, index2) in table.item.substances" :key="index2">

                    <v-icon>{{ icon('substance') }}</v-icon>{{c.name}}
                </span>
            </td>
            <td>
                <span v-for="(f, index2) in table.item.files" :key="index2"><a :href="f" :title="f">
                        <v-icon>{{ icon('file') }}</v-icon></a>&nbsp;</span>
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
    export default {
        name: 'StudiesTable',
        props: {
            data: Object,
            resource_url: String,
        },
        data() {
            return {
                headers: [
                    {text: 'Study', value: 'studies'},
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
        methods: {
            icon: function (key) {
                return lookup_icon(key)
            },
        }
    }
</script>

<style></style>