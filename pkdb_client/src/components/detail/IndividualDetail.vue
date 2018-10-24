<template>
    <v-card class="detail-card">
        <heading-toolbar :title="'Individual: '+individual.pk" :count="1" :icon="icon('individual')" :resource_url="resource_url"/>

        <v-layout>
            <v-flex>
        <individual-info :individual="individual"/>
            </v-flex>
        <v-flex>
            <v-layout wrap>
            <span v-for="item in this.individual.characteristica_all_final">
                <characteristica-card :data="item" />
            </span>
            </v-layout>
        </v-flex>
        </v-layout>
    </v-card>
</template>

<script>
    import {lookup_icon} from "@/icons"
    import CharacteristicaCard from './CharacteristicaCard';

    export default {
        name: "IndividualDetail",
        components: {
            CharacteristicaCard
        },
        props: {
            individual: {
                type: Object,
            },
            resource_url: {
                type: String
            }
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