<template>
  <span>
  <v-chip
      v-if="!count"
          :class= margin
          color="#FFFFFF"
          flat
          pill
          small
          :title="'Show ' + name + ' details'"
          @click.stop="update_details"
  >
    <v-icon small left :color="color">{{ icon }}</v-icon>&nbsp;
    <span style="color: black; font-weight: bold;"><text-highlight :queries="search.split(/[ ,]+/)">{{ name }}</text-highlight></span>
  </v-chip>

    <v-badge v-if="count" left dark overlap color="#000000">
      <span slot="badge">{{ count }}</span>
      <v-chip
              class="ma-1"
              color="#FFFFFF"
              flat
              pill
              small
              :title="'Show ' + name + ' details'"
              @click="update_details"

      >
        <v-icon small left :color="color">{{ icon }}</v-icon>&nbsp;
        <span style="color: black; font-weight: bold;"><text-highlight :queries="search.split(/[ ,]+/)">{{ name }}</text-highlight></span>
      </v-chip>
    </v-badge>
</span>
</template>

<script>
import axios from 'axios'
import {lookupIcon} from "@/icons"

export default {
  name: "ObjectChip",
  components: {},
  props: {
    margin: {
      type: String,
      default: 'ma-1'
    } ,
    object: {
      required: true
    },
    otype: {
      type: String,
      required: true
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
    name: function () {
      if ('name' in this.object) {
        return this.object.name;
      } else {
        return this.object.label;
      }
    },
    color: function () {
      if (this.otype.startsWith('group')) {
        return "#fdae61";
      } else if (this.otype.startsWith('individual')) {
        return "blue";
      } else if (this.otype.startsWith('substance')) {
        return "#00a087";
      } else if (this.otype.startsWith('intervention')) {
        return "red";
      } else if (this.otype.startsWith('output')) {
        return "black";
      } else if (this.otype.startsWith('timecourse')) {
        return "black";
      } else if (this.otype.startsWith('measurement_type')) {
        return "black";
      } else if (this.otype.startsWith('tissue')) {
        return "magenta";
      }

      return "#00a087";

    },
    show_type: function(){

      if (this.otype.startsWith('substance')) {
        return "info_node";
      } else if (this.otype.startsWith('measurement_type')) {
        return "info_node";
      } else if (this.otype.startsWith('tissue')) {
        return "info_node";
      }else if (this.otype.startsWith('application')) {
        return "info_node";
      }else if (this.otype.startsWith('route')) {
        return "info_node";
      }else if (this.otype.startsWith('form')) {
        return "info_node";}
      else if (this.otype.startsWith('info_node')) {
          return "info_node";
      }else if (this.otype.startsWith('group')) {
        return "group";
      }

      return null;

    },
    icon: function () {
      return lookupIcon(this.otype)
    },
  },
  data() {
    return {
      data: null,
      exists: false,
    }
  },
  methods: {
    update_details(){
      if (this.show_type === "info_node") {
        this.getInfoNode();
      }else if(this.show_type === "group"){
        //this.updateGroup();

      }
    },
    updateGroup() {
      // object is an InfoNode
            this.$store.state.show_type = "group";
            this.$store.state.detail_info = this.object;
            this.$store.state.display_detail = true;
    },
    getInfoNode() {
      if ("sid" in this.object && "label" in this.object){
        // object is an InfoNode
        let url = `${this.$store.state.endpoints.api}info_nodes/${this.object.sid}/?format=json`;

        // get data (FIXME: caching of InfoNodes in store)
        axios.get(url)
            .then(response => {
              this.data = response.data;
              this.exists = true;
              this.$store.state.show_type = this.show_type;
              this.$store.state.detail_info = this.data;
              this.$store.state.display_detail = true ;
            })
            .catch(err => {
              console.log(err.response.data);
              this.exists = false;
            })
            .finally(() => this.loading = false);
      }
    },
  },
  mounted() {

  },
}
</script>

<style scoped>

</style>