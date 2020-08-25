<template>
  <!-- account -->
  <div>
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
  </div>
</template>

<script>
import  UserLogin from "../auth/UserLogin"
import {IconsMixin} from "../../icons";

export default {
name: "Account",
  components:[UserLogin],
  mixins: [IconsMixin],
  data: () => ({
    dialog: false,
  }),
  computed: {
    username(){
      return this.$store.state.username
    }
  }
}
</script>

<style scoped>

</style>