<template>
    <v-card>
        <Heading :title="'Output: '+output.pk" :count="1" :icon="icon('output')" :resource_url="resource_url"/>

        Group: <a v-if="table.item.group" :href="table.item.group" :title="table.item.group"><v-icon>{{ icon('group') }}</v-icon></a><br />
        Individual"><a v-if="table.item.individual" :href="table.item.individual" :title="table.item.individual"><v-icon>{{ icon('individual') }}</v-icon></a><br />
        Interventions"><span v-for="(intervention, index2) in table.item.interventions" :key="index2"><br />
                    <a :href="intervention" :title="intervention"><v-icon>{{ icon('intervention') }}</v-icon></a>&nbsp;</span><br />
        Tissue: {{table.item.tissue}}<br />
        Substance: <a v-if="table.item.substance" :href="table.item.substance" :title="table.item.substance"><v-icon>{{ icon('substance') }}</v-icon></a><br />
        Time: {{table.item.time}}<br />
        Time Unit: {{ table.item.time_unit }}<br />
        Unit: {{table.item.unit}}<br />
        Value: {{ table.item.value }}<br />
        Mean: {{ table.item.mean }}<br />
        Median: {{ table.item.median }}<br />
        Min: {{ table.item.min }}<br />
        Max: {{ table.item.max }}<br />
        Sd: {{ table.item.sd }}<br />
        Se: {{ table.item.se }}<br />
        Cv: {{ table.item.cv }}<br />

    </v-card>
</template>

<script>
    import {lookup_icon} from "@/icons"

    export default {
        name: "OutputDetail",
        props: {
            output: {
                type: Object,
            },
            resource_url: {
                type: String
            }
        },
        computed: {
        },
        methods: {
            icon: function (key) {
                return lookup_icon(key)
            },
        }
    }
</script>

<style scoped>

</style>