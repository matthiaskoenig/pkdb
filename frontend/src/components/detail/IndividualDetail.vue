<template>
    <div>
        <v-list-item three-line >
          <v-list-item-content>
            <div class="overline">
             INDIVIDUAL
              <json-button :resource_url="api + 'individuals/'+ individual.pk +'/?format=json'"/>
            </div>
          <v-list-item-title class="headline mb-1">
            <text-highlight :queries="highlight">{{ individual.name }}</text-highlight>
          </v-list-item-title>
          <v-list-item-subtitle v-if="individual.group">Group:
            <object-chip :object="individual.group"
                         otype="group"
                         :search="highlight"
            />
          </v-list-item-subtitle>
          </v-list-item-content>

        </v-list-item>

      <characteristica-card-deck :characteristica="individual.characteristica"/>

    </div>
</template>

<script>
    import CharacteristicaCardDeck from './CharacteristicaCardDeck';
    import {ApiInteractionMixin} from "../../apiInteraction";

    export default {
      name: "IndividualDetail",
      mixins: [ApiInteractionMixin],
      components: {
            CharacteristicaCardDeck
        },
        props: {
            individual: {
                type: Object,
            }
        }
    }

</script>

<style scoped>

</style>