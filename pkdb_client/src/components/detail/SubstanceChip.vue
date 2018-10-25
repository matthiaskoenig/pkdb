<template>
    <div class="text-xs-center">
        <v-chip v-if="title" color="success">
            <v-icon small>{{ icon('substance') }}</v-icon>&nbsp;
            <text-highlight :queries="search.split(/[ ,]+/)">{{ title }}</text-highlight>
        </v-chip>
    </div>
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