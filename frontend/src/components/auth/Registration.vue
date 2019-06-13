<template>
    <div>
        <v-toolbar color="secondary" dark>

        <v-toolbar-title>Registration </v-toolbar-title>
        <v-spacer></v-spacer>
    </v-toolbar>
        <v-card-text>
            <v-form>
                <v-text-field prepend-icon="fas fa-user-circle"  :error="user_warnings.length" :error-messages="user_warnings" v-model="username" name="username" label="Login" type="text"></v-text-field>
                <v-text-field prepend-icon="fas fa-envelope"  :error="email_warnings.length" :error-messages="email_warnings" v-model="email" name="email" label="Email" type="text"></v-text-field>
                <v-text-field prepend-icon='fas fa-lock' :error="password_warnings.length" :error-messages="password_warnings"  v-model="password" name="password" label="Password" id="password" type="password"></v-text-field>

            </v-form>
        </v-card-text>
        <v-card-actions>
            <v-alert :value="success"  type="success" >
                {{registration_message}}
            </v-alert>
            <v-spacer></v-spacer>
            <v-btn color="primary" v-on:click="login" >register</v-btn>
        </v-card-actions>
    </div>


</template>

<script>
    import axios from 'axios'

    export default {
        name: "Registration",
        data: () => ({
            username: '',
            email: '',
            password:'',
            warnings:{},
            registration_message:"Thank You for the registration. Check your mails for the verification link.",
            success:false,

        }),

        computed: {

            user_warnings(){

                    if ("username" in this.warnings){
                        return this.warnings["username"]
                    }
                    else {
                        return []
                    }
            },
            password_warnings(){
                    if ("password" in this.warnings){
                        return this.warnings["password"]
                    }
                    else {
                        return []
                    }
            },
            email_warnings(){

                    if ("email" in this.warnings){
                        return this.warnings["email"]
                    }
                    else {
                        return []
                    }
            },
            token() {
                return this.$store.state.token;
            },
            user() {
                return this.$store.state.username;
            },
        },
        methods: {
            login: function(){
                    // reset store
                    // reset warnings
                    this.warnings = {};
                    this.success = false;

                const payload = {"username": this.username, "password": this.password, "email":this.email};

                    axios.post(this.$store.state.endpoints.register, payload)
                        .then((response)=>{
                            console.log(response);
                            this.success = true

                        })
                        .catch((error)=>{
                            this.warnings = error.response.data;
                            this.success = false
                        })
                }
            }



    }
</script>

<style scoped>
</style>