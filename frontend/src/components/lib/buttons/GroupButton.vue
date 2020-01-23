<template>
    <v-dialog class="detail-dialog">
        <v-btn slot="activator" fab small :title="group.name">
            <v-icon>{{ faIcon('group') }}</v-icon>
        </v-btn>
        <group-detail :group="group"/>
    </v-dialog>
</template>

<script>
    import {lookupIcon} from "@/icons"
    import GroupDetail from '../detail/GroupDetail'

    export default {
        name: "GroupButton",
        components: {GroupDetail},
        props: {
            group: {
                type: Object,
                required: true
            },
        },
        computed: {
        },
        methods: {
            faIcon: function (key) {
                return lookupIcon(key)
            },
        }
    }
</script>

<style scoped>
</style>