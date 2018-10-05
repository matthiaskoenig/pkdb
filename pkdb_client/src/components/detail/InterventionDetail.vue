<template>
    <v-card>
        <Heading :title="'Intervention: '+intervention.pk" :count="1" :icon="icon('intervention')" :resource_url="resource_url"/>
    </v-card>
</template>

<script>
    import {lookup_icon} from "@/icons"
    import CharacteristicaCard from '../detail/CharacteristicaCard';

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