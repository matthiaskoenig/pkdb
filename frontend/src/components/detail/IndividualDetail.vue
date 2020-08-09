<template>
    <v-card class="detail-card">
        <heading-toolbar :title="'Individual: '+ individual.pk"
                         :count="1"
                         icon="individual"
                         :resource_url="resource_url"
        />
        <v-layout>
            <v-flex xs2>
                <span class="attr">Individual Name</span><br />
                {{ individual.name }}
            </v-flex>
            <v-flex xs10>
                <characteristica-card-deck :characteristica="this.individual.characteristica_all_normed" />
            </v-flex>
        </v-layout>
    </v-card>
</template>

<script>
    import CharacteristicaCardDeck from './CharacteristicaCardDeck';

    export default {
        name: "IndividualDetail",
        components: {
            CharacteristicaCardDeck
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
        }
    }
</script>

<style scoped>

</style>