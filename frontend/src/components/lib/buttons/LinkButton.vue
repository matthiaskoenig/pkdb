<template>
    <span class="link-button">
        <v-btn fab
               small
               text
               :color="color"
               :to="to"
               :title="title"
               :disabled="to ? false : true"
        >
            <v-icon>{{ faIcon(icon) }}</v-icon>
        </v-btn>
    </span>
</template>

<script>
    import {lookupIcon} from "@/icons"

    export default {
        name: "LinkButton",
        props: {
            to: {
                type: String,
            },
            title: {
                type: String,
                required: true
            },
            icon: {
                type: String,
                required: true
            },
            color: {
                type: String,
                default: "black"
            },
        },
        methods: {
            faIcon(key) {
                return lookupIcon(key)
            },
        }
    }
</script>

<style>
</style>