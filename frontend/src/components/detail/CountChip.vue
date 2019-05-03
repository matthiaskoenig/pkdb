<template>
    <span class="text-xs-center">
        <v-chip color="w" disable=true>
            <v-icon small :title="icon">{{icon_object}}</v-icon>&nbsp;

            {{ count }}
        </v-chip>
    </span>
</template>

<script>
    import {lookup_icon} from "@/icons"

    export default {
        name: "CountChip",
        props: {
            count: {
                type: Number,
                required: true
            },
            icon:{
                type:String,
                required: true
            }
        },
        computed: {
            icon_object() {
                return lookup_icon(this.icon)
            },
        }
    }
</script>

<style scoped>

</style>