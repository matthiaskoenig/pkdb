<template>
    <v-dialog v-model="dialog" width="500">
        <v-btn
                slot="activator"
                color="red lighten-2"
                dark
        >
            <v-icon>{{ icon('individual') }}</v-icon></a>
        </v-btn>

        <v-card>
            <get-data :resource_url="individual_url">
                <div slot-scope="data">
                    <individual-detail :individual="data.data"/>
                </div>
            </get-data>

        </v-card>
    </v-dialog>

</template>

<script>
    import {lookup_icon} from "@/icons"
    import IndividualDetail from '../detail/IndividualDetail'

    export default {
        name: "IndividualButton",
        components: {IndividualDetail},
        props: {
            individual_url: {
                type: String,
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