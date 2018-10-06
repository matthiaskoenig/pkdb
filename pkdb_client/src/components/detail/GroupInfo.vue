<template>
    <v-card flat dark class="accent">
    <v-layout id="group-info" row wrap>
        <v-flex>
            <info-text>Name</info-text><br/>
            {{ group.name }}
        </v-flex>
        <v-flex>
            <info-text>Group Size</info-text><br/>
            {{ group.count }}
        </v-flex>
        <v-flex v-if="(group.individuals && group.individuals.length>0)">
            <info-text>individuals</info-text><br/>
            {{ group.individuals.length }}
        </v-flex>
    </v-layout>
    </v-card>
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