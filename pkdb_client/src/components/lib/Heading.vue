<template>
    <span id="heading">
        <v-icon :title="title">{{ icon }}</v-icon>&nbsp;
        <v-badge v-if="count" right color="red">
            <span slot="badge">{{ count }}</span>
            <span class="heading-title">{{ title }}</span>
        </v-badge>&nbsp;
        <span v-if="!count" class="heading-title">{{ title }}</span>
        <JsonButton :resource_url="resource_url"/>
    </span>
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
    .heading-title {
        font-size: large;
    }
</style>