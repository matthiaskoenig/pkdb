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