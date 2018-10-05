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


        <!--
        <md-list class="md-double-line">
            <div class="md-list-item-text">
                <span>{{ group.name }}</span>
                <span>Name</span>
            </div>
            <div class="md-list-item-text">
                <span>{{ group.count }}</span>
                <span>Count</span>
            </div>
            <div class="md-list-item-text">
                <span>{{ group.study_name }}</span>
                <span>Study</span>
            </div>
        </md-list>
        -->

        <md-badge title="Individuals" v-if="group.individuals.length" :md-content="group.individuals.length">
            <font-awesome-icon class="md-icon" icon="user"/>
        </md-badge>
    </div>
</template>

<script>
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
                    { header: 'Today' },
                    {
                        avatar: 'https://cdn.vuetifyjs.com/images/lists/1.jpg',
                        title: 'Brunch this weekend?',
                        subtitle: "<span class='text--primary'>Ali Connors</span> &mdash; I'll be in your neighborhood doing errands this weekend. Do you want to hang out?"
                    },
                    { divider: true, inset: true },
                    {
                        avatar: 'https://cdn.vuetifyjs.com/images/lists/2.jpg',
                        title: 'Summer BBQ <span class="grey--text text--lighten-1">4</span>',
                        subtitle: "<span class='text--primary'>to Alex, Scott, Jennifer</span> &mdash; Wish I could come, but I'm out of town this weekend."
                    },
                    { divider: true, inset: true },
                    {
                        avatar: 'https://cdn.vuetifyjs.com/images/lists/3.jpg',
                        title: 'Oui oui',
                        subtitle: "<span class='text--primary'>Sandra Adams</span> &mdash; Do you have Paris recommendations? Have you ever been?"
                    }
                ]
            }
        }
    }
</script>

<style scoped>

</style>