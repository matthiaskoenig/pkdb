<template>
    <span class="text-xs-center">
        <v-chip v-if="title" color="warning">
            <v-icon small>{{ icon('individual') }}</v-icon>&nbsp;
            <text-highlight :queries="search.split(/[ ,]+/)">{{ title }}</text-highlight>
        </v-chip>
    </span>
</template>

<script>
    import {lookup_icon} from "@/icons"

    export default {
        name: "IndividualChip",
        props: {
            title: {
                type: String,
                required: true
            },
            search: {
                type: String,
                default: ''
            },
        },
        methods: {
            icon(key) {
                return lookup_icon(key)
            },
        }
    }
</script>

<style scoped>

</style>