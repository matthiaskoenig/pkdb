<template>
    <v-card class="detail-card">
        <heading-toolbar :title="'Group: '+group.pk" :count="group.count" icon="group" :resource_url="resource_url"/>
        <v-layout>
            <v-flex>
                <v-btn small color="black" fab dark title="Group Size">{{ group.count }}</v-btn>
            </v-flex>
            <v-flex>
                <characteristica-card-deck :characteristica="group.characteristica_all_normed" />
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
            }
        },
        methods: {
        }
    }
</script>

<style scoped>
</style>