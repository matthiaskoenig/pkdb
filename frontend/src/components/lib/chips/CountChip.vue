<template>
    <v-chip color="black"
            :disabled="!count"

            outlined
            small
            :to="to"
    >
      <v-avatar left>
        <v-icon
                small
                :title="'Number of ' + name + 's'">
          {{ faIcon }}
        </v-icon>
      </v-avatar>
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