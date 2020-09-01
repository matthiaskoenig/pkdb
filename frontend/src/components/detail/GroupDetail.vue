<template>
    <v-card class="detail-card">
        <v-layout>
            <v-flex>
                <v-btn small color="black" fab dark title="Group Size">{{ group.count }}</v-btn>
            </v-flex>
            <v-flex>
                <characteristica-card-deck :characteristica="group.characteristica" />
            </v-flex>
        </v-layout>
    </v-card>
</template>

<script>
    import CharacteristicaCardDeck from './CharacteristicaCardDeck';

    export default {
        name: "GroupDetail",
        components: {
            CharacteristicaCardDeck
        },
        props: {
            group: {
                type: Object,
            },
            resource_url: {
                type: String
            },
          pk: {
            type: String
          }
        },
        methods: {

        }
    }
</script>

<style scoped>
</style>