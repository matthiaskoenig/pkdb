<template>
    <v-card>
        <Heading :title="'Output: '+output.pk" :count="1" :icon="icon('output')" :resource_url="resource_url"/>
    </v-card>
</template>

<script>
    import {lookup_icon} from "@/icons"

    export default {
        name: "OutputDetail",
        props: {
            output: {
                type: Object,
            },
            resource_url: {
                type: String
            }
        },
        computed: {
        },
        methods: {
            icon: function (key) {
                return lookup_icon(key)
            },
        }
    }
</script>

<style scoped>

</style>