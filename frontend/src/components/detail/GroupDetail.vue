<template>
  <v-card flat class="ma-0 pa-0 parent_color" width="100%">
    <v-card-title>

    <v-list-item >
      <v-list-item-content>
        <div class="overline">
          <v-icon class="mr-4">{{ faIcon('group') }}</v-icon>
          <text-highlight :queries="highlight">{{ group.name }}</text-highlight>
          <json-button :resource_url="api + 'groups/'+ group.pk +'/?format=json'"/>
        </div>
      </v-list-item-content>

    </v-list-item>
    </v-card-title>
    <v-card-text>
      <v-list  subheader dense>
        <v-subheader v-if="group.parent" >Parent</v-subheader>

        <v-list-item v-if="group.parent">
          Parent
          <object-chip :object="group.parent"
                       otype="group"
                       :search="highlight"
                       style="z-index: 9999"
          />
        </v-list-item>
        <v-subheader v-if="group.characteristica" >Characteristica</v-subheader>
        <v-list-item>

          <characteristica-card-deck :characteristica="group.characteristica" :layout="false"/>
        </v-list-item>
      </v-list>
    </v-card-text>


  </v-card>
</template>

<script>
    import CharacteristicaCardDeck from './CharacteristicaCardDeck';
    import {ApiInteractionMixin} from "../../apiInteraction";
    import {IconsMixin} from "../../icons";

    export default {
      name: "GroupDetail",
      mixins: [ApiInteractionMixin, IconsMixin],
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
.parent_color{
  background-color: inherit;
}
</style>