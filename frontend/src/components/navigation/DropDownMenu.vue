<template>
  <v-menu left transition="slide-y-transition" offset-y>
    <template v-slot:activator="{ on, attrs }">
      <v-btn
          dark
          icon
          v-bind="attrs"
          v-on="on"
      >
        <v-icon>fas fa-ellipsis-v</v-icon>
      </v-btn>
    </template>

    <v-list dense>
      <v-list-item>
        <!-- Curation -->
        <v-list-item-icon><v-icon>{{ faIcon('curation') }}</v-icon></v-list-item-icon>
        <!--<v-btn icon to="/curation" title="Curation information" color="grey" small></v-btn> -->
        <v-list-item-title>
          Curation
        </v-list-item-title>
      </v-list-item>

      <v-list-item>
        <!-- Rest API -->
        <v-list-item-icon><v-icon>{{ faIcon('api') }}</v-icon></v-list-item-icon>
        <v-list-item-title>
          API
        </v-list-item-title>
        <!--<v-btn icon :href="api_url" title="REST API" color="grey" small><v-icon small>{{ faIcon('api') }}</v-icon></v-btn> -->
     </v-list-item>

      <v-list-item v-if="username" @click.stop="dialog=true">
        <!-- User -->
        <!--
          <v-chip v-if="username" flat title="Logout" @click.stop="dialog=true" color="grey" small>
            <user-avatar :username="username"></user-avatar>
            {{ username }}
          </v-chip>
        -->

        <v-list-item-icon> <user-avatar :username="username"></user-avatar> </v-list-item-icon>

        <v-list-item-title>
          {{ username }}
        </v-list-item-title>

     </v-list-item >
      <v-list-item v-if="username==null"  @click.stop="dialog=true">
        <!-- User -->
        <!--
          <v-btn icon v-if="username==null" title="Login" @click.stop="dialog=true" color="grey" small>
            <v-icon small>{{ faIcon('account') }}</v-icon>
          </v-btn>
        -->

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

export default {
 name: 'DropDownMenu',
 components: {UserLogin},
 mixins: [IconsMixin],
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