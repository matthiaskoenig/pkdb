<template>
  <div>
    <v-list-item three-line >
      <v-list-item-content>
        <div class="overline">
          Group
          <json-button :resource_url="api + 'groups/'+ group.pk +'/?format=json'"/>

        </div>
        <v-list-item-title class="headline mb-1">
          <text-highlight :queries="highlight">{{ group.name }}</text-highlight>

        </v-list-item-title>
        <v-list-item-subtitle v-if="group.parent">Parent:
          <object-chip :object="group.parent"
                       otype="group"
                       :search="highlight"
          />
        </v-list-item-subtitle>
      </v-list-item-content>

    </v-list-item>

    <characteristica-card-deck :characteristica="group.characteristica" />

  </div>
</template>

<script>
    import CharacteristicaCardDeck from './CharacteristicaCardDeck';
    import {ApiInteractionMixin} from "../../apiInteraction";

    export default {
      name: "GroupDetail",
      mixins: [ApiInteractionMixin],
      components: {
            CharacteristicaCardDeck
        },

        props: {
            group: {
                type: Object,
            },
            resource_url: {
                type: String
            },
          pk: {
            type: String
          }
        },
        methods: {

        }
    }
</script>

<style scoped>
</style>