<template>
    <v-card>
        <Heading :title="'Output: '+output.pk" :icon="icon('output')" :resource_url="resource_url"/>

        Group: <a v-if="output.group" :href="output.group" :title="output.group"><v-icon>{{ icon('group') }}</v-icon></a><br />
        Individual: <a v-if="output.individual" :href="output.individual" :title="output.individual">
            <v-icon>{{ icon('individual') }}</v-icon></a><br />

        <individual-button :individual_url="output.individual"/>

        Interventions: <span v-for="(intervention, index2) in output.interventions" :key="index2"><br />
                    <a :href="intervention" :title="intervention"><v-icon>{{ icon('intervention') }}</v-icon></a>&nbsp;</span><br />
        Tissue: {{output.tissue}}<br />
        Substance: <a v-if="output.substance" :href="output.substance" :title="output.substance"><v-icon>{{ icon('substance') }}</v-icon></a><br />
        Time: {{output.time}}<br />
        Time Unit: {{ output.time_unit }}<br />
        Unit: {{output.unit}}<br />
        Value: {{ output.value }}<br />
        Mean: {{ output.mean }}<br />
        Median: {{ output.median }}<br />
        Min: {{ output.min }}<br />
        Max: {{ output.max }}<br />
        Sd: {{ output.sd }}<br />
        Se: {{ output.se }}<br />
        Cv: {{ output.cv }}<br />

    </v-card>
</template>

<script>
    import {lookup_icon} from "@/icons"
    import IndividualButton from '../lib/IndividualButton'

    export default {
        name: "OutputDetail",
        components: {IndividualButton},
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