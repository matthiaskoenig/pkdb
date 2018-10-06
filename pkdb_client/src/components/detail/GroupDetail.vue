<template>
    <v-card>
        <Heading :title="'Group: '+group.pk" :count="group.count" :icon="icon('group')" :resource_url="resource_url"/>
        <GroupInfo :group="group"/>

        <!-- <span v-for="(c_url, index1) in group.characteristica_all_final" :key="index1">
                <GetData :resource_url="c_url">
                    <div slot-scope="cdata">
                        <CharacteristicaCard :data="cdata.data" :resource_url="c_url"/>
                    </div>
                </GetData>
        </span> -->
        <GetData :resource_url="characteristica_url">
            <div slot-scope="cdata">
            <span v-for="item in cdata.data.results">
                <CharacteristicaCard :data="item"/>
            </span>
            </div>
        </GetData>

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