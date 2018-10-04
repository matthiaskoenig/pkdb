<template>
<div class="json-button">
    <md-button :href="resource_url" title="JSON" target="_blank" class="md-icon-button md-raised" :disabled="resource_url ? false : true">
        <font-awesome-icon icon="code"/>

    </md-button>
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