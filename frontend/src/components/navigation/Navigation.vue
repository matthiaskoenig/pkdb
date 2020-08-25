<template>
    <v-app-bar
               fixed
               dark
               dense
               class="fixed-nav-bar1"

    ><router-link tag="button" to="/" >
      <v-toolbar-title  title="Home" color="white"><span class="logo">PK-DB</span></v-toolbar-title>
    </router-link>
      <v-toolbar-items>

        <v-btn  to="/data" :title="tables_label" >
            <v-icon left dark color="#1E90FF">{{ faIcon('data') }}</v-icon>
          {{ tables_label }}
          </v-btn>

        <v-btn to="/search" title="Search" ><v-icon left dark color="#41b883">{{ faIcon('search') }}</v-icon> Search </v-btn>
      </v-toolbar-items>


      <v-spacer></v-spacer>
        <v-chip v-if="username" flat title="Logout" @click.stop="dialog=true" dark  >
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
         tables_label(){
           if(this.$store.getters.isInitial){
             return "Data"
           }else{
             return "Results"
           }
         }
       }
   }
</script>

<style scoped>
   .fixed-nav-bar1 {
       position: fixed;
       top: 0;
       left: 0;
       z-index: 9999;
       width: 100%;
       height: 50px;
   }

   .logo {
     padding-right: 25px;
     font-family: "Roboto Light";
     font-size: 30px;
   }
</style>