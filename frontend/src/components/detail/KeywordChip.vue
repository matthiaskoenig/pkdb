<template>
    <v-chip dark v-if="keyword" title="Group Details">
        {{ keyword }}
    </v-chip>
</template>

<script>
    export default {
        name: "KeywordChip",
        components: {
        },
        props: {
            keyword: {
                type: String,
                required: true
            },
        }
    }
</script>

<style scoped>

</style>