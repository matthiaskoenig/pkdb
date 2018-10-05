<template>
<div id="heading">
            <v-icon>{{ icon }}</v-icon>&nbsp;
            <v-badge right color="red">
                <span slot="badge">{{ count }}</span>
                <!-- <v-icon large color="grey lighten-1">icon</v-icon>-->
                <strong>{{ title }}</strong>
            </v-badge>&nbsp;&nbsp;
            <JsonButton :resource_url="resource_url"/>
</div>
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