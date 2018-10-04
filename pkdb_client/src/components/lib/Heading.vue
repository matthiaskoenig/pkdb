<template>
    <md-badge :md-content="count">
        <h1 class="md-title"><font-awesome-icon v-if="icon" :icon="icon" /> {{ title }}</h1>
        <JsonButton :resource_url="resource_url"/>
    </md-badge>
</template>

<script>
    export default {
        name: "Heading",
        props: {
            title: {
                type: String,
            },
            count: {
                type: Number,
            },
            icon: {
                type: String,
            },
            resource_url: {
                type: String
            }
        }
    }
</script>

<style scoped>
</style>