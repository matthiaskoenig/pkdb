<template>
    <span class="link-button">
        <v-btn color="primary" fab small dark :to="to" :title="title" :disabled="to ? false : true">
            <v-icon>{{ icon }}</v-icon>
        </v-btn>
    </span>
</template>

<script>
    export default {
        name: "DetailButton",
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
        },
    }
</script>

<style scoped>

</style>