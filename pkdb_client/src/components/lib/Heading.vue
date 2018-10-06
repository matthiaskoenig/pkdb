<template>
<span id="heading">
    <v-toolbar-title>
    <v-icon :title="title">{{ icon }}</v-icon>&nbsp;
    <v-badge v-if="count" right color="red">
        <span slot="badge">{{ count }}</span>
        <!-- <v-icon large color="grey lighten-1">icon</v-icon>-->
        {{ title }}
    </v-badge>&nbsp;
    <span v-if="!count">{{ title }}</span>
    <JsonButton :resource_url="resource_url"/>
    </v-toolbar-title>
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
</style>