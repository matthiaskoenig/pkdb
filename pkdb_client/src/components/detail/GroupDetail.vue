<template>
    <v-card>
        <heading :title="'Group: '+group.pk" :count="group.count" :icon="icon('group')" :resource_url="resource_url"/>
        <group-info :group="group"/>


        <get-data :resource_url="characteristica_url">
            <div slot-scope="cdata">
            <span v-for="item in cdata.data.results">
                <characteristica-card :data="item" :resource_url="characteristica_url"/>
            </span>
            </div>
        </get-data>

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
        computed: {

            characteristica_url() {
                var url = this.$store.state.endpoints.api + '/characteristica_elastic/?ids='+ this.group.characteristica_all_final.join('__');
                console.log(url);

                return url;
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