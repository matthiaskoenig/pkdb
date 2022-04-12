<template>
  <span >
    <v-chip
        v-if="!object.count"
        :class= margin
        color="#FFFFFF"
        flat
        pill
        small
        :title="'Show ' + label + ' details'"
        @click.stop="update_details"
    >
      <v-icon small left :color="detail.color">{{faIcon(otype)}}</v-icon>&nbsp;
      <span style="color: black; font-weight: bold"><text-highlight :queries="search.split(/[ ,]+/)">{{ label }}</text-highlight></span>
    </v-chip>
    <v-badge v-else left dark overlap color="#000000">
      <span  slot="badge">{{ object.count }}</span>
      <v-chip
          class="ma-1"
          color="#FFFFFF"
          flat
          pill
          small
          :title="'Show ' + label + ' details'"
          @click.stop="update_details"
      >
        <v-icon small left :color="detail.color">{{faIcon(otype)}}</v-icon>&nbsp;
        <span style="color: black; font-weight: bold;"><text-highlight :queries="search.split(/[ ,]+/)">{{ label }}</text-highlight></span>
      </v-chip>
    </v-badge>
  </span>
</template>
<script>
import {ApiInteractionMixin} from "../../../apiInteraction";
import {IconsMixin} from "../../../icons";

export default {
  name: "ObjectChip",
  mixins: [ApiInteractionMixin, IconsMixin],
  data() {
    return {
      details:{
        group:{
          color: "#fdae61",
          show_type: "group",
          pk_key:"pk"
        },
        individual: {
          color: "blue",
          show_type: "individual",
          pk_key:"pk"
        },
        intervention: {
          color: "red",
          show_type: "intervention",
          pk_key:"pk"
        },
        output: {
          color: "black",
          show_type: "output",
          pk_key:"pk"
        },
        timecourse: {
          color: "black",
          show_type: "timecourse",
          pk_key:"pk"
        },
        scatter: {
          color: "black",
          show_type: "scatter",
          pk_key:"pk"
        },

        //info nodes
        measurement_type: {
          color: "black",
          show_type: "info_node",
          pk_key:"sid"
        },

        tissue: {
          color: "magenta",
          show_type: "info_node",
          pk_key:"sid"
        },
        choice: {
          color: "#00a087",
          show_type: "info_node",
          pk_key:"sid"
        },
        substance: {
          color: "#00a087",
          show_type: "info_node",
          pk_key:"sid"
        },
        application: {
          color: "#00a087",
          show_type: "info_node",
          pk_key:"sid"
        },
        form: {
          color: "#00a087",
          show_type: "info_node",
          pk_key:"sid"
        },
        route: {
          color: "#00a087",
          show_type: "info_node",
          pk_key:"sid"
        },
        info_node: {
          color: "#00a087",
          show_type: "info_node",
          pk_key:"sid"
        },
        // other
        time: {
          color: "#00a087",
          show_type: null,
          pk_key: null
        },
      }
    }
  },
  props: {
    margin: {
      type: String,
      default: 'ma-1'
    } ,
    object: {
      type: Object,
      required: true,
    },
    otype: {
      type: String,
      required: true
    },
    search: {
      type: String,
      default: ''
    },
  },
  computed: {

    label: function () {
      if ('label' in this.object)
      {return this.object.label;
      } else {
        return this.object.name;
      }
    },
    detail() {
      return this.details[this.otype]
    }
  },
  methods: {
    update_details() {
      if(this.detail.pk_key){
        this.getInfo(this.object[this.detail.pk_key],this.detail.show_type)
      }
    },
  }



}
</script>

<style scoped>

</style>