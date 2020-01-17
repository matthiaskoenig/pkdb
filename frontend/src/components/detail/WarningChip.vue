<template>
    <span class="text-xs-center">
        <v-chip v-if="title" class="warning" outlined>

            <v-icon small color="warning">{{ icon('warning') }}</v-icon>&nbsp;
          {{ title }}
        </v-chip>
    </span>
</template>

<script>
    import {lookup_icon} from "@/icons"

    export default {
        name: "WarningChip",
        props: {
            title: {
                type: String,
                required: true
            }

        },
        methods: {
            icon(key) {
                return lookup_icon(key)
            },
        }
    }
</script>

<style scoped>

</style>