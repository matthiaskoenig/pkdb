<template>
    <v-card>
        <heading :title="'Individual: '+individual.pk" :count="1" :icon="icon('individual')" :resource_url="resource_url"/>
        <individual-info :individual="individual"/>

        <span v-for="(c_url, index1) in individual.all_characteristica_final" :key="index1">
                <get-data :resource_url="c_url">
                    <div slot-scope="cdata">
                        <characteristica-card :data="cdata.data" :resource_url="c_url"/>
                    </div>
                </get-data>
        </span>
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