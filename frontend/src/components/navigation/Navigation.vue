<template>
    <v-app-bar fixed
               dense
               app
               clipped-left
               clipped-right
    >
      <router-link tag="button" to="/" >
      <v-toolbar-title  title="Home" color="white"><span class="logo">PK-DB</span></v-toolbar-title>
    </router-link>
      <v-toolbar-items>
        <v-btn text to="/data" title="Data">
            <v-icon left color="#1E90FF">{{ faIcon('data') }}</v-icon>Data
        </v-btn>
      </v-toolbar-items>


      <v-spacer></v-spacer>
        <v-chip v-if="username" text title="Logout" @click.stop="dialog=true" dark>
                 <user-avatar :username="username"></user-avatar>
                 {{ username }}
        </v-chip>
        <v-dialog v-model="dialog" max-width="500">
        <user-login></user-login>
        </v-dialog>
       <drop-down-menu/>
   </v-app-bar>
</template>

<script>
   import {IconsMixin} from "@/icons"
   import DropDownMenu from "./DropDownMenu";
   import Account from "./Account";
   import  UserLogin from "../auth/UserLogin"

   export default {
       name: 'Navigation',
       components: {
         UserLogin,
         Account,
         DropDownMenu,
       },
       mixins: [IconsMixin],
       data: () => ({
           dialog: false,
       }),
       computed: {
         api_url() {
             return this.$store.state.endpoints.api;
           },
         username(){
           return this.$store.state.username
         },
       }
   }
</script>

<style scoped>
   .logo {
     padding-right: 25px;
     font-family: "Roboto Light";
     font-size: 30px;
   }
</style>