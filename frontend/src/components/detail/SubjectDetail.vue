<template>
  <div width="100%" style="color: white">
    <div class="overline">
       <h2>
      <v-icon class="mr-4">{{ faIcon(subject_type) }}</v-icon>
      <text-highlight :queries="highlight">{{ subject.name }}</text-highlight>
      <json-button :resource_url="api + 'subjects/'+ subject.pk +'/?format=json'"/>
    </h2>
    </div>

    <v-list  subheader dense>
      <v-subheader v-if="subject.count" >Count</v-subheader>

      <v-list-item v-if="subject.count">
        {{subject.count}}
      </v-list-item>

      <v-subheader v-if="subject.parent" >Parent</v-subheader>

      <v-list-item v-if="subject.parent">
        <object-chip :object="subject.parent"
                     otype="group"
                     :search="highlight"
                     style="z-index: 9999"
        />
      </v-list-item>
      <v-subheader v-if="subject.group" >Group</v-subheader>

      <v-list-item v-if="subject.group">
        <object-chip :object="subject.group"
                     otype="group"
                     :search="highlight"
                     style="z-index: 9999"
        />
      </v-list-item>
      <v-subheader v-if="subject.characteristica" >Characteristica</v-subheader>
      <v-list-item>

        <characteristica-card-deck :characteristica="subject.characteristica" :layout="false"/>
      </v-list-item>
    </v-list>
  </div>
</template>

<script>
    import CharacteristicaCardDeck from './CharacteristicaCardDeck';
    import {ApiInteractionMixin} from "../../apiInteraction";
    import {IconsMixin} from "../../icons";

    export default {
      name: "SubjectDetail",
      mixins: [ApiInteractionMixin, IconsMixin],
      components: {
            CharacteristicaCardDeck
        },

        props: {
            subject: {
                type: Object,
            },
            subject_type:{
              type: String,
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