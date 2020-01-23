<template>
    <v-chip :color="color"
            :title="otype"
            outlined
    >

        <v-icon left small color="black">{{ icon }}</v-icon>&nbsp;
        <text-highlight :queries="search.split(/[ ,]+/)">{{ name }}</text-highlight>



        <v-btn v-if="count"
               small
               color="black"
               fab
               dark
               title="count">{{ count }}</v-btn>
    </v-chip>
</template>

<script>
    import {lookupIcon} from "@/icons"

    export default {
        name: "ObjectChip",
        components: {
        },
        props: {
            object: {
                required: true
            },
            otype: {
                type: String,
                required:true
            },
            count: {
                type: Number,
                default: 0
            },
            search: {
                type: String,
                default: ''
            },
        },
        computed: {
            name: function (){
                if (this.otype.startsWith('substance')){
                    return this.object;
                } else {
                    return this.object.name;
                }
            },
            color: function () {
                if (this.otype.startsWith('group')) {
                    return "#fdae61";
                } else if (this.otype.startsWith('individual')){
                    return "blue";
                } else if (this.otype.startsWith('substance')){
                    return "#00a087";
                } else if (this.otype.startsWith('intervention')){
                    return "red";
                } else if (this.otype.startsWith('output')){
                    return "black";
                } else if (this.otype.startsWith('timecourse')){
                    return "black";
                }

                return "#00a087";
            },
            icon: function () {
                return lookupIcon(this.otype)
            },
        },
        methods: {
        }
    }
</script>

<style scoped>

</style>