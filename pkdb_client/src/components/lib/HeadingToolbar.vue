<template>
    <v-toolbar id="heading-toolbar" color="secondary" dark>
            <Heading :count="count" :icon="icon" :title="title" :resource_url="resource_url"/>
    </v-toolbar>
</template>

<script>
    export default {
        name: "HeadingToolbar",
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

<style>
</style>