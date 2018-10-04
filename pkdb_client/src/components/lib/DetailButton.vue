<template>
<div class="detail-button">
    <md-button :to="to" :title="title" class="md-icon-button md-raised" :disabled="to ? false : true">
        <font-awesome-icon :icon="icon"/>
    </md-button>

</div>
</template>

<script>
    export default {
        name: "JsonButton",
        props: {
            title: {
                type: String,
                required: true
            },
            icon: {
                type: String,
                required: true
            },
            to: {
                type: String,
            },
        },
    }
</script>

<style scoped>

</style>