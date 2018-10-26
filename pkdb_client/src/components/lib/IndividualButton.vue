<template>
    <v-dialog class="detail-dialog">
        <v-btn slot="activator" fab small :title="individual.name">
            <v-icon>{{ icon('individual') }}</v-icon></a>
        </v-btn>
        <individual-detail :individual="individual"/>
    </v-dialog>
</template>

<script>
    import {lookup_icon} from "@/icons"
    import IndividualDetail from '../detail/IndividualDetail'

    export default {
        name: "IndividualButton",
        components: {IndividualDetail},
        props: {
            individual: {
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