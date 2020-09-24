<template>
  <v-app-bar fixed
             dense
             app
             clipped-left
             clipped-right
  >
    <router-link tag="button" to="/">
      <v-toolbar-title title="Home" color="white"><span class="logo">PK-DB</span></v-toolbar-title>
    </router-link>
    <v-toolbar-items>
      <v-btn text to="/data" title="Data">
        <v-icon left color="#1E90FF">{{ faIcon('data') }}</v-icon>
        Data
      </v-btn>

    </v-toolbar-items>


    <v-spacer></v-spacer>

    <div>
      <!-- If logged in -->
      <div v-if="username">
        <v-chip text title="Logout" @click.stop="dialog=true" dark>
          <user-avatar :username="username"></user-avatar>
          {{ username }}
        </v-chip>
        <drop-down-menu/>
      </div>

      <!-- If logged out -->
      <div v-else>
        <v-btn
            text
            icon
            :href="api_swagger"
            title="REST API"
            target="_blank"
        >
          <v-icon small color="#1E90FF">{{ faIcon('api') }}</v-icon>
        </v-btn>

        <v-btn text
               icon
               to="/curation"
               title="Info Nodes">
          <v-icon small>{{ faIcon('curation') }}</v-icon>
        </v-btn>
        <v-btn text
            icon
            title="Login"
            @click.stop="dialog=true">
          <v-icon small>{{ faIcon('account') }}</v-icon>
        </v-btn>
      </div>
    </div>


    <v-dialog v-model="dialog" max-width="500">
      <user-login></user-login>
    </v-dialog>

  </v-app-bar>
</template>

<script>
import {IconsMixin} from "@/icons"
import DropDownMenu from "./DropDownMenu";
import Account from "./Account";
import UserLogin from "../auth/UserLogin"
import {ApiInteractionMixin} from "../../apiInteraction";

export default {
  name: 'Navigation',
  components: {
    UserLogin,
    Account,
    DropDownMenu,
  },
  mixins: [IconsMixin, ApiInteractionMixin],
  data: () => ({
    dialog: false,
  }),
}
</script>

<style scoped>
.buttons-cell {
  min-width: 100px;

}

.logo {
  padding-right: 25px;
  font-family: "Roboto Light";
  font-size: 30px;
}

</style>