<template>
  <v-menu left transition="slide-y-transition" offset-y>
    <template v-slot:activator="{ on, attrs }">
      <v-btn
          text
          icon
          v-bind="attrs"
          v-on="on"
          title="Api"
      >
        <v-icon >{{faIcon('api')}}</v-icon>
      </v-btn>
    </template>

    <v-list dense>

      <v-list-item :href="api">
        <!-- Rest API -->
        <v-list-item-title>
          Django
        </v-list-item-title>
     </v-list-item>

      <v-list-item :href="api_swagger">
        <!-- Rest API -->
        <v-list-item-title>
          Swagger
        </v-list-item-title>
      </v-list-item>

      <v-list-item :href="api_redoc">
        <!-- Rest API -->
        <v-list-item-title>
          Redoc
        </v-list-item-title>
      </v-list-item>

   </v-list>
    <v-dialog v-model="dialog" max-width="500">
      <user-login></user-login>
    </v-dialog>
 </v-menu>
</template>

<script>
import {IconsMixin} from "@/icons"
import  UserLogin from "../auth/UserLogin"
import {ApiInteractionMixin} from "../../apiInteraction";

export default {
 name: 'DropDownMenu',
 components: {UserLogin},
 mixins: [IconsMixin, ApiInteractionMixin],
  data: () => ({
    dialog: false,
  }),
}
</script>

<style scoped>

</style>