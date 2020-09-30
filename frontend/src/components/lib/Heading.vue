<template>
    <span id="heading">
        <scatter-icon v-if="icon==='scatters'" class="v-icon--left"/>
        <v-icon v-else :title="title"
                color="black"
        >
            {{ icon }}
        </v-icon>&nbsp;
        <v-badge v-if="count" right color="black">
            <span slot="badge">{{ count }}</span>
            <span class="heading-title">{{ title }}</span>
        </v-badge>&nbsp;
        <span v-if="!count" class="heading-title">{{ title }}</span>
        <JsonButton :resource_url="resource_url"/>
    </span>
</template>

<script>

import ScatterIcon from "../detail/ScatterIcon";

    export default {
        name: "Heading",
        components:{ScatterIcon},
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