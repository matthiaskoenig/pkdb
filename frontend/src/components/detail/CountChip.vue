<template>
    <v-chip color="black"
            :disabled="!count"
            label
            outlined
    >
        <v-icon :title="'Number of ' + name + 's'">{{ icon }}</v-icon>&nbsp;
        {{ count }}
    </v-chip>
</template>

<script>
    export default {
        name: "CountChip",
        props: {
            count: {
                type: Number,
                required: true
            },
            name: {
                type: String,
                required: true
            },
            icon:{
                type:String,
                required: true
            }
        },
        computed: {}
    }
</script>

<style scoped>
</style>