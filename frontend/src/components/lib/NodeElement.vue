<template>
    <span>
        <strong>{{ data.sid }}</strong>
    </span>
</template>

<script>
    // TODO: load additional information and provide access to it, e.g., synonmys or annotations

    export default {
        name: "NodeElement",
        components: {

        },
        props: {
            data: {
                type: Object,
                required: true
            }
        },
        computed: {
        },
        methods: {
        }
    }

</script>

<style scoped>

</style>