<template>

    <v-chip v-if="intervention" color="#2b83ba" title="Intervention Details" >
        <v-icon small color="black">{{ icon('intervention') }}</v-icon>&nbsp;
        <text-highlight :queries="search.split(/[ ,]+/)">{{ intervention.name }}</text-highlight>
    </v-chip>

    <!--
    <v-dialog class="detail-dialog text-xs-center">
        <template v-slot:activator="{ on }">

            <v-chip v-if="intervention" color="#2b83ba" title="Intervention Details" >
                <v-icon small color="black">{{ icon('intervention') }}</v-icon>&nbsp;
                <text-highlight :queries="search.split(/[ ,]+/)">{{ intervention.name }}</text-highlight>
            </v-chip>

        </template>
        <intervention-detail :intervention="intervention"/>
    </v-dialog>
    -->
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