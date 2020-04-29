<template>
    <v-chip color="black"
            :disabled="!count"
            label
            outlined
            :to="to"
    >
        <v-icon color="black" :title="'Number of ' + name + 's'">{{ faIcon }}</v-icon>
        {{ count }}
    </v-chip>
</template>

<script>
    import {lookupIcon} from "@/icons"

    export default {
        name: "CountChip",
        props: {
            to: {
                type: String,
            },
            count: {
                type: Number,
                required: true
            },
            name: {
                type: String,
                required: true
            },
            icon:{
                type:String,
                required: true
            }
        },
        computed: {
            faIcon: function(){
                return lookupIcon(this.icon)
            }
        },
        methods: {

        }
    }
</script>

<style scoped>
</style>