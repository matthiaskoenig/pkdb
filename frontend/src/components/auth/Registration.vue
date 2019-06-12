<template>
    <div>
        <v-toolbar color="secondary" dark>

        <v-toolbar-title>Registreation </v-toolbar-title>
        <v-spacer></v-spacer>
        <v-tooltip bottom>
            <v-btn
                    icon
                    large
                    :href="source"
                    target="_blank"
                    slot="activator"
            >
            </v-btn>
        </v-tooltip>
    </v-toolbar>
        <v-card-text>
            <v-form>
                <v-text-field prepend-icon="fas fa-user-circle"  :rules="nameRules" v-model="username" name="username" label="Login" type="text"></v-text-field>
                <v-text-field prepend-icon="fas fa-envelope" :rules="emailRules" v-model="email" name="email" label="Email" type="text"></v-text-field>
                <v-text-field prepend-icon='fas fa-lock' v-model="password" name="password" label="Password" id="password" type="password"></v-text-field>
                <v-text-field prepend-icon='fas fa-lock' v-model="confirm_password" name="confirm_password" label=" confirm Password" id="confirm_password" type="password"></v-text-field>

            </v-form>
        </v-card-text>
        <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn color="primary">Login</v-btn>
        </v-card-actions>
    </div>

    <!--
    <span id="user-login">
        <div v-if="user">
            <button v-on:click="logout">Logout</button>
        </div>
        <div v-else>
            <input type="text" placeholder="username" v-model="username">
            <input type="password" placeholder="password" v-model="password">
            <button v-on:click="login">Login</button>
        </div>
        <p>
            <span v-if="user">
            User: {{ user }}<br />
            Token: {{ token }}<br />
            </span>
            <span v-if="warnings">Warnings: {{ warnings }}</span>
        </p>
    </span>
    -->
</template>

<script>
    import axios from 'axios'

    export default {
        name: "Registration",
        data: () => ({
            valid: true,
            username: '',
            nameRules: [
                v => !!v || 'Username is required',
            ],
            email: '',
            emailRules: [
                v => !!v || 'E-mail is required',
                v => /.+@.+/.test(v) || 'E-mail must be valid'
            ],
            passwordRules: [
                v => !!v || 'Password is required',
            ],
            confirmPasswordRules: [
                v => !!v || 'Confirm password is required',
                v => v = v === this.password || 'Confirm password does not match',

            ],
            password:'',
            confirm_password:''
        }),

        computed: {
            token() {
                return this.$store.state.token;
            },
            user() {
                return this.$store.state.username;
            },
        },
        methods: {
            login: function(){
                //FIXME: login in django

                // reset store
                this.logout();
                // reset warnings
                this.warnings = null;

                // window.alert("login id: " + this.username + "\n" + "password: " + this.password);
                const payload = {"username": this.username, "password": this.password};
                // console.log(payload);

                axios.post(this.$store.state.endpoints.obtainAuthToken, payload)
                    .then((response)=>{
                        this.$store.dispatch('login', {
                            username: this.username,
                            token: response.data.token
                        })
                    })
                    .catch((error)=>{
                        this.warnings = error.response.data;

                        console.log(error);
                    })
            },

            logout: function(){
                //FIXME: logout in django
                // window.alert("logout id: " + this.username);
                this.$store.dispatch('logout')
            }
        }
    }
</script>

<style scoped>
</style>