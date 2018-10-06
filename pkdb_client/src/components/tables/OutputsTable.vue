<template>
    <v-card id="outputs-table">
        <heading-toolbar :count="data.count" :icon="icon('outputs')" title="Outputs" :resource_url="resource_url"/>
        <v-data-table
                :headers="headers"
                :items="data.entries"
                hide-actions
                class="elevation-1">
            <template slot="items" slot-scope="table">
                <td>
                    <LinkButton :to="'/outputs/'+ table.item.pk" :title="'Output: '+table.item.pk" :icon="icon('output')"/>
                    <JsonButton :resource_url="api + '/outputs_read/'+ table.item.pk +'/?format=json'"/>
                </td>
                <td>{{table.item.pktype }}</td>
                <td>
                    <a v-if="table.item.group" :href="table.item.group" :title="table.item.group">
                        <v-icon>{{ icon('group') }}</v-icon></a>
                </td>
                <td>
                    <a v-if="table.item.individual" :href="table.item.individual" :title="table.item.individual">
                        <v-icon>{{ icon('individual') }}</v-icon></a></td>
                <td>
                    <span v-for="(intervention, index2) in table.item.interventions" :key="index2">
                    <a :href="intervention" :title="intervention"><v-icon>{{ icon('intervention') }}</v-icon></a>&nbsp;
                    </span>
                </td>
                <td>{{table.item.tissue}}</td>
                <td>
                    <a v-if="table.item.substance" :href="table.item.substance" :title="table.item.substance">
                        <v-icon>{{ icon('substance') }}</v-icon> </a>
                </td>
                <td>{{table.item.time}} <span v-if="table.item.time_unit">[{{table.item.time_unit }}]</span></td>
                <td>{{table.item.unit}} </td>
                <td>{{table.item.value }} </td>
                <td>{{table.item.mean }}</td>
                <td>{{table.item.median }}</td>
                <td>{{table.item.min }}</td>
                <td>{{table.item.max }}</td>
                <td>{{table.item.sd }}</td>
                <td>{{table.item.se }}</td>
                <td>{{table.item.cv }}</td>
            </template>
        </v-data-table>
    </v-card>
</template>


<script>
    import {lookup_icon} from "@/icons"

    export default {
        name: 'OutputsTable',
        props: {
            data: Object,
            resource_url: String,
        },
        data() {
            return {
                headers: [
                    {text: 'Output', value: 'output'},
                    {text: 'Type', value: 'type'},
                    {text: 'Group', value: 'group'},
                    {text: 'Individual', value: 'individual'},
                    {text: 'Interventions', value: 'interventions'},
                    {text: 'Tissue', value: 'tissue'},
                    {text: 'Substance', value: 'substance'},
                    {text: 'Time', value: 'time'},
                    {text: 'Unit', value: 'unit'},
                    {text: 'Value', value: 'value'},
                    {text: 'Mean', value: 'mean'},
                    {text: 'Median', value: 'median'},
                    {text: 'Min', value: 'min'},
                    {text: 'Max', value: 'max'},
                    {text: 'Sd', value: 'sd'},
                    {text: 'Se', value: 'se'},
                    {text: 'Cv', value: 'cv'},
                ],
            }
        },
        computed: {
            api() {
                return this.$store.state.endpoints.api;
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