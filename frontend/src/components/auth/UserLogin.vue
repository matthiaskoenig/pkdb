<template>
    <v-card>
        <span v-if="user">
            <v-btn color="primary"  v-on:click="logout">Logout</v-btn>
             <p>
            <span v-if="user">
            User: {{ user }}<br />
            Token: {{ token }}<br />
                <v-spacer> </v-spacer>
                <router-link   v-on:click.native="close" to="/request-password-reset" >
                   request password reset
                </router-link>
            </span>
        </p>
        <!--
        <a :href="domain+'/accounts/password/change/'+user">change password</a>
        <a :href="domain+'/accounts/password/reset/'+user">reset password</a>
        -->
        </span>
        <span v-else>

        <v-card-text>
            <v-form>

                <v-alert v-for="general_warning in general_warnings" :value="general_warnings" type="error">
                    {{general_warning}}
                </v-alert>
                <v-text-field v-on:keyup.enter="login" prepend-icon="fas fa-user-circle" :error="user_warnings" :error-messages="user_warnings" v-model="username" name="username" label="Login" type="text"></v-text-field>
                <v-text-field v-on:keyup.enter="login" prepend-icon='fas fa-lock' :error="password_warnings" :error-messages="password_warnings" v-model="password" name="password" label="Password" id="password" type="password"></v-text-field>
            </v-form>
        </v-card-text>
        <v-card-actions>
            <v-spacer>
                <router-link   v-on:click.native="close" to="/registration" >
                   register
                </router-link>
                <v-spacer> </v-spacer>
                 <router-link   v-on:click.native="close" to="/request-password-reset" >
                   forgot password
                </router-link>


            </v-spacer>
            <v-spacer> </v-spacer>
            <v-btn color="primary"  v-on:click="login">Login</v-btn>

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
            showUserDialog: {
                default:false
            }
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

                        this.close()
                    })
                    .catch((error)=>{
                        this.warnings = error.response.data;

                        console.log(error);
                    })
            },

            logout: function(){
                this.$store.dispatch('logout');
                this.close()
            }
        }
    }
</script>

<style scoped>
</style>