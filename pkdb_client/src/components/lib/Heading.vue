<template>
<div id="heading">


    <h1 class="md-title"><font-awesome-icon :icon="icon" /> </h1>

    <JsonButton :resource_url="resource_url"/>

    <div class="text-xs-center">
    <v-badge left color="red">
        <span slot="badge">10</span>
        <!-- <v-icon large color="grey lighten-1">icon</v-icon>-->
        <h3>{{ title }}</h3>
    </v-badge>
    </div>


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