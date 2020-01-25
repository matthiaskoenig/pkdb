<template>
    <v-card>
        <span v-if="user">
            <v-card-text>
            <v-form>
                <v-text-field readonly
                              prepend-icon="fas fa-user-circle"
                              v-model="user"
                              name="username"
                              label="Username"
                              type="text"
                              :value="user"
                />
            </v-form>
            </v-card-text>
            <v-card-actions>
                <v-btn color="primary"  v-on:click="logout">Logout</v-btn>
                <v-spacer/>
                <v-btn flat>
                    <router-link v-on:click.native="close" to="/request-password-reset">
                       password reset
                    </router-link>
                </v-btn>
            </v-card-actions>
        </span>
        <span v-else>
            <v-card-text>
                <v-form>
                    <v-alert v-for="general_warning in general_warnings"
                             :value="general_warnings"
                             type="error"
                             :key="general_warning">
                        {{general_warning}}
                    </v-alert>
                    <v-text-field v-on:keyup.enter="login"
                                  prepend-icon="fas fa-user-circle"
                                  :error="user_warnings"
                                  :error-messages="user_warnings"
                                  v-model="username"
                                  name="username"
                                  label="Login"
                                  type="text"
                    />
                    <v-text-field v-on:keyup.enter="login"
                                  prepend-icon='fas fa-lock'
                                  :error="password_warnings"
                                  :error-messages="password_warnings"
                                  v-model="password"
                                  name="password"
                                  label="Password"
                                  id="password"
                                  type="password"
                    />
                </v-form>
            </v-card-text>
            <v-card-actions>
                <v-btn color="primary" v-on:click="login">Login</v-btn>
                    <v-spacer/>
                    <v-btn text>
                        <router-link v-on:click.native="close" to="/registration" >
                        register
                        </router-link>
                    </v-btn>
                    <v-btn text>
                        <router-link v-on:click.native="close" to="/request-password-reset" >
                        forgot password
                        </router-link>
                    </v-btn>
            </v-card-actions>
        </span>
    </v-card>
</template>

<script>
    import axios from 'axios'

    export default {
        name: "UserLogin",
        data: () => ({
            valid: true,
            username: '',
            password:'',
            warnings:''
        }),
        props: {
        },
        computed: {
            token() {
                return this.$store.state.token;
            },
            user() {
                return this.$store.state.username;
            },
            general_warnings(){
                if (this.warnings){

                    if ("non_field_errors" in this.warnings){
                        return this.warnings["non_field_errors"]
                    }
                    else {
                        return null
                    }
                }
                else{
                    return null
                }


            },
            user_warnings(){
                if (this.warnings){

                    if ("username" in this.warnings){
                        console.log(this.warnings);
                        return this.warnings["username"]
                    }
                    else {
                        return null
                    }
                }
                else{
                    return null
                }

            },
            password_warnings(){
                if (this.warnings){

                    if ("password" in this.warnings){
                        return this.warnings["password"]
                    }
                    else {
                        return null
                    }
                }
                else{
                    return null
                }
            }
        },
        methods: {
            close() {
                this.$emit('update:dialog', false)
            },

            login: function(){
                // reset store
                this.$store.dispatch('logout');
                // reset warnings
                this.warnings = null;

                // window.alert("login id: " + this.username + "\n" + "password: " + this.password);
                const payload = {"username": this.username, "password": this.password};
                console.log(payload);

                axios.post(this.$store.state.endpoints.obtainAuthToken, payload)
                    .then((response)=>{
                        this.$store.dispatch('login', {
                            username: this.username,
                            token: response.data.token,
                    });

                        this.close();
                        // do a refresh
                        this.$router.go()
                    })
                    .catch((error)=>{
                        this.warnings = error.response.data;

                        console.log(error);
                    })
            },

            logout: function(){
                this.$store.dispatch('logout');
                 this.close();
                // do a refresh
                this.$router.go()
            }
        }
    }
</script>

<style scoped>
</style>