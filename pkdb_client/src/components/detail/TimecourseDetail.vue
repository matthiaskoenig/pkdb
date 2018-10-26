<template>
    <v-card>
        <Heading :title="'Timecourse: '+timecourse.pk" :icon="icon('timecourse')" :resource_url="resource_url"/>

        Group: <a v-if="timecourse.group" :href="timecourse.group" :title="timecourse.group"><v-icon>{{ icon('group') }}</v-icon></a><br />
        Individual: <a v-if="timecourse.individual" :href="timecourse.individual" :title="timecourse.individual">
        <v-icon>{{ icon('individual') }}</v-icon></a><br />
        Interventions: <span v-for="(intervention, index2) in timecourse.interventions" :key="index2"><br />
                    <a :href="intervention" :title="intervention"><v-icon>{{ icon('intervention') }}</v-icon></a>&nbsp;</span><br />
        Tissue: {{timecourse.tissue}}<br />
        Substance: <a v-if="timecourse.substance" :href="timecourse.substance" :title="timecourse.substance"><v-icon>{{ icon('substance') }}</v-icon></a><br />
        Time: {{timecourse.time}}<br />
        Time Unit: {{ timecourse.time_unit }}<br />
        Unit: {{timecourse.unit}}<br />
        Value: {{ timecourse.value }}<br />
        Mean: {{ timecourse.mean }}<br />
        Median: {{ timecourse.median }}<br />
        Min: {{ timecourse.min }}<br />
        Max: {{ timecourse.max }}<br />
        Sd: {{ timecourse.sd }}<br />
        Se: {{ timecourse.se }}<br />
        Cv: {{ timecourse.cv }}<br />

        <TimecoursePlot :timecourse="timecourse"/>

    </v-card>
</template>

<script>
    import {lookup_icon} from "@/icons"
    import TimecoursePlot from '@/components/plots/TimecoursePlot';

    export default {
        name: "TimecourseDetail",
        components: {
            TimecoursePlot: TimecoursePlot,
        },
        props: {
            timecourse: {
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