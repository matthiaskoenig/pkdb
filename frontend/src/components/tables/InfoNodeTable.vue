<template>

  <v-card flat width="100%">
    <table-toolbar :otype="otype" :count="count" :autofocus="autofocus" :url="url" @update="searchUpdate"/>
    <v-data-table
        fill-height
        fixed-header
        :height="windowHeight"
        :headers="headers"
        :items="entries"
        :options.sync="options"
        :server-items-length="count"
        :loading="loading"
        :class="table_class"
        :footer-props="footer_options"
    >
      <template v-slot:item.buttons="{ item }">
        <JsonButton :resource_url="api + 'info_nodes/'+ item.sid+ '/?format=json' "/>
      </template>
      <template v-slot:item.label="{ item }">
        <info-node-chip :item="item"/>
      </template>

      <template v-slot:item.type="{ item }">
        <text-highlight :queries="highlight.split(/[ ,]+/)">{{ item.ntype }}</text-highlight>
        <br/>
        <text-highlight :queries="highlight.split(/[ ,]+/)">
          <span v-if="item.dtype!='undefined'">{{ item.dtype }}</span></text-highlight>
      </template>

      <template v-slot:item.description="{ item }">
        <text-highlight :queries="highlight.split(/[ ,]+/)">{{ item.description }}</text-highlight>
      </template>
      <template v-slot:item.synonyms="{ item }">
        <ul>
          <span v-for="synonym in item.synonyms" :key="synonym">
            <li><text-highlight :queries="highlight.split(/[ ,]+/)">{{ synonym }}</text-highlight></li>
          </span>
        </ul>
      </template>

      <template v-slot:item.parents="{ item }">
        <v-chip v-for="(parent, index) in item.parents" :key="index"
                small
                outlined
                color="black"
        >

                  <span v-if="parent.label === parent.name">
                    <strong><text-highlight :queries="highlight.split(/[ ,]+/)">{{ parent.label }}</text-highlight></strong>
                  </span>
                  <span v-if="parent.label != parent.name">
                    <text-highlight :queries="highlight.split(/[ ,]+/)">{{ parent.label }}</text-highlight> |
                    <strong><text-highlight :queries="highlight.split(/[ ,]+/)">{{ parent.name }}</text-highlight></strong>
                  </span>

        </v-chip>
      </template>


      <!-- extras -->
      <template v-slot:item.extras="{ item }">

        <span v-if="item.ntype === 'measurement_type'">
            <span v-if="item.measurement_type.units.length > 0">
              Units<br/>
               <v-chip v-for="unit in item.measurement_type.units" :key="unit"
                       small
                       outlined
                       color="black"
               >
                  {{ unit }}
              </v-chip>
            </span>
            <span v-if="item.measurement_type.choices.length > 0">
                Choices<br/>
                <v-chip v-for="choice in item.measurement_type.choices" :key="choice.sid"
                        small
                        outlined
                        color="black"
                >
                  <span v-if="choice.label === choice.name">
                    <strong><text-highlight :queries="highlight.split(/[ ,]+/)">{{ choice.label }}</text-highlight></strong>
                  </span>
                  <span v-if="choice.label != choice.name">
                    <text-highlight :queries="highlight.split(/[ ,]+/)">{{ choice.label }}</text-highlight> |
                    <strong><text-highlight :queries="highlight.split(/[ ,]+/)">{{ choice.name }}</text-highlight></strong>
                  </span>

                </v-chip>
            </span>
        </span>

        <span v-if="item.ntype === 'substance'">
            <span v-if="item.substance.mass">
              Mass: <text-highlight :queries="highlight.split(/[ ,]+/)">{{
                item.substance.mass
              }}</text-highlight><br/>
            </span>
            <span v-if="item.substance.charge">
              Charge: <text-highlight
                :queries="highlight.split(/[ ,]+/)">{{ item.substance.charge }}</text-highlight><br/>
            </span>
            <span v-if="item.substance.formula">
              Formula: <text-highlight
                :queries="highlight.split(/[ ,]+/)">{{ item.substance.formula }}</text-highlight><br/>
            </span>
        </span>
      </template>

      <template v-slot:item.annotations="{ item }">
        <span v-for="annotation in item.annotations" :key="annotation.term">
          <annotation :annotation="annotation" />
        </span>

      </template>

      <template v-slot:item.xrefs="{ item }">
        <span v-for="xref in item.xrefs" :key="xref.url">
          <xref v-bind="xref" />
        </span>
      </template>

      <no-data/>
    </v-data-table>
  </v-card>
</template>

<script>
import {searchTableMixin, UrlMixin} from "../tables/mixins";
import TableToolbar from '../tables/TableToolbar';
import NoData from '../tables/NoData';
import Annotation from "../info_node/Annotation";
import Xref from "../info_node/Xref";
import InfoNodeChip from "../lib/chips/InfoNodeChip";
import {StoreInteractionMixin} from "../../storeInteraction";

export default {
  name: "InfoNodeTable",
  components: {
    InfoNodeChip,
    NoData,
    TableToolbar,
    Annotation,
    Xref,
  },
  mixins: [searchTableMixin, UrlMixin, StoreInteractionMixin],
  data() {
    return {
      otype: "info_nodes",
      otype_single: "info_nodes",
      headers: [
        {text: '', value: 'buttons', sortable: false},
        {text: 'Label (Name)', value: 'label', sortable: false},
        {text: 'Type', value: 'type', sortable: false},
        {text: 'Description', value: 'description', sortable: false},
        {text: 'Synonyms', value: 'synonyms', sortable: false},
        {text: 'Parents', value: 'parents', sortable: false},
        {text: 'Extra', value: "extras",sortable: false},
        {text: 'Annotations', value: 'annotations', sortable: false},
        {text: 'Cross references', value: 'xrefs', sortable: false},
      ]
    }
  }

}
</script>

<style scoped></style>
