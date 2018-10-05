<template>
    <div id="group-info">
        <v-list two-line>
            <template v-for="(item, index) in items">
                <v-subheader
                        v-if="item.header"
                        :key="item.header"
                >
                    {{ item.header }}
                </v-subheader>

                <v-divider
                        v-else-if="item.divider"
                        :inset="item.inset"
                        :key="index"
                ></v-divider>

                <v-list-tile
                        v-else
                        :key="item.title"
                        avatar
                        @click=""
                >
                    <v-list-tile-avatar>
                        <img :src="item.avatar">
                    </v-list-tile-avatar>

                    <v-list-tile-content>
                        <v-list-tile-title v-html="item.title"></v-list-tile-title>
                        <v-list-tile-sub-title v-html="item.subtitle"></v-list-tile-sub-title>
                    </v-list-tile-content>
                </v-list-tile>
            </template>
        </v-list>
    </div>
</template>

<script>
    import {lookup_icon} from "@/icons"
    export default {
        name: "GroupInfo",
        props: {
            group: {
                type: Object,
                required: true,
            }
        },
        computed: {
            items() {
                return [
                    {
                        subtitle: 'Name',
                        title: this.group.name
                    },
                    {
                        subtitle: 'Count',
                        title: this.group.count
                    },
                    {
                        subtitle: 'Study',
                        title: this.group.study_name
                    },
                    {
                        subtitle: 'Individuals',
                        title: this.individuals_count
                    }
                ]
            },
            individuals_count(){
                return this.group.individuals.count
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