<template>
    <span>
        <strong>{{ data.label }}</strong>
    </span>
</template>

<script>
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