<template>
    <v-card  id="interventions-table">
        <heading-toolbar :count="data.count" :icon="icon('interventions')" title="Interventions" :resource_url="resource_url"/>
        <v-data-table
                :headers="headers"
                :items="data.entries"
                hide-actions
                class="elevation-1">
            <template slot="items" slot-scope="table">

                <td>
                    <LinkButton :to="'/interventions/'+ table.item.pk" :title="'Group: '+table.item.pk" :icon="icon('intervention')"/>
                    <JsonButton :resource_url="api + '/interventions_read/'+ table.item.pk +'/?format=json'"/>
                </td>
                <td>{{table.item.name }}</td>
                <td>{{table.item.category }}</td>
                <td>{{table.item.choice }}</td>
                <td>{{table.item.route }}</td>
                <td>{{table.item.form}}</td>
                <td>{{table.item.application}}</td>
                <td><a v-if="table.item.substance" :href="table.item.substance" :title="table.item.substance"><v-icon>{{ icon('substance') }}</v-icon> </a></td>
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
        name: 'InterventionsTable',
        props: {
            data: Object,
            resource_url: String,
        },
        data() {
            return {
                headers: [
                    {text: 'Intervention', value: 'intervention'},
                    {text: 'Name', value: 'name'},
                    {text: 'Category', value: 'category'},
                    {text: 'Choice', value: 'choice'},
                    {text: 'Route', value: 'route'},
                    {text: 'Form', value: 'form'},
                    {text: 'Application', value: 'application'},
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
<style>


</style>
