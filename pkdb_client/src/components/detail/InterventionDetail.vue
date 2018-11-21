<template>
    <v-card>
        <heading-toolbar :title="'Intervention: '+intervention.pk" :icon="icon('intervention')" :resource_url="resource_url"/>

        <v-layout wrao>
            <v-flex xs4>
                <characteristica-card :data="intervention" />
            </v-flex>
            <v-flex xs4>
                <span class="attr">Name</span><br /> {{intervention.name }}<br />
                <span class="attr">Category</span><br /> {{intervention.category }}<br />
                <span class="attr">Choice</span><br /> {{intervention.choice }}<br />
                <span class="attr">Route</span><br /> {{intervention.route }}<br />
                <span class="attr">Form</span><br /> {{intervention.form}}<br />
                <span class="attr">Application</span><br /> {{intervention.application}}<br />
                <span class="attr">Substance</span><br /> {{intervention.substance}}<br />

                <span class="attr">Time</span><br /> {{intervention.time}} <br />
                <span class="attr">Time Unit</span><br /> {{intervention.time_unit }} <br />
            </v-flex>
            <v-flex xs4>
                <span class="attr">Unit</span><br /> {{intervention.unit}} <br />
                <span class="attr">Value</span><br /> {{intervention.value }} <br />
                <span class="attr">Mean</span><br /> {{intervention.mean }}<br />
                <span class="attr">Median</span><br /> {{intervention.median }}<br />
                <span class="attr">Min</span><br /> {{intervention.min }}<br />
                <span class="attr">Max</span><br /> {{intervention.max }}<br />
                <span class="attr">Sd</span><br /> {{intervention.sd }}<br />
                <span class="attr">Se</span><br /> {{intervention.se }}<br />
                <span class="attr">Cv</span><br /> {{intervention.cv }}<br />
            </v-flex>

        </v-layout>
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