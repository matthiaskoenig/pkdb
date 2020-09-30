<template>
  <div width="100%" style="color: white">
    <div class="overline">
      <h2>
        <v-icon class="mr-4">{{ faIcon("intervention") }}</v-icon>
        <text-highlight :queries="highlight">{{ intervention.name }}</text-highlight>
        <JsonButton :resource_url="api + 'interventions/'+ intervention.pk +'/?format=json'"/>
      </h2>
    </div>
    <v-list  subheader dense>

    </v-list>
    <v-subheader>Measurement</v-subheader>
    <v-list-item>
      <characteristica-card :data="intervention" />
    </v-list-item>

    <v-list-item v-for="(item, key) in data" :key="key" v-if="item.if_is">
      <v-subheader >{{key}}</v-subheader>

      <object-chip
          :object="item.value"
          :otype="key.toLowerCase()"
          :search="highlight"/>
    </v-list-item>

  </div>

</template>

<script>
    import CharacteristicaCard from './CharacteristicaCard';
    import {utils} from "../../utils";
    import {ApiInteractionMixin} from "../../apiInteraction";
    import {IconsMixin} from "../../icons";

    export default {
        name: "InterventionDetail",
      mixins:[utils, ApiInteractionMixin, IconsMixin],
      computed:{
            data(){return {
              "Application": {value:this.intervention.application, if_is: this.intervention.application},
              "Route": {value:this.intervention.route, if_is: this.intervention.route},
              "Form":  {value:this.intervention.form, if_is: this.intervention.form},
              "Time":  {value:this.timeObject(this.intervention), if_is: this.intervention.time_unit},
            }
          }
      },
        components: {
            CharacteristicaCard
        },
        props: {
            intervention: {
                type: Object,
            }
        },
        methods: {
          timeObject: function (o){return utils.timeObject(o)},
        }
    }
</script>

<style scoped>

</style>