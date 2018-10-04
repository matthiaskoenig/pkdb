<template>
<div id="heading">
    <md-badge :md-content="count">
    </md-badge>
    <h1 class="md-title"><font-awesome-icon :icon="icon" /> {{ title }}</h1>
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