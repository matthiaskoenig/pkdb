<template>
    <v-sheet flat>
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
                <link-button v-if="item.study"
                            :sid="item.study.sid"
                            show_type_input="study"
                            :title="'Study: '+item.study.name"
                            icon="study"
                />

                <JsonButton :resource_url="api + 'interventions/'+ item.pk +'/?format=json'"/>
            </template>

            <template v-slot:item.intervention="{ item }">

                <object-chip :object="item"
                             otype="intervention"
                             :search="search"
                />

            </template>

          <template v-slot:item.details="{ item }">
            <v-layout d-flex flex-wrap >

            <characteristica-card :data="item" />
            </v-layout>

          </template>

            <template v-slot:item.details2="{ item }">
              <object-chip
                  v-if="item.application.sid"
                  :object="item.application"
                  otype="application"
                  :search="search"
              />
              <object-chip
                  v-if="item.route.sid"
                  :object="item.route"
                  otype="route"
                  :search="search"
              />
              <object-chip
                  v-if="item.form.sid"
                  :object="item.form"
                  otype="form"
                  :search="search"
              />

              <object-chip
                  v-if="item.time_unit"
                  :object="timeObject(item)"
                  otype="time"
                  :search="search"
              />
            </template>

            <no-data/>
        </v-data-table>
    </v-sheet>
</template>

<script>
    import {searchTableMixin} from "./mixins";
    import TableToolbar from './TableToolbar';
    import NoData from './NoData';
    import CharacteristicaCard from '../detail/CharacteristicaCard'

    export default {
        name: "InterventionsTable",
        components: {
            NoData,
            TableToolbar,
            CharacteristicaCard,
        },
        mixins: [searchTableMixin],
        data () {
            return {
                otype: "interventions",
                otype_single: "intervention",
                headers: [
                    {text: '', value: 'buttons',sortable: false},
                    {text: 'Intervention', value: 'intervention', sortable: false},
                    {text: 'Details', value: 'details', sortable: false},
                    {text: '', value: 'details2', sortable: false},
                ],
            }
        },
      methods: {
        toNumber: function(num){
          // round to two numbers
          return +(Math.round(num + "e+2")  + "e-2");
        },
        timeObject: function(item){
          return{
            name: "t = " + this.toNumber(item.time) + ' ' + item.time_unit,
            otype: "time",
          }
        },

      }

    }
</script>

<style scoped>
</style>