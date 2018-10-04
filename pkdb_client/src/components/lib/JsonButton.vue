<template>
<div class="json-button">
    <span v-if="resource_url">
        <md-button :href="resource_url" title="JSON" target="_blank" class="md-icon-button md-dense md-primary" :disabled="resource_url ? false : true">
            <font-awesome-icon icon="code"/>
        </md-button>
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