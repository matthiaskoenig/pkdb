<template>
    <v-card class="detail-card">
        <heading-toolbar :title="'Group: '+group.pk" :count="group.count" :icon="icon('group')" :resource_url="resource_url"/>
        <v-layout>
            <v-flex>
                <v-btn small color="black" fab dark title="Group Size">{{ group.count }}</v-btn>
            </v-flex>
            <v-flex>
                <v-layout wrap>
                    <span v-for="item in this.group.characteristica_all_normed">
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
        name: "GroupDetail",
        components: {
            CharacteristicaCard
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
            icon: function (key) {
                return lookup_icon(key)
            },
        }
    }
</script>

<style scoped>
</style>