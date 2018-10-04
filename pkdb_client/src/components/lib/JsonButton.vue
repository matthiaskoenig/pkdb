<template>
<div class="json-button">
    <span v-if="resource_url">
        <v-btn fab dark small color="success" :to="resource_url" :disabled="resource_url ? false : true" :title="JSON">
            <v-icon dark>fas fa-code</v-icon>
        </v-btn>
    </span>
</div>
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