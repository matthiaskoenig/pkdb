<template>
    <v-card>
        <Heading :title="'Output: '+output.pk" icon="output" :resource_url="resource_url"/>
        <div>
        Group:
        <get-data v-if="output.group" :resource_url="group_url(output.group.pk)">
            <span slot-scope="data">
                <group-button :group="data.data"/>
            </span>
        </get-data><br />

        Individual:
        <get-data v-if="output.individual" :resource_url="individual_url(output.individual.pk)">
            <span slot-scope="data">
                <individual-button :individual="data.data"/>
            </span>
        </get-data><br />

        Interventions: <span v-for="(intervention, index2) in output.interventions" :key="index2"><br />
                    <a :href="intervention_url(intervention.pk)" :title="intervention.name"><v-icon>{{ faIcon('intervention') }}</v-icon></a>&nbsp;</span><br />
        Tissue: {{output.tissue}}<br />
        Substance:           <substance-chip :title="output.substance.name"/>
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
    import {lookupIcon} from "@/icons"
    import {UrlMixin} from "../tables/mixins";

    export default {
        name: "OutputDetail",
        components: {

        },
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
        mixins : [UrlMixin],
        methods: {
            icon: function (key) {
                return lookupIcon(key)
            },
        }
    }
</script>

<style scoped>

</style>