<template>
    <md-badge :md-content="count">
        <h1 class="md-title"><font-awesome-icon :icon="icon" /> {{ title }}</h1>
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
            }
        }
    }
</script>

<style scoped>
</style>