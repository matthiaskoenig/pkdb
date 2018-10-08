<template>
    <v-card>
        <Heading :title="'Output: '+output.pk" :icon="icon('output')" :resource_url="resource_url"/>
        <div>
        Group:
        <get-data v-if="output.group" :resource_url="output.group">
            <span slot-scope="data">
                <group-button :group="data.data"/>
            </span>
        </get-data><br />

        Individual:
        <get-data v-if="output.individual" :resource_url="output.individual">
            <span slot-scope="data">
                <individual-button :individual="data.data"/>
            </span>
        </get-data><br />

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
        </div>

    </v-card>
</template>

<script>
    import {lookup_icon} from "@/icons"
    import IndividualButton from '../lib/IndividualButton'
    import GroupButton from '../lib/GroupButton'

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