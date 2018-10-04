<template>
<div class="detail-button">
    <md-button :to="to" :title="title" class="md-icon-button md-raised md-dense md-primary" :disabled="to ? false : true">
        <font-awesome-icon :icon="icon"/>
    </md-button>

</div>
</template>

<script>
    export default {
        name: "DetailButton",
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