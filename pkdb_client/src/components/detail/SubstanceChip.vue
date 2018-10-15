<template>
    <div class="text-xs-center">
        <v-chip> <v-icon>{{ icon('substance') }}</v-icon>{{substance}}</v-chip>
    </div>
</template>

<script>
    import {lookup_icon} from "@/icons"
    export default {
        name: "SubstanceChip",
        props: {
            substance : String,
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