<template>
    <v-card>
        <Heading :title="'Intervention: '+intervention.pk" :icon="icon('intervention')" :resource_url="resource_url"/>

        Name: {{intervention.name }}<br />
        Category: {{intervention.category }}<br />
        Choice: {{intervention.choice }}<br />
        Route: {{intervention.route }}<br />
        Form: {{intervention.form}}<br />
        Application: {{intervention.application}}<br />
        Substance: <a v-if="intervention.substance" :href="intervention.substance" :title="intervention.substance"/>
        <v-icon>{{ icon('substance') }}</v-icon></a><br />
        Time:  {{intervention.time}} <br />
        Time Unit:  {{intervention.time_unit }} <br />
        Unit:  {{intervention.unit}} <br />
        Value:  {{intervention.value }} <br />
        Mean:  {{intervention.mean }}<br />
        Median:  {{intervention.median }}<br />
        Min: {{intervention.min }}<br />
        Max: {{intervention.max }}<br />
        Sd: {{intervention.sd }}<br />
        Se: {{intervention.se }}<br />
        Cv: {{intervention.cv }}<br />
    </v-card>
</template>

<script>
    import {lookup_icon} from "@/icons"
    import CharacteristicaCard from './CharacteristicaCard';

    export default {
        name: "InterventionDetail",
        components: {
            CharacteristicaCard
        },
        props: {
            intervention: {
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