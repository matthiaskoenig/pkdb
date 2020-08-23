<template>
    <v-chip
            :disabled="!count"
            class="ma-1"
            color="#FFFFFF"
            flat
            pill
            small

            :to="to"
    >
        <v-icon
                small
                left
                :title="'Number of ' + name + 's'">
          {{ faIcon }}
        </v-icon>

      <strong>{{ count }}</strong>
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