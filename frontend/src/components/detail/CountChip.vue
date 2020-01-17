<template>
    <!--
    <v-chip class="ma-2" color="black" text-color="white">
        <v-avatar left class="green darken-4">
            {{count}} Test
        </v-avatar>
    </v-chip>
    -->

    <v-chip color="white"
            :disabled=disabled
    >
        <v-icon small :title="'Number of '+icon+'s'">{{icon_object}}</v-icon>&nbsp;
        {{ count }}
    </v-chip>

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
            disabled:{
                type:Boolean,
                required:false,
                default:false
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