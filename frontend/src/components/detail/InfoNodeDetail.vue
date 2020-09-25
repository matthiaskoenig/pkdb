<template>
  <v-card
      width="100%"
      flat

  >
    <v-list-item three-line >
      <v-list-item-content>
        <div class="overline">
          <json-button v-if="url" :resource_url="url"></json-button> {{ data.ntype.toUpperCase() }}
          <span v-if="data.dtype != 'undefined'">({{ data.dtype.toUpperCase() }})</span>
        </div>
        <v-list-item-title class="headline mb-1"><text-highlight :queries="highlight">{{ data.label }}</text-highlight>
          <v-chip v-if="data.ntype === 'substance'"
                  outlined
                  small
                  class="ml-2"
                  :title="substance_class==='generic' ? 'Generic substance class without chemical structure': 'Specific substance with chemical structure'"
          >
            {{ substance_class.toUpperCase() }}
          </v-chip>
        </v-list-item-title>
        <v-list-item-subtitle v-if="parents_labels.length>0">Parents:
          <object-chip :object="parent"
                       otype="info_node"
                       v-for="parent in data.parents"
                       :key="parent.sid"
                       :search="highlight"
          />
        </v-list-item-subtitle>
      </v-list-item-content>
    </v-list-item>





    <v-card-text>
    <div v-if="data.description && data.description.length>0">
      <text-highlight :queries="highlight">
      {{ data.description }}<br />
      </text-highlight>
    </div>

    <div v-if="data.annotations && data.annotations.length>0">
      <span v-for="annotation in data.annotations" :key="annotation.term">
          <annotation :annotation="annotation" />
          <span v-if="annotation.label"><strong>
                  <text-highlight :queries="highlight">
            {{ annotation.label }}
                </text-highlight>

            </strong></span>
          <text-highlight :queries="highlight">
            {{ annotation.description ? annotation.description: "" }}
          </text-highlight>
          <span v-if="annotation.collection==='chebi'">
            <v-img :title="annotation.term" :src="'https://www.ebi.ac.uk/chebi/displayImage.do?defaultImage=true&imageIndex=0&chebiId=' + annotation.term.substring(6)" max-width="200"/>
          </span>
        <br />
      </span>
    </div>

    <div v-if="data.xrefs && data.xrefs.length>0">
      <span class="label">Database links</span><br />
      <span v-for="xref in data.xrefs" :key="xref.url">
        <xref v-bind="xref"/>
      </span>
    </div>

    <br />

    <div v-if="data.synonyms && data.synonyms.length>0">
      <span class="label">Synonyms</span><br />
      <ul>
        <li v-for="synonym in data.synonyms" :key="synonym">
          <text-highlight :queries="highlight">
          {{ synonym }}
          </text-highlight>
        </li>
      </ul>
    </div>
    </v-card-text>
  </v-card>

</template>

<script>

import Annotation from "../info_node/Annotation";
import Xref from "../info_node/Xref";
import {StoreInteractionMixin} from "../../storeInteraction";

export default {
  name: 'InfoNodeDetail',
  mixins: [StoreInteractionMixin],
  components: {
    Annotation,
    Xref,
  },
  props: {
    data: {
      type: Object,
      required: true,
    },
    url: {
      type: String,
      required: false,
    }
  },
  computed: {
    substance_class: function (){
      let label = "generic";
      let annotations = this.data.annotations
      for (const annotation of annotations){
        if (annotation.collection == "inchikey"){
          label = "specific";
          break;
        }
      }
      return label
    },

    parents_labels: function () {
      let labels = []
      let parents = this.data.parents
      if (parents){
        for (let i=0; i<parents.length; i++ ){
          labels.push(parents[i].label)
        }
      }
      return labels
    }
  },
  methods: {},
}
</script>
<style>
  .label {
    font-weight: bold;
    padding: 5px;
  }
</style>