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
            to: {
                type: String,
            },
            title: {
                type: String,
                required: true
            },
            icon: {
                type: String,
                required: true
            },
        },
    }
</script>

<style scoped>

</style>