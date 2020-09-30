<template>
    <v-sheet flat>
        <table-toolbar :otype="otype" :count="count" :autofocus="autofocus" :url="url" @update="searchUpdate"/>
        <v-data-table
            fill-height
            fixed-header
            :height="windowHeight"
            dense
            :headers="headers"
            :items="entries"
            disable-sort
            :options.sync="options"
            :server-items-length="count"
            :loading="loading"
            :class="table_class"
            :footer-props="footer_options"
        >
          <template v-slot:item.buttons="{ item }">
            <link-button :detail_info_input="item"
                        show_type_input="study"
                        :title="'Study: '+item.pk"
                        icon="study"
            />
            <JsonButton :resource_url="api + 'studies/'+ item.sid +'/?format=json'"/>
          </template>
          <template v-slot:item.study="{ item }">
            <text-highlight :queries="search.split(/[ ,]+/)">{{ item.sid }}</text-highlight><br />
            <text-highlight :queries="search.split(/[ ,]+/)">{{ item.name }}</text-highlight><br />
            {{ item.date }}<br />
          </template>
          <template v-slot:item.counts="{ item }">
            <count-chip :count=item.group_count icon="group" name="group"></count-chip>
            <count-chip :count=item.individual_count icon="individual" name="individual"></count-chip>
            <count-chip :count=item.intervention_count icon="intervention" name="intervention"></count-chip>
            <count-chip :count=item.output_count icon="output" name="output"></count-chip >
            <count-chip :count=item.timecourse_count icon="timecourse" name="timecourse" />
            <count-chip :count=item.scatter_count icon="scatter" name="scatter" />

          </template>

          <template v-slot:item.reference="{ item }">
            <span v-if="item.reference">
                  <pubmed :pmid="item.reference.pmid"/>
                  <span class="font-weight-thin"><text-highlight :queries="search.split(/[ ,]+/)">{{ item.reference.title }}</text-highlight></span>
                </span>
          </template>

          <template v-slot:item.substances="{ item }">
                <span v-for="substance in item.substances" :key="substance.sid">
                    <object-chip :object="substance"
                                 otype="substance"
                                 :search="search"
                    />
                </span>
          </template>

          <template v-slot:item.creator="{ item }">
            <user-avatar :user="item.creator"
                         :search="search"
            />
          </template>

          <template v-slot:item.curators="{ item }">
                <span v-for="(curator, index2) in item.curators" :key="index2">
                    <user-rating :user="curator" :search="search"/>
                </span>
          </template>

          <no-data/>
        </v-data-table>
    </v-sheet>
</template>

<script>
    import {searchTableMixin} from "./mixins";
    import TableToolbar from './TableToolbar';
    import Xref from "../info_node/Xref";
    import Pubmed from "../info_node/Pubmed";
    import NoData from './NoData';
    import CharacteristicaCard from '../detail/CharacteristicaCard'

    export default {
        name: "StudiesTable",
        components: {
            NoData,
            TableToolbar,
            CharacteristicaCard,
            Xref,
            Pubmed,
        },
        mixins: [searchTableMixin],
        data () {
            return {
                otype: "studies",
                otype_single: "study",
                headers: [
                    {text: '', value: 'buttons', sortable: false},
                    {text: 'Study', value: 'study', sortable: false},
                    {text: 'Counts', value: 'counts', sortable: false},
                    {text: 'Reference', value: 'reference', sortable: false},
                    {text: 'Curators', value: 'curators', sortable: false},
                    {text: 'Substances', value: 'substances', sortable: false},
                    // {text: 'Creator', value: 'creator',sortable: false},

                ],
            }
        },
    }
</script>

<style scoped></style>
<style>
.theme--light.v-datatable.v-datatable__actions {
  position: fixed !important;
  bottom: 0 !important;
  width: 100% !important;
}
</style>