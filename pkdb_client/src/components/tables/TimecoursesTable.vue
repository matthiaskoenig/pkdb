<template>
    <v-card id="timecourses-table">
        <heading-toolbar :count="data.count" :icon="icon('timecourses')" title="Timecourses" :resource_url="resource_url"/>
        <v-data-table
                :headers="headers"
                :items="data.entries"
                hide-actions
                class="elevation-1">
            <template slot="items" slot-scope="table">
                <td>
                    <LinkButton :to="'/timecourses/'+ table.item.pk" :title="'Timecourse: '+table.item.pk" :icon="icon('output')"/>
                    <JsonButton :resource_url="api + '/timecourses_read/'+ table.item.pk +'/?format=json'"/>
                </td>
                <td>{{table.item.pktype }}</td>
                <td>
                    <a v-if="table.item.group" :href="table.item.group" :title="table.item.group">
                        <v-icon>{{ icon('group') }}</v-icon></a>
                    <get-data :resource_url="table.item.group">
                        <div slot-scope="data">
                            {{ data.data.name }}
                        </div>
                    </get-data>
                </td>
                <td>
                    <a v-if="table.item.individual" :href="table.item.individual" :title="table.item.individual">
                        <v-icon>{{ icon('individual') }}</v-icon></a></td>
                <td>
                    <span v-for="(intervention_url, index2) in table.item.interventions" :key="index2">
                    <a :href="intervention_url" :title="intervention"><v-icon>{{ icon('intervention') }}</v-icon></a>&nbsp;
                        <get-data :resource_url="intervention_url">
                        <div slot-scope="data">
                            {{ data.data.name }}
                        </div>
                    </get-data>
                    </span>
                </td>
                <td>{{table.item.tissue}}</td>
                <td>
                    <a v-if="table.item.substance" :href="table.item.substance" :title="table.item.substance">
                        <v-icon>{{ icon('substance') }}</v-icon> </a>
                    <get-data :resource_url="table.item.substance">
                        <div slot-scope="data">
                            {{ data.data.name }}
                        </div>
                    </get-data>
                </td>
                <td>
                    <TimecoursePlot :timecourse="table.item"/>
                </td>
            </template>
        </v-data-table>
    </v-card>
</template>

<script>
    import {lookup_icon} from "@/icons"
    import TimecoursePlot from '@/components/plots/TimecoursePlot';

    export default {
        name: 'TimecoursesTable',
        components: {
            TimecoursePlot: TimecoursePlot,
        },
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
                    {text: 'Timecourse', value: 'timecourse'},
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