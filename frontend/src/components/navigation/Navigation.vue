<template>
    <v-app-bar
               fixed
               dark
               dense
               class="fixed-nav-bar1"

    >
      <v-toolbar-title to="/" title="Home" color="white"><span class="logo">PK-DB</span></v-toolbar-title>
      <v-toolbar-items>
          <v-btn  to="/data" title="Data" >
            <v-icon left dark color="#1E90FF">{{ faIcon('data') }}</v-icon>
            Data
          </v-btn>

        <v-btn to="/search" title="Search" ><v-icon left dark color="#41b883">{{ faIcon('search') }}</v-icon> Search </v-btn>
      </v-toolbar-items>

      <v-spacer></v-spacer>
        <v-chip v-if="username" flat title="Logout" @click.stop="dialog=true" dark  >
                 <user-avatar :username="username"></user-avatar>
                 {{ username }}
        </v-chip>
       <drop-down-menu/>
   </v-app-bar>
</template>

<script>
   import {IconsMixin} from "@/icons"
   import DropDownMenu from "./DropDownMenu";
   import Account from "./Account";

   export default {
       name: 'Navigation',
       components: {
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