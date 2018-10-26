<template>
    <span class="text-xs-center">

    <v-dialog class="detail-dialog">
        <!--<v-btn slot="activator" fab small :title="group.name">-->
        <span slot="activator">
            <v-chip v-if="title" color="warning">
                <v-icon small>{{ icon('group') }}</v-icon>&nbsp;
                <text-highlight :queries="search.split(/[ ,]+/)">{{ title }}</text-highlight>
            </v-chip>
        </span>
        <!--</v-btn>-->
        <group-detail :group="group"/>
        Test
    </v-dialog>

    </span>
</template>

<script>
    import {lookup_icon} from "@/icons"

    export default {
        name: "GroupChip",
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