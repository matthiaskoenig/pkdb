<template>
    <v-dialog class="detail-dialog text-xs-center">
        <span slot="activator">
            <v-chip v-if="group" color="orange" title="Group Details">
                <v-icon small>{{ icon('group') }}</v-icon>&nbsp;
                <text-highlight :queries="search.split(/[ ,]+/)">{{ group.name }}</text-highlight>
                <v-btn small color="black" fab dark title="Group Size">{{ group.count }}</v-btn>
            </v-chip>
        </span>
        <group-detail :group="group"/>
    </v-dialog>
</template>

<script>
    import {lookup_icon} from "@/icons"
    import GroupDetail from "./GroupDetail"

    export default {
        name: "GroupChip",
        components: {
            GroupDetail
        },
        props: {
            group: {
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