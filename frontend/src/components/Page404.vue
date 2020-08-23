<template>
  <v-row align="start"
         justify="center">
    <v-col sm="12" md="10" lg="8">

        <h1>404 <code><strong v-if="this.prevRoute">{{ this.prevRoute.path }}</strong></code></h1>
        <p>
            Page <code><strong v-if="this.prevRoute">{{ this.prevRoute.path }}</strong></code> not found or no access to page as
          <code>
            <strong v-if="this.$store.state.username">{{ this.$store.state.username }}</strong>
            <strong v-else>anonymous</strong>
          </code> user.
        </p>
    </v-col>
  </v-row>
</template>

<script>
    import UserLogin from './auth/UserLogin'
    export default {
        name: 'Page404',
        components: {
            UserLogin
        },
        data() {
            return {
                prevRoute: null
            }
        },
        beforeRouteEnter(to, from, next) {
            next(vm => {
                vm.prevRoute = from
            })
        },
        methods: {
        }
    }
</script>

<style>
</style>