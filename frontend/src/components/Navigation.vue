<template>
  <span id="navigation">
    <v-app-bar
               class="fixed-nav-bar1"
               permanent
               floating
               dark
               dense
               color="#222222"
    >
      <!--
      <v-app-bar-nav-icon @click="collapse = !collapse"></v-app-bar-nav-icon>
      -->

      <v-toolbar-title to="/" title="Home" color="white"><span class="logo">PK-DB</span></v-toolbar-title>


      <v-btn icon to="/" title="Home" color="white"><v-icon>{{ faIcon('home') }}</v-icon></v-btn>
      <v-btn icon to="/data" title="Data" color="#1E90FF"><v-icon>{{ faIcon('data') }}</v-icon></v-btn>
      <v-btn icon to="/search" title="Search" color="#41b883"><v-icon>{{ faIcon('search') }}</v-icon></v-btn>

      <v-spacer></v-spacer>
      <v-btn icon to="/curation" title="Curation information" color="grey" small><v-icon small>{{ faIcon('curation') }}</v-icon></v-btn>
      <v-btn icon :href="api_url" title="REST API" color="grey" small><v-icon small>{{ faIcon('api') }}</v-icon></v-btn>

      <!-- account -->
        <v-chip v-if="username" flat title="Logout" @click.stop="dialog=true" color="grey" small>
            <user-avatar :username="username"></user-avatar>
            {{ username }}
        </v-chip>
        <v-btn icon v-if="username==null" title="Login" @click.stop="dialog=true" color="grey" small>
            <v-icon small>{{ faIcon('account') }}</v-icon>
        </v-btn>

        <v-dialog v-model="dialog" max-width="500">
            <user-login></user-login>
        </v-dialog>

    </v-app-bar>

    <!--
  <v-navigation-drawer
      v-model="drawer"
      absolute
      temporary
  >
    <v-list
        nav
        dense
    >
      <v-list-item-group
          v-model="group"
          active-class="deep-purple--text text--accent-4"
      >
        <v-list-item>
          <v-list-item-icon>
            <v-icon>{{ faIcon('home') }}</v-icon>
          </v-list-item-icon>
          <v-list-item-title to="/">Home</v-list-item-title>
        </v-list-item>

        <v-list-item>
          <v-list-item-icon>
            <v-icon color="#41b883">{{ faIcon('search') }}</v-icon>
          </v-list-item-icon>
          <v-list-item-title to="/search">Search</v-list-item-title>
        </v-list-item>


      </v-list-item-group>
    </v-list>
  </v-navigation-drawer>
  -->
    </span>
</template>

<script>
    import {IconsMixin} from "@/icons"
    import  UserLogin from "./auth/UserLogin"

    export default {
        name: 'Navigation',
        components: {
            UserLogin,
        },
        mixins: [IconsMixin],
        data: () => ({
            dialog: false,
            drawer: false,
            collapse: true,
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
        margin-left: 5px;
        margin-right: 5px;
    }

    .logo {
      padding-right: 25px;
      font-family: "Roboto Light";
      font-size: 30px;
    }
</style>