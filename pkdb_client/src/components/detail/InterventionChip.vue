<template>
    <v-dialog class="detail-dialog text-xs-center">
        <span slot="activator">
            <v-chip v-if="intervention" color="blue" title="Intervention Details">
                <v-icon small>{{ icon('intervention') }}</v-icon>&nbsp;
                <text-highlight :queries="search.split(/[ ,]+/)">{{ intervention.name }}</text-highlight>
            </v-chip>
        </span>
        <intervention-detail :intervention="intervention"/>
    </v-dialog>
</template>

<script>
    import {lookup_icon} from "@/icons"
    import InterventionDetail from "./InterventionDetail"

    export default {
        name: "InterventionChip",
        components: {
            InterventionDetail
        },
        props: {
            intervention: {
                type: Object,
                required: true
            },
            search: {
                type: String,
                default: ''
            },
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