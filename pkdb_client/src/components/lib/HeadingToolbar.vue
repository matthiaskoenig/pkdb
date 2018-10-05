<template>
    <v-toolbar id="heading-toolbar" color="secondary" dark dense>
        <v-toolbar-title>
            <Heading :count="count" :icon="icon" :title="title" :resource_url="resource_url"/>
        </v-toolbar-title>
    </v-toolbar>
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

<style>
</style>