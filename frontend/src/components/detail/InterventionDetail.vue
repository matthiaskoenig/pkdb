<template>
  <div>
    <v-list-item three-line >
      <v-list-item-content>
        <div class="overline">
          Intervention
          <JsonButton :resource_url="api + 'interventions/'+ intervention.pk +'/?format=json'"/>
        </div>
        <v-list-item-title class="headline mb-1">
          <text-highlight :queries="highlight">{{ intervention.name }}</text-highlight>
        </v-list-item-title>
        <v-layout d-flex flex-wrap >

          <characteristica-card :data="intervention" />
        </v-layout>

        <object-chip
            v-if="intervention.application"
            :object="intervention.application"
            otype="application"
            :search="highlight"
        />
        <object-chip
            v-if="intervention.route"
            :object="intervention.route"
            otype="route"
            :search="highlight"
        />
        <object-chip
            v-if="intervention.form"
            :object="intervention.form"
            otype="form"
            :search="highlight"
        />

        <object-chip
            v-if="intervention.time_unit"
            :object="timeObject(intervention)"
            otype="time"
            :search="highlight"
        />
      </v-list-item-content>

    </v-list-item>
  </div>

</template>

<script>
    import CharacteristicaCard from './CharacteristicaCard';
    import {utils} from "../../utils";
    import {ApiInteractionMixin} from "../../apiInteraction";

    export default {
        name: "InterventionDetail",
      mixins:[utils, ApiInteractionMixin],
        components: {
            CharacteristicaCard
        },
        props: {
            intervention: {
                type: Object,
            },
            resource_url: {
                type: String
            }
        },
        computed: {
        },
        methods: {
          timeObject: function (o){return utils.timeObject(o)},

        }
    }
</script>

<style scoped>

</style>