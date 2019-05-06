<template>
    <span v-if="resource_url">
        <v-btn slot="activator" fab dark small flat color="black" :href="resource_url"
               :disabled="resource_url ? false : true" title="JSON for query">
            <v-icon dark>fas fa-code</v-icon>
        </v-btn>
    </span>
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