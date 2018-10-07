<template>
    <div class="group-info">
        <v-layout>
            <v-flex xs4>
                <span class="attr">Group Name</span><br />
                {{ group.name }}
            </v-flex>
            <v-flex xs4>
                <span class="attr">Group Size</span><br />
                {{ group.count }}
            </v-flex>
            <v-flex xs4>
                <span class="attr">Group Individuals</span><br />
                <span v-if="(group.individuals && group.individuals.length>0)">
                    <v-icon>fa fa-check-circle</v-icon> {{ group.individuals.length }}"</span>
                <span v-else>
                    <v-icon>fa fa-times-circle</v-icon>
                </span>
            </v-flex>
        </v-layout>
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
        methods: {
            icon: function (key) {
                return lookup_icon(key)
            },
        }
    }
</script>

<style scoped>

</style>