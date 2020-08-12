<template>
    <span>
     <v-badge v-if="count" left dark overlap color="#000000">
        <span slot="badge">{{ count }}</span>
        <v-btn :color="color"
               fab
               x-small
               dark
               elevation="0"
               :link="false"
        >
            <v-icon small
                    color="black"
            >{{ icon }}</v-icon>&nbsp;
        </v-btn>
     </v-badge>    &nbsp;

    <v-btn v-if="!count"
           :color="color"
           fab
           x-small
           dark
           elevation="0"
           :link="false"
    >
        <v-icon small color="black">{{ icon }}</v-icon>&nbsp;
    </v-btn>&nbsp;
    <text-highlight :queries="search.split(/[ ,]+/)">{{ name }}</text-highlight>
    </span>
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
              if ('name' in this.object){
                return this.object.name;
              } else {
                return this.object.label;
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
                    return "white";
                } else if (this.otype.startsWith('timecourse')){
                    return "white";
                } else if (this.otype.startsWith('measurement_type')){
                    return "white";
                } else if (this.otype.startsWith('tissue')){
                    return "#DDDDDD";
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