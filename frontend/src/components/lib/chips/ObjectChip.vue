<template>
    <span>
      <v-chip
              flat
              color="#FFFFFF"
              small
              :title="'Show ' + name + ' details'"
      >
        <v-avatar left>

     <v-badge v-if="count" left dark overlap color="#000000">
        <span slot="badge">{{ count }}</span>
            <v-icon small
                    :color="color"
            >
              {{ icon }}
            </v-icon>&nbsp;
     </v-badge>

        <v-icon v-if="!count" small :color="color">{{ icon }}</v-icon>&nbsp;

                 </v-avatar>
    <span style="{color: black;}"><text-highlight :queries="search.split(/[ ,]+/)">{{ name }}</text-highlight></span>
        </v-chip>
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