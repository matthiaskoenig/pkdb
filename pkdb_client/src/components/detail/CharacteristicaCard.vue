<template>
    <div class="characteristica-card">
        {{ data }}
    </div>
</template>

<script>

    export default {
        name: "CharacteristicaCard",
        props: {
            data: Object,
            resource_url: String,
        },
        computed: {
        }
    }
</script>

<style scoped>
</style>
