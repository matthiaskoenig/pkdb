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
                <td>
                    {{table.item.application }}<br/>
                    {{table.item.time}} <span v-if="table.item.time_unit">[{{table.item.time_unit }}]</span><br />
                    {{ table.item.route }}<br/>
                    {{table.item.form}}
                </td>
                <td><a v-if="table.item.substance" :href="table.item.substance" :title="table.item.substance"><v-icon>{{ icon('intervention') }}</v-icon> </a>
                    <get-data :resource_url="table.item.substance" v-if="table.item.substance">
                        <div slot-scope="data">
                            {{ data.data.name }}
                        </div>
                    </get-data>
                </td>
                <td><characteristica-card :data="table.item" /></td>
            </template>
        </v-data-table>
    </v-card>
</template>

<script>
    import {lookup_icon} from "@/icons"
    import CharacteristicaCard from '../detail/CharacteristicaCard'

    export default {
        name: 'InterventionsTable',
        components: {
            CharacteristicaCard
        },
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
                    {text: 'Application', value: 'application'},
                    {text: 'Substance', value: 'substance'},
                    {text: 'Value', value: 'value'},
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
