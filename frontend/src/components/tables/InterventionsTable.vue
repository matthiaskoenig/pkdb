<template>
    <v-card flat>
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
                <LinkButton v-if="item.study"
                            :sid="item.study.sid"
                            show_type="study"
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

          <template v-slot:item.substance="{ item }">
            <characteristica-card :data="item" :count="1" />
            <object-chip :object="item.substance"
                         otype="substance"
                         :search="search"
            />

          </template>

            <template v-slot:item.details="{ item }">
              <object-chip :object="item.application"
                           otype="application"
                           :search="search"
              />
              <object-chip :object="item.route"
                           otype="route"
                           :search="search"
              />
              <object-chip :object="item.form"
                           otype="form"
                           :search="search"
              />

              <object-chip :object="timeObject(item)"
                           otype="time"
                           :search="search"
              />
            </template>

            <no-data/>
        </v-data-table>
    </v-card>
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
                    {text: 'Substance', value: 'substance', sortable: false},
                    {text: 'Details', value: 'details', sortable: false},
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