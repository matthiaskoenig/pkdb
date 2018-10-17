<template>
    <span>
        {{ options }}
    </span>
</template>

<script>
    export default {
        name: "OptionsBrowser",
        props: {
            options: {
                type: Object,
                required: true
            }
        },
    }
</script>

<style scoped>

</style>