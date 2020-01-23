<template>
    <v-dialog class="detail-dialog">
        <v-btn slot="activator" fab small :title="individual.name">
            <v-icon>{{ faIcon('individual') }}</v-icon>
        </v-btn>
        <individual-detail :individual="individual"/>
    </v-dialog>
</template>

<script>
    import {lookupIcon} from "@/icons"
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
            faIcon: function (key) {
                return lookupIcon(key)
            },
        }
    }
</script>

<style scoped>

</style>