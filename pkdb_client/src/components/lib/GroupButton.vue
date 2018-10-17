<template>
    <v-dialog class="detail-dialog">
        <v-btn slot="activator" fab small :title="group.name">
            <v-icon>{{ icon('group') }}</v-icon></a>
        </v-btn>
        <group-detail :group="group"/>
    </v-dialog>
</template>

<script>
    import {lookup_icon} from "@/icons"
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
            icon: function (key) {
                return lookup_icon(key)
            },
        }
    }
</script>

<style scoped>
</style>