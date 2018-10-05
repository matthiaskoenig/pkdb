<template>
    <v-card>
        <Heading :title="'Individual: '+individual.pk" :count="1" :icon="icon('individual')" :resource_url="resource_url"/>
        <IndividualInfo :individual="individual"/>

        <span v-for="(c_url, index1) in individual.all_characteristica_final" :key="index1">
                <GetData :resource_url="c_url">
                    <div slot-scope="cdata">
                        <CharacteristicaCard :data="cdata.data" :resource_url="c_url"/>
                    </div>
                </GetData>
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