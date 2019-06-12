<template>
        <div id="app">
          <v-app id="inspire">
            <v-content>
              <v-container fluid fill-height>
                <v-layout align-center justify-center>
                  <v-flex xs12 sm8 md4>
                    <v-card class="elevation-12">
                            <user-login></user-login>
                    </v-card>
                  </v-flex>
                </v-layout>
              </v-container>
            </v-content>
          </v-app>
        </div>










        <!--
               <h1>User Account</h1>
               #<h2>Vue login</h2>
               #<div id="login-example">
                   <user-login></user-login>
               </div>

               <h2>Django endpoints</h2>
               <ul>
                   <span v-if="user">
                   <li><a :href="domain+'/accounts/password/change/'+user">change password</a></li>
                   <li><a :href="domain+'/accounts/password/reset/'+user">reset password</a></li>
                   </span>
                   <span v-else>
                       <li><a :href="domain+'/accounts/register/'">register</a></li>
                       <li><a :href="domain+'/accounts/resend-verification/'">resend-verification</a></li>

                       <li><a :href="domain+'/accounts/login/'">login</a></li>
                       <li><a :href="domain+'/accounts/logout/'">logout</a></li>

            </span>
        </ul>
    </span>
    -->
</template>

<script>
    import UserLogin from './UserLogin'

    export default {
        name: "Account",
        components: {
            UserLogin
        },
        data() {
            return {}
        },
        computed: {
            domain() {
                return this.$store.state.django_domain;
            },
            user() {
                return this.$store.state.username;
            },
        },
    }
</script>

<style scoped>
</style>