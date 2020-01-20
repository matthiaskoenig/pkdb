<template>
    <v-dialog class="detail-dialog text-xs-center">
        <template v-slot:activator="{ on }">
            <v-chip v-if="individual" color="#fdae61" title="Group Details">
                <v-icon small color="black">{{ icon('individual') }}</v-icon>&nbsp;
                <text-highlight :queries="search.split(/[ ,]+/)">{{ individual.name }}</text-highlight>
            </v-chip>
        </template>
        <individual-detail :individual="individual"/>
    </v-dialog>
</template>

<script>
    import {lookup_icon} from "@/icons"
    import IndividualDetail from "./IndividualDetail"

    export default {
        name: "IndividualChip",
        components: {
            IndividualDetail
        },
        props: {
            individual: {
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