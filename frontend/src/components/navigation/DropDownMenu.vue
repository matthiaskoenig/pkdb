<template>
  <v-menu left transition="slide-y-transition" offset-y>
    <template v-slot:activator="{ on, attrs }">
      <v-btn
          text
          icon
          v-bind="attrs"
          v-on="on"
      >
        <v-icon >fas fa-ellipsis-v</v-icon>
      </v-btn>
    </template>

    <v-list dense>
      <v-list-item to="/curation">
        <!-- Curation -->
        <v-list-item-icon ><v-icon>{{ faIcon('curation') }}</v-icon>

        </v-list-item-icon>
        <v-list-item-title>
          Curation
        </v-list-item-title>
      </v-list-item>

      <v-list-item :href="api">
        <!-- Rest API -->
        <v-list-item-icon><v-icon>{{ faIcon('api') }}</v-icon></v-list-item-icon>
        <v-list-item-title>
          API
        </v-list-item-title>
     </v-list-item>
      <v-list-item :href="api_swagger">
        <!-- Rest API -->
        <v-list-item-icon><v-icon>{{ faIcon('api') }}</v-icon></v-list-item-icon>
        <v-list-item-title>
          Swagger API
        </v-list-item-title>
      </v-list-item>

      <v-list-item :href="api_redoc">
        <!-- Rest API -->
        <v-list-item-icon><v-icon>{{ faIcon('api') }}</v-icon></v-list-item-icon>
        <v-list-item-title>
          Redoc API
        </v-list-item-title>
      </v-list-item>

      <v-list-item v-if="username" @click.stop="dialog=true">

        <v-list-item-icon> <user-avatar :username="username"></user-avatar> </v-list-item-icon>

        <v-list-item-title>
          {{ username }}
        </v-list-item-title>

     </v-list-item >
      <v-list-item v-if="username==null"  @click.stop="dialog=true">

        <v-list-item-icon> <v-icon>{{  faIcon('account')  }}</v-icon></v-list-item-icon>

        <v-list-item-title>
          Login
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
  computed:{
    username(){
      return this.$store.state.username
    }
  }
}
</script>

<style scoped>

</style>