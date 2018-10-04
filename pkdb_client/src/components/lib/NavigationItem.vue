<template>
    <!-- <md-tab :id="id" :md-label="label" :md-icon="icon" to="/"> </md-tab>-->

    <a :href="to">
        <md-icon>{{ md_icon }}</md-icon>
        <font-awesome-icon :icon="icon"/>
        {{ label }}
    </a>

</template>

<script>
    export default {
        name: "NavigationItem",
        props: {
            id: {
                type: String,
                required: true
            },
            label: {
                type: String,
                required: true
            },
            icon: {
                type: String,
            },
            md_icon: {
                type: String,
            },
            to: {
                type: String,
                required: true
            }
        },
    }
</script>

<style scoped>

</style>