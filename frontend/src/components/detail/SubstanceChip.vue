<template>

    <span class="text-xs-center">
        <v-chip v-if="title" color="#00a087">

            <v-icon small color="black">{{ icon('substance') }}</v-icon>&nbsp;
            <text-highlight :queries="search.split(/[ ,]+/)">{{ title }}</text-highlight>
        </v-chip>
    </span>

</template>

<script>
    import {lookup_icon} from "@/icons"

    export default {
        name: "SubstanceChip",
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