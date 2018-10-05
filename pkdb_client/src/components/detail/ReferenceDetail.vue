<template>
    <v-card>
        <Heading :title="'Reference: '+reference.pk" :count="1" :icon="icon('reference')" :resource_url="resource_url"/>
    </v-card>
</template>

<script>
    import {lookup_icon} from "@/icons"

    export default {
        name: "ReferenceDetail",
        props: {
            reference: {
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