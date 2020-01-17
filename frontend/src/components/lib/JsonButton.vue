<template>
    <v-btn v-if="resource_url"
           slot="activator"
           fab
           dark
           small
           text
           color="black"
           :href="resource_url"
           :disabled="resource_url ? false : true"
           title="JSON for query"
    >
        <v-icon dark>fas fa-code</v-icon>
    </v-btn>
</template>

<script>
    export default {
        name: "JsonButton",
        props: {
            resource_url: String
        }
    }
</script>

<style scoped>

</style>